import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe as group, expect, test } from "vitest";
import { ELIGIBILITY_WORDING, RIGOR_PROMISES } from "./rigor";

/**
 * `docs/PLAN.md` says the rigor rules are "testable requirements, not
 * aspirations". This is the test.
 *
 * These are the sentences most likely to be softened by accident — during a
 * layout pass, a copy edit, a tidy-up of duplication. Each one is short and
 * reads like filler. Losing any of them changes what this tool claims about a
 * person's health.
 */

const read = (name: string) =>
  readFileSync(fileURLToPath(new URL(name, import.meta.url)), "utf8");

group("all five rules are present and numbered as the plan numbers them", () => {
  test("there are exactly five", () => {
    expect(RIGOR_PROMISES).toHaveLength(5);
    expect(RIGOR_PROMISES.map((p) => p.rule)).toEqual([1, 2, 3, 4, 5]);
  });

  test("each one says something", () => {
    for (const promise of RIGOR_PROMISES) {
      expect(promise.heading.length).toBeGreaterThan(10);
      expect(promise.body.length).toBeGreaterThan(60);
    }
  });
});

group("rule 1 — it never asserts eligibility", () => {
  test("the wording is the plan's wording", () => {
    expect(ELIGIBILITY_WORDING).toContain("may qualify");
    expect(ELIGIBILITY_WORDING).toContain("only the study team can confirm");
  });

  test("nothing anywhere in the promises claims the person qualifies", () => {
    const all = RIGOR_PROMISES.map((p) => `${p.heading} ${p.body}`)
      .join(" ")
      .toLowerCase();
    for (const claim of ["you are eligible", "you qualify for", "confirms you"]) {
      expect(all).not.toContain(claim);
    }
  });

  test("it is on the printed sheet, which leaves with the person", () => {
    // The results page gets the wording from the server, which owns it and has
    // its own test pinning the exact phrase — a stronger guarantee than this
    // one, because no client can render results without it. The printed sheet
    // adds its own copy, since it is read away from the page by somebody else.
    expect(read("./PrintableSummary.tsx")).toContain("ELIGIBILITY_WORDING");
  });

  test("the results page renders the server's disclaimer rather than its own", () => {
    expect(read("./App.tsx")).toContain("results.disclaimer");
  });
});

group("rule 3 — no diagnosis, no treatment advice", () => {
  test("it is stated, not merely obeyed", () => {
    const rule3 = RIGOR_PROMISES.find((p) => p.rule === 3)!;
    const text = `${rule3.heading} ${rule3.body}`.toLowerCase();
    expect(text).toContain("diagnos");
    expect(text).toContain("treatment");
    expect(text).toContain("doctor");
  });
});

group("rule 4 — what is kept, and what is sent", () => {
  const rule4 = () => RIGOR_PROMISES.find((p) => p.rule === 4)!;

  test("it admits that the condition and place go to the registry", () => {
    // The old wording said nothing was "sent anywhere else", which was untrue —
    // that is the entire mechanism of the product. See docs/decisions/0005.
    expect(rule4().body).toContain("ClinicalTrials.gov");
  });

  test("it says the personal details go no further", () => {
    const text = rule4().body.toLowerCase();
    expect(text).toContain("age");
    expect(text).toContain("no further");
  });

  test("it does not make the claim that was false", () => {
    const everything = RIGOR_PROMISES.map((p) => p.body).join(" ");
    expect(everything).not.toContain("sent anywhere else");
  });

  test("the old false sentence is gone from the interface entirely", () => {
    for (const file of ["./App.tsx", "./PrintableSummary.tsx", "./TrialCard.tsx"]) {
      expect(read(file)).not.toContain("stored or sent anywhere else");
    }
  });
});

group("rule 5 — always link out", () => {
  test("it explains why, not just that", () => {
    const rule5 = RIGOR_PROMISES.find((p) => p.rule === 5)!;
    expect(rule5.body.toLowerCase()).toContain("change");
    expect(rule5.body.toLowerCase()).toContain("date");
  });
});

group("the promises are actually rendered", () => {
  test("the component maps over every one of them", () => {
    const source = read("./RigorNotes.tsx");
    expect(source).toContain("RIGOR_PROMISES.map");
  });

  test("they are not hidden behind a disclosure control", () => {
    // A promise you have to click to read is a promise arranged not to be read.
    const source = read("./RigorNotes.tsx");
    expect(source).not.toContain("<details");
    expect(source).not.toContain("<summary");
  });

  test("the page renders them", () => {
    expect(read("./App.tsx")).toContain("<RigorNotes />");
  });
});
