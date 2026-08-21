# One image: the built interface and the API that serves it.
#
# Two stages, because the tools that *build* the web page have no business being
# in the image that runs in production. node and its ~200MB of packages exist
# only in the first stage; the final image has Python, the application, and the
# handful of built files that came out of stage one.

# --------------------------------------------------------------------------
# Stage 1 — build the interface
# --------------------------------------------------------------------------
FROM node:22-slim AS web

WORKDIR /build

# Copy the manifests alone first. Docker caches each step, and this one only
# re-runs when the dependencies actually change — editing a component does not
# reinstall node_modules.
COPY web/package.json web/package-lock.json ./
# `npm ci` rather than `npm install`: it installs exactly the lockfile, and fails
# instead of quietly resolving something newer. A build that can drift is not a
# build you can reproduce for a judge.
RUN npm ci

COPY web/ ./
RUN npm run build

# --------------------------------------------------------------------------
# Stage 2 — the image that actually runs
# --------------------------------------------------------------------------
FROM python:3.12-slim

# Never write .pyc files, never buffer stdout — logs should appear when they
# happen rather than when the buffer fills.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY whynot/ ./whynot/
RUN pip install --no-cache-dir .

# Only the built output crosses from stage one. No node, no node_modules, no
# source.
COPY --from=web /build/dist ./web/dist

# Run as a normal user. A process that only reads a public registry and serves
# static files has no need of root, and a container that runs as root is one
# mistake away from being a bigger problem than it should be.
RUN useradd --create-home --uid 10001 whynot && chown -R whynot:whynot /app
USER whynot

# There is no API key in this image and no .env, deliberately. The search path
# needs no credentials — ClinicalTrials.gov v2 is public and unauthenticated —
# and the judge endpoint that will need one (W2-2b) is not built yet. When it is,
# the key belongs in the runtime environment, never baked into a layer.

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/health').status == 200 else 1)"

CMD ["uvicorn", "whynot.api:app", "--host", "0.0.0.0", "--port", "8000"]
