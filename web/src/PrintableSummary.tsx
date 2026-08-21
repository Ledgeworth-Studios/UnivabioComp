import type { SearchResponse, Trial } from "./api";
import { describe } from "./profile";
import { ELIGIBILITY_WORDING } from "./rigor";
import type { Profile } from "./profile";

/**
 * The thing a person takes to their appointment.
 *
 * `docs/PLAN.md` says the deliverable is a list of questions to ask a study
 * coordinator. W3-3 built the questions and, in doing so, measured how few there
 * are today: across 130 live trials, one. The interesting unknowns live in the
 * free-text criteria, and reading those needs the judge, which is waiting on an
 * API key. A page that printed only questions would usually come out blank.
 *
 * So this prints the whole of what somebody needs at an appointment — which
 * trials, where they are, what would stop them, what nobody has settled, and what
 * to ask — with the questions section already in place for W3-3b to fill.
 *
 * Two things are different here from the on-screen card, and both are because
 * paper is not a browser:
 *
 * - **Every URL is written out in full**, because you cannot click a printout.
 * - **Nothing is collapsed.** The screen hides the eligibility criteria behind a
 *   disclosure triangle; that is not available to someone holding a sheet of
 *   paper, so the criteria are simply left off and the registry address given
 *   instead. Printing a dozen unread criteria per trial would bury the part that
 *   is actually actionable.
 */

function TrialSummary({ trial }: { trial: Trial }) {
  const stoppers = trial.hard_checks.filter((check) => check.verdict === "NOT_MET");
  const unsettled = trial.hard_checks.filter((check) => check.verdict === "UNKNOWN");

  return (
    <article className="print-trial">
      <h3>{trial.brief_title}</h3>
      <p className="print-ids">
        {trial.nct_id} · {trial.overall_status ?? "status unknown"}
        {trial.phases.length > 0 && ` · ${trial.phases.join(", ")}`}
        {trial.lead_sponsor && ` · ${trial.lead_sponsor}`}
      </p>

      {trial.may_not_enrol_individuals && (
        <p className="print-caution">{trial.may_not_enrol_individuals.caution}</p>
      )}

      {trial.nearest_site ? (
        <p>
          <strong>Nearest site:</strong>{" "}
          {trial.nearest_site.facility ?? trial.nearest_site.label}, {trial.nearest_site.label} —{" "}
          {trial.nearest_site.distance_miles} miles
          {trial.site_count > 1 && ` (this study has ${trial.site_count} sites)`}
        </p>
      ) : (
        <p>
          <strong>Sites:</strong> {trial.site_count}
        </p>
      )}

      {stoppers.length > 0 && (
        <div className="print-block">
          <h4>What would stop you</h4>
          <ul>
            {stoppers.map((check) => (
              <li key={check.field}>
                {check.reason}
                {check.source && <em> (registry says: {check.source})</em>}
              </li>
            ))}
          </ul>
        </div>
      )}

      {unsettled.length > 0 && (
        <div className="print-block">
          <h4>Not settled</h4>
          <ul>
            {unsettled.map((check) => (
              <li key={check.field}>
                {check.reason}
                {check.source && <em> (registry says: {check.source})</em>}
              </li>
            ))}
          </ul>
        </div>
      )}

      {trial.questions_for_the_study_team.length > 0 && (
        <div className="print-block">
          <h4>Ask the study team</h4>
          <ul>
            {trial.questions_for_the_study_team.map((item) => (
              <li key={item.question}>
                &ldquo;{item.question}&rdquo; <em>{item.because}</em>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Written out, not linked: a printed page cannot be clicked. */}
      <p className="print-url">Full record: {trial.url}</p>
    </article>
  );
}

export function PrintableSummary({
  profile,
  results,
  printedOn,
}: {
  profile: Profile;
  results: SearchResponse;
  /** Passed in rather than read here, so the same input always renders the same. */
  printedOn: string;
}) {
  const stated = describe(profile).filter((chip) => chip.value !== null);

  return (
    <section className="printable">
      <header>
        {/* An h1, not an h2: this view replaces the whole page, so the masthead's
            h1 is not on screen. Starting at h2 would leave the document with no
            top-level heading and a skipped level. */}
        <h1>Trials to ask about</h1>
        <p className="print-meta">Prepared {printedOn} from ClinicalTrials.gov.</p>
        <p className="print-meta">
          Searched with: {stated.map((chip) => `${chip.label} — ${chip.value}`).join("; ")}
        </p>
        {/* A coordinator will ask what you told it, and the answer should be on
            the sheet rather than in a browser tab that was closed on the way. */}
        <p className="print-meta">
          Anything not listed above wasn&rsquo;t stated, and was treated as unknown rather
          than as a reason to rule anything out.
        </p>
        <p className="print-disclaimer">
          <strong>{ELIGIBILITY_WORDING}</strong> {results.disclaimer} This sheet does
          not diagnose anything and does not advise treatment.
        </p>
      </header>

      {results.trials.map((trial) => (
        <TrialSummary key={trial.nct_id} trial={trial} />
      ))}

      <footer>
        <p className="print-meta">
          Registry records change. Check clinicaltrials.gov for the current version of
          any study listed here before relying on it.
        </p>
      </footer>
    </section>
  );
}
