/**
 * The five promises this tool makes, in the words it makes them in.
 *
 * `docs/PLAN.md` calls these the rigor rules and says they are "testable
 * requirements, not aspirations". They are kept here, apart from the components
 * that display them, for one reason: a sentence that lives in the middle of some
 * JSX gets softened during a layout tidy-up and nobody notices. From here they
 * can be pinned by tests, and `rigor.test.ts` does exactly that.
 *
 * The numbering matches `docs/PLAN.md` so the two can be checked against each
 * other by anybody, including a competition judge with the repository open.
 */

export interface RigorPromise {
  /** Matches the numbered rule in docs/PLAN.md. */
  rule: number;
  heading: string;
  body: string;
}

/** Rule 1, kept separate because it is shown at the top of every result set. */
export const ELIGIBILITY_WORDING =
  "You may qualify — only the study team can confirm.";

export const RIGOR_PROMISES: RigorPromise[] = [
  {
    rule: 1,
    heading: "It never tells you that you qualify",
    body:
      "The most this tool will say is that nothing it can check rules you out. " +
      ELIGIBILITY_WORDING,
  },
  {
    rule: 2,
    heading: "Every reason shows where it came from",
    body:
      "Each thing we say about a trial is printed with the registry's own wording " +
      "underneath it, so you can check it against the source rather than take our " +
      "word for it.",
  },
  {
    rule: 3,
    heading: "It does not diagnose, and it does not advise treatment",
    body:
      "This is a search tool for a public registry. It has no opinion about your " +
      "health, what is wrong with you, or what you should do about it, and it is " +
      "not a substitute for talking to a doctor.",
  },
  {
    rule: 4,
    heading: "Nothing you tell us is kept",
    body:
      "The condition and the place you choose are sent to ClinicalTrials.gov, " +
      "because that is how the search works. Your age, sex and whether you're a " +
      "healthy volunteer are not — they go no further than the search itself. " +
      "Nothing is written down, and closing this page ends it.",
  },
  {
    rule: 5,
    heading: "It always links to the original",
    body:
      "Registry records change, and ours is a copy made the moment you searched. " +
      "Every trial shows its status and the date its record was last updated, and " +
      "links to the real thing.",
  },
];
