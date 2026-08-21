import type { Check, Trial } from "./api";

/**
 * One trial, as much of the registry's own words as fits, and nothing invented.
 *
 * Two rules from `docs/PLAN.md` are visible here rather than merely honoured in
 * the backend. Every check shows the registry wording it was decided from (rule
 * 2), and every card links out to the trial's own page, because our copy of the
 * registry goes stale and theirs does not (rule 5).
 *
 * Note what this card does *not* say. It never tells the reader they are
 * eligible, or that they match. A check that came out `NOT_MET` is phrased as
 * something about the trial — "this trial enrols ages 18 and older" — and the
 * only claim ever made about the reader is one they made about themselves.
 */

const VERDICT_LABEL: Record<Check["verdict"], string> = {
  MET: "Nothing here rules you out",
  NOT_MET: "This one is a conflict",
  UNKNOWN: "Ask the study team",
};

function CheckRow({ check }: { check: Check }) {
  return (
    <li className={`check check-${check.verdict.toLowerCase()}`}>
      <span className="check-verdict">{VERDICT_LABEL[check.verdict]}</span>
      <span className="check-reason">{check.reason}</span>
      {check.source && <span className="check-source">Registry says: {check.source}</span>}
    </li>
  );
}

export function TrialCard({ trial }: { trial: Trial }) {
  const site = trial.nearest_site;

  return (
    <article className="trial">
      <header>
        <h3>{trial.brief_title}</h3>
        <p className="trial-meta">
          <span className="pill">{trial.overall_status ?? "status unknown"}</span>
          {trial.phases.length > 0 && <span className="pill">{trial.phases.join(", ")}</span>}
          <span className="nct">{trial.nct_id}</span>
        </p>
      </header>

      {site ? (
        <p className="site">
          Nearest site: <strong>{site.facility ?? site.label}</strong>, {site.label} —{" "}
          {site.distance_miles} miles away
          {trial.site_count > 1 && ` (of ${trial.site_count} sites)`}
        </p>
      ) : (
        <p className="site site-unknown">
          {trial.site_count} site{trial.site_count === 1 ? "" : "s"}; choose a location to see
          which is nearest.
        </p>
      )}

      <ul className="checks">
        {trial.hard_checks.map((check) => (
          <CheckRow key={check.field} check={check} />
        ))}
      </ul>

      {trial.criteria.length > 0 && (
        <details className="criteria">
          <summary>
            {trial.criteria.length} eligibility criteria, in the registry&rsquo;s own words
          </summary>
          <ul>
            {trial.criteria.map((criterion) => (
              <li key={criterion.index}>
                <span className="kind">{criterion.kind.toLowerCase()}</span> {criterion.text}
              </li>
            ))}
          </ul>
          <p className="criteria-note">
            These have not been checked against your situation yet — reading them is the part
            that needs a model, and it is not built.
          </p>
        </details>
      )}

      <footer>
        <a href={trial.url} target="_blank" rel="noreferrer">
          Read this trial on ClinicalTrials.gov
        </a>
        {trial.last_update_post_date && (
          <span className="updated"> · registry record updated {trial.last_update_post_date}</span>
        )}
      </footer>
    </article>
  );
}
