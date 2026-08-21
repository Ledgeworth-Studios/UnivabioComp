import type { Check } from "./api";

/**
 * What each verdict says in words.
 *
 * These live apart from the card for two reasons. The linter's: a file that
 * exports both a component and a constant breaks fast refresh. The better one:
 * these strings *are* the accessibility of the verdicts. Each check has a
 * coloured left border, and to somebody who cannot distinguish those colours, or
 * who is listening to the page rather than looking at it, the border is nothing
 * at all — so the words have to carry the entire meaning alone (WCAG 1.4.1).
 * They are tested in `verdictLabels.test.ts`.
 *
 * `UNKNOWN` deliberately does not say who should answer. It used to read "Ask
 * the study team", which contradicted the questions panel as soon as W3-3
 * established that half the unknowns are things the person can answer
 * themselves — being told to ring a research nurse about your own age is not a
 * good look. The row states the fact; the panel states whose move it is.
 */
export const VERDICT_LABEL: Record<Check["verdict"], string> = {
  MET: "Nothing here rules you out",
  NOT_MET: "This one is a conflict",
  UNKNOWN: "Not settled yet",
};
