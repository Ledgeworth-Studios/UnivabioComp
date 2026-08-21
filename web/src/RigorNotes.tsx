import { RIGOR_PROMISES } from "./rigor";

/**
 * The five promises, on screen rather than in a document nobody opens.
 *
 * `docs/PLAN.md` is explicit that these are requirements and not aspirations,
 * and W5-4 exists because a rule honoured only in the code is a rule the person
 * using the tool has to take on trust. Two of them — sources shown, always link
 * out — are also demonstrated on every card; saying them here as well is not
 * redundancy, it tells the reader what to expect before they have to work it out.
 *
 * Not hidden behind a disclosure triangle, deliberately. A promise you have to
 * click to read is a promise arranged not to be read.
 */
export function RigorNotes() {
  return (
    <section className="rigor" aria-labelledby="rigor-heading">
      <h2 id="rigor-heading">What this tool will and won&rsquo;t do</h2>
      <dl>
        {RIGOR_PROMISES.map((promise) => (
          <div key={promise.rule}>
            <dt>{promise.heading}</dt>
            <dd>{promise.body}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}
