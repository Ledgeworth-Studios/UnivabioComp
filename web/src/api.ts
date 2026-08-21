/**
 * The shape of what `POST /api/search` returns, and the one function that calls it.
 *
 * These types are written by hand to mirror the Pydantic models in
 * `whynot/api.py`. They could be generated from the server's OpenAPI schema
 * instead — the server publishes one at /openapi.json — but a generator is a
 * build step and a dependency to explain, and this is about forty lines. If the
 * two ever drift, `npm run build` fails on the field that moved.
 */

export type Verdict = "MET" | "NOT_MET" | "UNKNOWN";

export interface Check {
  field: string;
  verdict: Verdict;
  reason: string;
  /** The registry's own wording that the reason came from. Rigor rule 2. */
  source: string | null;
}

export interface Criterion {
  index: number;
  kind: "INCLUSION" | "EXCLUSION" | "UNCLASSIFIED";
  text: string;
  /** Verbatim registry text, so a quote can always be found in the record. */
  source_text: string;
}

export interface Site {
  facility: string | null;
  label: string;
  city: string | null;
  state: string | null;
  country: string | null;
  status: string | null;
  distance_miles: number;
}

export interface Trial {
  nct_id: string;
  brief_title: string;
  official_title: string | null;
  overall_status: string | null;
  study_type: string | null;
  phases: string[];
  lead_sponsor: string | null;
  conditions: string[];
  enrollment_count: number | null;
  url: string;
  last_update_post_date: string | null;
  status_verified_date: string | null;
  age_range: string;
  sex: string;
  accepts_healthy_volunteers: boolean | null;
  hard_checks: Check[];
  ruled_out_by_structured_fields: boolean;
  criteria: Criterion[];
  nearest_site: Site | null;
  site_count: number;
}

export interface SearchResponse {
  disclaimer: string;
  total_count: number | null;
  returned: number;
  trials: Trial[];
}

export interface SearchRequest {
  condition: string;
  latitude?: number | null;
  longitude?: number | null;
  radius_miles?: number;
  age_years?: number | null;
  sex?: string | null;
  is_healthy_volunteer?: boolean | null;
  max_results?: number;
}

/** Ask the backend for trials. Throws an Error whose message is worth showing. */
export async function search(request: SearchRequest): Promise<SearchResponse> {
  const response = await fetch("/api/search", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    // FastAPI puts a readable message in `detail` for our own errors, and an
    // array of field problems there for validation failures.
    const body = await response.json().catch(() => null);
    const detail = body?.detail;
    throw new Error(
      typeof detail === "string" ? detail : `The search failed (HTTP ${response.status}).`,
    );
  }
  return (await response.json()) as SearchResponse;
}
