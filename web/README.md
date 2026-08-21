# web — the interface

A Vite + React + TypeScript single page that talks to the FastAPI backend in
`whynot/`.

    npm install
    npm run dev        # http://localhost:5173

The dev server proxies `/api` to `http://127.0.0.1:8000`, so start the backend
first — from the repository root, `just serve`. Or start both at once with
`just dev`.

    npm run build      # type-check and bundle into dist/
    npm run lint

## What is here

    src/api.ts        the shape of the backend's responses, and the fetch call
    src/places.ts     the short list of cities you can search near (see D-4)
    src/App.tsx       the one page: a form, and the results it produces
    src/TrialCard.tsx one trial, with the registry's own wording quoted back

Design, loading and empty states, mobile layout and accessibility are Week 5 in
`BACKLOG.md`. This is the skeleton that proves the query path works end to end.
