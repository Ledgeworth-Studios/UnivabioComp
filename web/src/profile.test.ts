import { describe as group, expect, test } from "vitest";
import { EMPTY_PROFILE, describe, toSearchRequest } from "./profile";
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
    const request = toSearchRequest({ ...EMPTY_PROFILE, condition: "asthma", placeIndex: 0 });

    expect(request.latitude).toBeNull();
    expect(request.longitude).toBeNull();
  });

  test("a place sends its coordinates", () => {
    const request = toSearchRequest({ ...EMPTY_PROFILE, condition: "asthma", placeIndex: 1 });

    expect(request.latitude).toBeCloseTo(45.5152);
    expect(request.longitude).toBeCloseTo(-122.6784);
  });

  test("an out-of-range place index falls back to Anywhere instead of crashing", () => {
    const request = toSearchRequest({ ...EMPTY_PROFILE, condition: "asthma", placeIndex: 99 });

    expect(request.latitude).toBeNull();
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
    // clear. placeIndex 0 is "Anywhere".
    const chips = describe({ ...EMPTY_PROFILE, condition: "asthma", placeIndex: 0 });
    const within = chips.find((chip) => chip.key === "radiusMiles");

    expect(within?.value).toBeNull();
    expect(within?.absentLabel).toBe("not needed");
  });

  test("a radius that does apply shows its miles", () => {
    const chips = describe({ ...EMPTY_PROFILE, condition: "asthma", placeIndex: 1, radiusMiles: 25 });
    expect(chips.find((chip) => chip.key === "radiusMiles")?.value).toBe("25 miles");
  });
});
