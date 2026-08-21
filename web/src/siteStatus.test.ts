import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe as group, expect, test } from "vitest";

/**
 * D-7. The API has always carried each site's own recruiting status, and for
 * most of this project's life both renderers threw it away — so a study that was
 * `RECRUITING` overall could advertise a `WITHDRAWN` site 2.8 miles away with
 * nothing said about it. Measured on live data, that was one result in six.
 *
 * This is the same shape as the defect this codebase keeps rediscovering: a
 * field fetched, carried through the API, and read by nothing. These tests are
 * here so it cannot happen a third time silently.
 *
 * They read the components off disk rather than rendering them. There is no
 * component-rendering library in this project and adding one to assert on two
 * lines of JSX would cost more explanation than it buys — the same reasoning
 * `contrast.test.ts` and `rigor.test.ts` already follow.
 */

const read = (name: string) =>
  readFileSync(fileURLToPath(new URL(name, import.meta.url)), "utf8");

const CARD = read("./TrialCard.tsx");
const SHEET = read("./PrintableSummary.tsx");
const TYPES = read("./api.ts");

group("the test is reading real files", () => {
  test("each one is a component that draws a site", () => {
    for (const source of [CARD, SHEET]) {
      expect(source.length).toBeGreaterThan(200);
      expect(source).toContain("nearest_site");
    }
  });
});

group("the status of the nearest site is shown, not dropped", () => {
  test.each([
    ["the trial card", CARD],
    ["the printable sheet", SHEET],
  ])("%s renders status_note", (_name, source) => {
    expect(source).toContain("status_note");
  });

  test.each([
    ["the trial card", CARD],
    ["the printable sheet", SHEET],
  ])("%s offers the nearest site that is open", (_name, source) => {
    expect(source).toContain("nearest_recruiting_site");
  });

  test("the card distinguishes an open site from a shut one visually", () => {
    expect(CARD).toContain("is_recruiting");
    expect(CARD).toContain("site-status-closed");
  });
});

group("the wording never promises a site will take the person", () => {
  test.each([
    ["the trial card", CARD],
    ["the printable sheet", SHEET],
  ])("%s makes no claim of enrolment", (_name, source) => {
    const text = source.toLowerCase();
    for (const claim of ["you can enrol", "you can enroll", "you are eligible", "will enrol you"]) {
      expect(text).not.toContain(claim);
    }
  });
});

group("the type carries the fields the renderers rely on", () => {
  test("Site has the status fields", () => {
    expect(TYPES).toContain("is_recruiting: boolean");
    expect(TYPES).toContain("status_note: string");
  });

  test("Trial has the nearest open site", () => {
    expect(TYPES).toContain("nearest_recruiting_site: Site | null");
  });
});
