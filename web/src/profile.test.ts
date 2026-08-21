import { describe as group, expect, test } from "vitest";
import { PLACES } from "./places";
import { EMPTY_PROFILE, describe, parseList, toSearchRequest } from "./profile";
import type { Profile } from "./profile";

/**
 * Tests for the one object holding what the app believes about the person.
 *
 * The rule these exist to protect: **a field the person has not stated is
 * `null`, and stays `null` all the way to the request.** Not zero, not an empty
 * string. A default there would turn "I didn't say" into a claim the user never
 * made — and for age, the claim would be that they are a newborn, which is
 * `NOT_MET` against every adult trial in the registry. That is the exact error
 * `docs/PLAN.md` says to weight hardest, and it would be one careless `?? 0`
 * away.
 */

const stated: Profile = {
  ...EMPTY_PROFILE,
  condition: "multiple sclerosis",
  ageYears: 41,
  sex: "female",
  isHealthyVolunteer: true,
};

group("what the person did not say stays unsaid", () => {
  test("an unstated age reaches the request as null, never as zero", () => {
    const request = toSearchRequest({ ...EMPTY_PROFILE, condition: "asthma" });

    expect(request.age_years).toBeNull();
    expect(request.age_years).not.toBe(0);
    expect(request.sex).toBeNull();
    expect(request.is_healthy_volunteer).toBeNull();
  });

  test("a stated age reaches the request unchanged", () => {
    expect(toSearchRequest(stated).age_years).toBe(41);
    expect(toSearchRequest(stated).sex).toBe("female");
  });

  test("an age of zero is a real answer and is not confused with silence", () => {
    // A newborn is a person. If this ever returns null, the code is treating a
    // stated 0 as "not said", which is the same bug seen from the other side.
    const newborn = toSearchRequest({ ...EMPTY_PROFILE, condition: "x", ageYears: 0 });

    expect(newborn.age_years).toBe(0);
    expect(newborn.age_years).not.toBeNull();
  });

  test("clearing a field puts it back to not-said", () => {
    const cleared: Profile = { ...stated, ageYears: null, sex: null, isHealthyVolunteer: null };

    expect(toSearchRequest(cleared).age_years).toBeNull();
    expect(toSearchRequest(cleared).sex).toBeNull();
    expect(toSearchRequest(cleared).is_healthy_volunteer).toBeNull();
  });
});

group("chips describe the profile honestly", () => {
  test("unstated fields come back with no value, so the chip can show them as unsaid", () => {
    const chips = describe({ ...EMPTY_PROFILE, condition: "asthma" });
    const byKey = Object.fromEntries(chips.map((chip) => [chip.key, chip]));

    expect(byKey.ageYears.value).toBeNull();
    expect(byKey.sex.value).toBeNull();
    expect(byKey.isHealthyVolunteer.value).toBeNull();
  });

  test("stated fields come back with something to show", () => {
    const byKey = Object.fromEntries(describe(stated).map((chip) => [chip.key, chip]));

    expect(byKey.condition.value).toBe("multiple sclerosis");
    expect(byKey.ageYears.value).toBe("41");
    expect(byKey.sex.value).toBe("female");
    expect(byKey.isHealthyVolunteer.value).toContain("don't have this condition");
  });

  test("the condition cannot be cleared, because a search needs one", () => {
    const byKey = Object.fromEntries(describe(stated).map((chip) => [chip.key, chip]));

    expect(byKey.condition.clearable).toBe(false);
    expect(byKey.ageYears.clearable).toBe(true);
    expect(byKey.sex.clearable).toBe(true);
  });

  test("every field of the profile appears as a chip", () => {
    // A field that exists but is never shown is a field the person cannot
    // correct — which defeats the point of the chips.
    const shown = describe(stated).map((chip) => chip.key);
    for (const key of Object.keys(EMPTY_PROFILE) as (keyof Profile)[]) {
      expect(shown).toContain(key);
    }
  });
});

group("searching anywhere", () => {
  test("choosing Anywhere sends no coordinates rather than a made-up pair", () => {
    const request = toSearchRequest({ ...EMPTY_PROFILE, condition: "asthma", place: PLACES[0] });

    expect(request.latitude).toBeNull();
    expect(request.longitude).toBeNull();
  });

  test("a place sends its coordinates", () => {
    const request = toSearchRequest({ ...EMPTY_PROFILE, condition: "asthma", place: PLACES[1] });

    expect(request.latitude).toBeCloseTo(45.5152);
    expect(request.longitude).toBeCloseTo(-122.6784);
  });

  test("a place looked up by name is used, not silently dropped", () => {
    // The bug this replaced: the profile held an *index* into the six preset
    // cities, so a place found by searching — index 7 — fell off the end and
    // every reader quietly fell back to "Anywhere", searching the whole world
    // without saying so. The profile now holds the place itself.
    const tucson = { name: "Tucson, Pima County, Arizona", latitude: 32.2229, longitude: -110.9748 };
    const request = toSearchRequest({ ...EMPTY_PROFILE, condition: "asthma", place: tucson });

    expect(request.latitude).toBeCloseTo(32.2229);
    expect(request.longitude).toBeCloseTo(-110.9748);
  });

  test("a place looked up by name shows on its chip", () => {
    const tucson = { name: "Tucson, Pima County, Arizona", latitude: 32.2229, longitude: -110.9748 };
    const chips = describe({ ...EMPTY_PROFILE, condition: "asthma", place: tucson });

    expect(chips.find((c) => c.key === "place")?.value).toContain("Tucson");
  });
});

group("not said means something specific and is not borrowed", () => {
  test("an unstated age is offered back as 'not said'", () => {
    const chips = describe({ ...EMPTY_PROFILE, condition: "asthma" });
    const age = chips.find((chip) => chip.key === "ageYears");

    expect(age?.value).toBeNull();
    expect(age?.absentLabel).toBe("not said");
  });

  test("a radius with nowhere to apply is 'not needed', not 'not said'", () => {
    // "Not said" becomes a question for the study team. A search with no
    // location has no radius to state, and nobody failed to mention it —
    // borrowing the phrase would muddy the one idea the interface must keep
    // clear. PLACES[0] is "Anywhere".
    const chips = describe({ ...EMPTY_PROFILE, condition: "asthma", place: PLACES[0] });
    const within = chips.find((chip) => chip.key === "radiusMiles");

    expect(within?.value).toBeNull();
    expect(within?.absentLabel).toBe("not needed");
  });

  test("a radius that does apply shows its miles", () => {
    const chips = describe({ ...EMPTY_PROFILE, condition: "asthma", place: PLACES[1], radiusMiles: 25 });
    expect(chips.find((chip) => chip.key === "radiusMiles")?.value).toBe("25 miles");
  });
});

group("the fields a person would actually say (D-6)", () => {
  const told: Profile = {
    ...EMPTY_PROFILE,
    condition: "multiple sclerosis",
    diagnosedYear: 2019,
    currentTreatments: ["ocrelizumab"],
    pastTreatments: ["interferon beta-1a", "prednisone"],
  };

  test("they reach the search request", () => {
    const request = toSearchRequest(told);

    expect(request.diagnosed_year).toBe(2019);
    expect(request.current_treatments).toEqual(["ocrelizumab"]);
    expect(request.past_treatments).toEqual(["interferon beta-1a", "prednisone"]);
  });

  test("unstated stays null and empty, never 0 and never ['']", () => {
    // A year of 0 would be a claim nobody made, and [""] is a treatment called
    // nothing. Both are the same bug as an unstated age becoming a newborn.
    const request = toSearchRequest({ ...EMPTY_PROFILE, condition: "x" });

    expect(request.diagnosed_year).toBeNull();
    expect(request.current_treatments).toEqual([]);
    expect(request.past_treatments).toEqual([]);
  });

  test("each one shows on a chip, and reads the way it was typed", () => {
    const byKey = Object.fromEntries(describe(told).map((chip) => [chip.key, chip]));

    expect(byKey.diagnosedYear.value).toBe("2019");
    expect(byKey.currentTreatments.value).toBe("ocrelizumab");
    expect(byKey.pastTreatments.value).toBe("interferon beta-1a, prednisone");
  });

  test("an empty list is not said, rather than an empty string", () => {
    const byKey = Object.fromEntries(describe({ ...EMPTY_PROFILE, condition: "x" }).map((c) => [c.key, c]));

    expect(byKey.currentTreatments.value).toBeNull();
    expect(byKey.currentTreatments.absentLabel).toBe("not said");
  });

  test("a typed list is split the way a person writes one", () => {
    expect(parseList("ocrelizumab, prednisone")).toEqual(["ocrelizumab", "prednisone"]);
    expect(parseList("  ocrelizumab ,,  prednisone  ,")).toEqual(["ocrelizumab", "prednisone"]);
    expect(parseList("")).toEqual([]);
    expect(parseList("   ")).toEqual([]);
  });
});
