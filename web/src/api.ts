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
  /** Whether this site itself is enrolling — not the study's overall status. */
  is_recruiting: boolean;
  /** That status in words a patient can read, e.g. "not open yet". */
  status_note: string;
}

export interface Signal {
  name: string;
  explanation: string;
  /** The registry wording that matched, so a reader can check our working. */
  quote: string | null;
}

/** Present only when two independent signals agree. See docs/decisions/0003. */
export interface NonPatientNotice {
  caution: string;
  signals: Signal[];
}

export interface CoordinatorQuestion {
  question: string;
  because: string;
  /** The registry wording behind it, so it can be pointed at on a printout. */
  source: string | null;
}

export interface SelfAnswerable {
  /** The chip this points at: "age" or "sex". */
  field: string;
  prompt: string;
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
  may_not_enrol_individuals: NonPatientNotice | null;
  questions_for_the_study_team: CoordinatorQuestion[];
  you_could_tell_us: SelfAnswerable[];
  nearest_site: Site | null;
  /** The closest site that is enrolling, when it is not the nearest site. */
  nearest_recruiting_site: Site | null;
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
  diagnosed_year?: number | null;
  current_treatments?: string[];
  past_treatments?: string[];
  max_results?: number;
}

/**
 * Ask the backend for trials.
 *
 * Every error path ends in a sentence a person can act on. `fetch` rejects with
 * "Failed to fetch" when it cannot reach the server, which is the browser
 * talking to a developer, not us talking to somebody trying to find a trial —
 * so each failure is translated on the way out.
 */
export async function search(request: SearchRequest): Promise<SearchResponse> {
  let response: Response;
  try {
    response = await fetch("/api/search", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(request),
    });
  } catch {
    // No response at all: the server is down, or the connection dropped.
    throw new Error(
      "We couldn't reach the search service. Check your connection and try again — " +
        "nothing you typed has been lost.",
    );
  }

  if (!response.ok) {
    // FastAPI puts a readable message in `detail` for our own errors, and an
    // array of field problems there for validation failures.
    const body = await response.json().catch(() => null);
    const detail = body?.detail;
    if (typeof detail === "string") {
      throw new Error(detail);
    }
    if (response.status === 422) {
      throw new Error("That search doesn't look right — check the condition and try again.");
    }
    throw new Error(
      `The search failed (error ${response.status}). This is our end, not yours — trying again may work.`,
    );
  }

  return (await response.json()) as SearchResponse;
}

/** One candidate for a typed place name. */
export interface FoundPlace {
  name: string;
  latitude: number;
  longitude: number;
}

export interface PlacesResponse {
  attribution: string;
  places: FoundPlace[];
}

/**
 * Look up a typed place name.
 *
 * **Never call this from an onChange handler.** The OpenStreetMap Foundation's
 * usage policy forbids auto-complete search outright, and this runs on their
 * donated servers. It is called when the person presses the button, and at no
 * other time — see `whynot/geocode.py` and `docs/decisions/0007`.
 */
export async function findPlaces(query: string): Promise<PlacesResponse> {
  let response: Response;
  try {
    response = await fetch(`/api/places?q=${encodeURIComponent(query)}`);
  } catch {
    throw new Error(
      "We couldn't reach the place lookup. Check your connection, or pick a city from the list.",
    );
  }
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(
      typeof body?.detail === "string"
        ? body.detail
        : "The place lookup failed. Pick a city from the list instead.",
    );
  }
  return (await response.json()) as PlacesResponse;
}
