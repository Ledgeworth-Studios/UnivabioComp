import { describe as group, expect, test } from "vitest";
import { VERDICT_LABEL } from "./verdictLabels";

/**
 * A verdict must never be carried by colour alone (WCAG 1.4.1).
 *
 * Each check on a card has a coloured left border — green, red, amber. To
 * somebody who cannot distinguish them, or who is listening to the page rather
 * than looking at it, that border is nothing at all. The words have to carry the
 * whole meaning on their own, and these tests exist so that a later tidy-up
 * cannot reduce the labels to decoration.
 */

group("every verdict says what it means in words", () => {
  test("all three verdicts have a label", () => {
    expect(Object.keys(VERDICT_LABEL).sort()).toEqual(["MET", "NOT_MET", "UNKNOWN"]);
  });

  test.each(["MET", "NOT_MET", "UNKNOWN"] as const)("%s reads as a sentence", (verdict) => {
    const label = VERDICT_LABEL[verdict];
    expect(label.trim().length).toBeGreaterThan(8);
  });

  test("the three labels are distinct", () => {
    expect(new Set(Object.values(VERDICT_LABEL)).size).toBe(3);
  });

  test("no label names a colour", () => {
    // "Shown in red" would be useless to the people this rule is for.
    const all = Object.values(VERDICT_LABEL).join(" ").toLowerCase();
    for (const colour of ["red", "green", "amber", "orange", "yellow", "grey", "gray"]) {
      expect(all).not.toContain(colour);
    }
  });

  test("MET does not claim the person is eligible", () => {
    // Rigor rule 1, guarded at the exact place it is most tempting to break.
    const met = VERDICT_LABEL.MET.toLowerCase();
    expect(met).not.toContain("eligible");
    expect(met).not.toContain("you qualify");
  });

  test("UNKNOWN does not say who should answer", () => {
    // W3-3 established that half the unknowns are the person's own to answer,
    // so the row states the fact and the questions panel says whose move it is.
    expect(VERDICT_LABEL.UNKNOWN.toLowerCase()).not.toContain("study team");
  });
});
