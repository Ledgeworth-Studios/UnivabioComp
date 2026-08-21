import { describe as group, expect, test } from "vitest";
import { createLatestOnly } from "./latestOnly";

/**
 * The race this guards is the one bug on this page that would be actively
 * dangerous rather than merely annoying: displaying eligibility verdicts
 * computed for a profile the person has already corrected.
 */

group("only the newest search may show its results", () => {
  test("a single search is the newest", () => {
    const guard = createLatestOnly();
    expect(guard.begin()()).toBe(true);
  });

  test("an older search is refused once a newer one has started", () => {
    const guard = createLatestOnly();

    const first = guard.begin();
    const second = guard.begin();

    expect(second()).toBe(true);
    expect(first()).toBe(false);
  });

  test("the newest wins no matter what order the answers come back in", () => {
    // The actual failure: correct the age to 12, then to 34; the reply for 12
    // arrives last and would otherwise overwrite the reply for 34.
    const guard = createLatestOnly();

    const forTwelve = guard.begin();
    const forThirtyFour = guard.begin();

    // Replies land in the wrong order.
    expect(forThirtyFour()).toBe(true);
    expect(forTwelve()).toBe(false);
  });

  test("a ticket stays valid while it is the newest, however often it is asked", () => {
    const guard = createLatestOnly();
    const only = guard.begin();

    expect(only()).toBe(true);
    expect(only()).toBe(true);
  });

  test("many in flight at once leaves exactly one winner", () => {
    const guard = createLatestOnly();
    const tickets = Array.from({ length: 6 }, () => guard.begin());

    expect(tickets.filter((isNewest) => isNewest()).length).toBe(1);
    expect(tickets[tickets.length - 1]()).toBe(true);
  });

  test("two guards do not interfere with each other", () => {
    const one = createLatestOnly();
    const two = createLatestOnly();

    const fromOne = one.begin();
    two.begin();

    expect(fromOne()).toBe(true);
  });
});
