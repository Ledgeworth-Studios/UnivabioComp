/**
 * Everything the app believes about the person searching — in one place.
 *
 * There is exactly one of these, and every part of the interface reads and
 * writes it. That matters more than it looks. `docs/PLAN.md` step 1 is "free
 * text -> structured patient profile", done by a model, and it is not built yet
 * (W2-1, waiting on an API key). When it arrives, its job is to produce *this
 * object* and nothing else. Everything downstream — the chips, the search
 * request, the verdicts — already works against it, so extraction becomes a
 * function that returns a `Profile` rather than a change to the whole app.
 *
 * Every field about the person is `null` when the person has not told us. Not
 * zero, not an empty string, not a sensible default — `null`, meaning "we don't
 * know", which the backend turns into `UNKNOWN` and a question for the study
 * team. Defaulting any of these would silently convert "I didn't say" into a
 * claim the user never made.
 */

import type { SearchRequest } from "./api";
import { PLACES } from "./places";
import type { Place } from "./places";

export interface Profile {
  /** What they are looking for. The one field a search cannot do without. */
  condition: string;
  /**
   * Where to search from — the place itself, not a position in some list.
   *
   * This was an index into `PLACES` until D-4 let people look up a place name.
   * The moment the list could grow, an index stopped meaning anything on its
   * own: search for Tucson, get index 7, and every reader that still consulted
   * the six-item constant fell back to "Anywhere" and searched the whole world
   * without telling anybody. Holding the place removes the class of bug rather
   * than the instance.
   */
  place: Place;
  radiusMiles: number;

  ageYears: number | null;
  /** "female" | "male", or null for "I'd rather not say". */
  sex: string | null;
  /** true only if they have said they don't have the condition. Never false. */
  isHealthyVolunteer: boolean | null;

  // Added by D-6. The test each one had to pass is in docs/decisions/0008:
  // would a person say this in a sentence about their situation, unprompted?
  // Lab values and disease scores fail it, so criteria needing those stay
  // UNKNOWN and become questions for the study team — the product working.

  /** "diagnosed in 2019". A year, because nobody remembers the day. */
  diagnosedYear: number | null;
  /** What they are on now, as they'd say it: "ocrelizumab". */
  currentTreatments: string[];
  /** What they were on before. Trials ask about prior therapy constantly. */
  pastTreatments: string[];
}

/** Split a typed list — "ocrelizumab, prednisone" — the way a person writes one. */
export function parseList(text: string): string[] {
  return text
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

export const EMPTY_PROFILE: Profile = {
  condition: "",
  place: PLACES[1],
  radiusMiles: 50,
  ageYears: null,
  sex: null,
  isHealthyVolunteer: null,
  diagnosedYear: null,
  currentTreatments: [],
  pastTreatments: [],
};

/** The one place a `Profile` becomes a request. */
export function toSearchRequest(profile: Profile): SearchRequest {
  const place = profile.place ?? PLACES[0];
  return {
    condition: profile.condition,
    latitude: place.latitude,
    longitude: place.longitude,
    radius_miles: profile.radiusMiles,
    age_years: profile.ageYears,
    sex: profile.sex,
    is_healthy_volunteer: profile.isHealthyVolunteer,
    diagnosed_year: profile.diagnosedYear,
    current_treatments: profile.currentTreatments,
    past_treatments: profile.pastTreatments,
  };
}

/** How each field reads on a chip, and whether the person actually said it. */
export interface ChipView {
  key: keyof Profile;
  label: string;
  /** What the chip shows, or null when there is nothing to show. */
  value: string | null;
  /**
   * What to display when `value` is null.
   *
   * Almost always "not said", which in this product means something specific:
   * we don't know, so it becomes a question for the study team rather than a
   * reason you were ruled out. That meaning is the interface's central idea, so
   * it must not be borrowed for fields that are simply *not applicable* — a
   * search with no location has no radius, and nobody failed to mention it.
   */
  absentLabel: string;
  /** Can this be cleared back to "not said"? The condition cannot. */
  clearable: boolean;
}

const NOT_SAID = "not said";

export function describe(profile: Profile): ChipView[] {
  const place = profile.place ?? PLACES[0];
  const searchingAnywhere = place.latitude === null;
  return [
    {
      key: "condition",
      label: "Condition",
      value: profile.condition || null,
      absentLabel: NOT_SAID,
      clearable: false,
    },
    {
      key: "place",
      label: "Near",
      value: searchingAnywhere ? "Anywhere" : place.name,
      absentLabel: NOT_SAID,
      clearable: false,
    },
    {
      key: "radiusMiles",
      label: "Within",
      value: searchingAnywhere ? null : `${profile.radiusMiles} miles`,
      // Not "not said": a search with no location has no radius to state.
      absentLabel: "not needed",
      clearable: false,
    },
    {
      key: "ageYears",
      label: "Age",
      value: profile.ageYears === null ? null : `${profile.ageYears}`,
      absentLabel: NOT_SAID,
      clearable: true,
    },
    {
      key: "sex",
      label: "Sex recorded at birth",
      value: profile.sex,
      absentLabel: NOT_SAID,
      clearable: true,
    },
    {
      key: "isHealthyVolunteer",
      label: "Healthy volunteer",
      value: profile.isHealthyVolunteer ? "yes — I don't have this condition" : null,
      absentLabel: NOT_SAID,
      clearable: true,
    },
    {
      key: "diagnosedYear",
      label: "Diagnosed",
      value: profile.diagnosedYear === null ? null : `${profile.diagnosedYear}`,
      absentLabel: NOT_SAID,
      clearable: true,
    },
    {
      key: "currentTreatments",
      label: "Currently taking",
      value: profile.currentTreatments.length ? profile.currentTreatments.join(", ") : null,
      absentLabel: NOT_SAID,
      clearable: true,
    },
    {
      key: "pastTreatments",
      label: "Taken before",
      value: profile.pastTreatments.length ? profile.pastTreatments.join(", ") : null,
      absentLabel: NOT_SAID,
      clearable: true,
    },
  ];
}
