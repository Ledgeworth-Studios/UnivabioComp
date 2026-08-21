import type { Check, Trial } from "./api";
import { VERDICT_LABEL } from "./verdictLabels";

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
  const nearestOpen = trial.nearest_recruiting_site;

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

      {trial.may_not_enrol_individuals && (
        <aside className="caution" role="note">
          <p className="caution-text">{trial.may_not_enrol_individuals.caution}</p>
          <ul className="caution-evidence">
            {trial.may_not_enrol_individuals.signals.map((signal) => (
              <li key={signal.name}>
                {signal.explanation}
                {signal.quote && <span className="check-source">Record says: {signal.quote}</span>}
              </li>
            ))}
          </ul>
        </aside>
      )}

      {site ? (
        <p className="site">
          Nearest site: <strong>{site.facility ?? site.label}</strong>, {site.label} —{" "}
          {site.distance_miles} miles away
          {trial.site_count > 1 && ` (of ${trial.site_count} sites)`}
          {/* D-7: a site's own status is not the study's overall status. Saying
              nothing here told people a withdrawn site was somewhere to go. */}
          <span className={site.is_recruiting ? "site-status" : "site-status site-status-closed"}>
            This site: {site.status_note}.
          </span>
          {nearestOpen && (
            <span className="site-status">
              Nearest site enrolling now: <strong>{nearestOpen.facility ?? nearestOpen.label}</strong>
              , {nearestOpen.label} — {nearestOpen.distance_miles} miles away.
            </span>
          )}
          {!site.is_recruiting && !nearestOpen && (
            <span className="site-status site-status-closed">
              No site on this trial is listed as enrolling right now. The study team can say
              whether that is still true.
            </span>
          )}
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

      {(trial.questions_for_the_study_team.length > 0 || trial.you_could_tell_us.length > 0) && (
        <section className="questions">
          {trial.questions_for_the_study_team.length > 0 && (
            <>
              <h4>Ask the study team</h4>
              <ul className="ask">
                {trial.questions_for_the_study_team.map((item) => (
                  <li key={item.question}>
                    <span className="ask-question">&ldquo;{item.question}&rdquo;</span>
                    <span className="ask-because">{item.because}</span>
                    {item.source && <span className="check-source">Registry says: {item.source}</span>}
                  </li>
                ))}
              </ul>
            </>
          )}

          {trial.you_could_tell_us.length > 0 && (
            <>
              <h4>Or tell us, and we can check it</h4>
              <ul className="tell-us">
                {trial.you_could_tell_us.map((item) => (
                  <li key={item.field}>{item.prompt}</li>
                ))}
              </ul>
            </>
          )}
        </section>
      )}

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
