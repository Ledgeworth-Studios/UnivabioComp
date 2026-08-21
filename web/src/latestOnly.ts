/**
 * Only the newest answer is allowed to win.
 *
 * The page runs a fresh search every time somebody corrects a chip. Two quick
 * corrections mean two searches in flight, and **HTTP gives no promise about
 * which finishes first.** Correct your age from 41 to 12, then immediately to 34,
 * and the reply for 12 can land last — leaving the screen showing which trials
 * would rule out a twelve-year-old, under chips that say 34.
 *
 * For most applications that is an annoyance. Here it means showing somebody
 * eligibility verdicts computed for a person they have already told us they are
 * not, which is the worst thing this page could do quietly.
 *
 * The fix is the smallest one that works: every search takes a ticket, and when
 * it comes back it asks whether it is still the most recent. If it is not, its
 * result is dropped. No cancellation, no abort controllers, no request
 * bookkeeping — a counter and a comparison.
 *
 *     const guard = createLatestOnly();
 *
 *     const isStillWanted = guard.begin();
 *     const answer = await search(...);
 *     if (!isStillWanted()) return;   // somebody has asked something newer
 *
 * This lives in its own file rather than as a `useRef` inside the component
 * because a race is not something you can verify by looking at the page. Here it
 * can be tested directly, which is the whole reason `web/` got a test runner.
 */

export interface LatestOnly {
  /** Take a ticket. The returned function says whether it is still the newest. */
  begin: () => () => boolean;
}

export function createLatestOnly(): LatestOnly {
  let issued = 0;
  return {
    begin() {
      issued += 1;
      const mine = issued;
      return () => mine === issued;
    },
  };
}
