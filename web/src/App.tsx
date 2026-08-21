import { useRef, useState } from "react";
import { search } from "./api";
import type { SearchResponse } from "./api";
import { createLatestOnly } from "./latestOnly";
import { PLACES } from "./places";
import { PrintableSummary } from "./PrintableSummary";
import { ProfileChips } from "./ProfileChips";
import { EMPTY_PROFILE, toSearchRequest } from "./profile";
import type { Profile } from "./profile";
import { TrialCard } from "./TrialCard";

/**
 * One page. Ask for a condition and a place, then refine by correcting chips.
 *
 * The shape of this page is chosen to match where the product is going. Step 1
 * of the pipeline is meant to be "type a sentence about your situation and a
 * model turns it into a profile" — that is W2-1, and it needs an API key we do
 * not have. Everything after it is built: the profile object, the chips that
 * show it back, and the search that runs on it. So the opening form is the
 * temporary part. When extraction lands it replaces this form, hands back a
 * `Profile`, and the rest of the page does not change.
 *
 * Note what the person is *not* asked at the start: their age, their sex, or
 * whether they are healthy. Those arrive as "not said" chips they can fill in if
 * they want to. Asking up front implies the answers are required; offering them
 * afterwards, next to a sentence saying a blank is a question rather than a
 * rejection, says what this tool actually does.
 */

export default function App() {
  const [profile, setProfile] = useState<Profile>({
    ...EMPTY_PROFILE,
    condition: "multiple sclerosis",
  });

  // The chips edit the profile field by field and then say "done". `commit` has
  // to search the profile as it is at that moment, and React state updates are
  // not visible until the next render — so the latest value is kept here too.
  const latestProfile = useRef(profile);

  // Two quick chip corrections mean two searches in flight, and the older one
  // can answer last. See `latestOnly.ts`: showing verdicts computed for a
  // profile the person has already corrected is the worst thing this page could
  // do quietly, so a late answer is dropped rather than displayed.
  const searches = useRef(createLatestOnly());

  const [results, setResults] = useState<SearchResponse | null>(null);
  // The profile the results on screen were actually computed for. The empty
  // state needs it: "nothing within 50 miles of Portland" has to name the
  // radius that was searched, not whatever the chips say now.
  const [searchedFor, setSearchedFor] = useState<Profile | null>(null);
  const [hasSearched, setHasSearched] = useState(false);
  // The printable view is a mode of this page rather than a separate route, so
  // there is no router to install and explain. What you see is what prints.
  const [printing, setPrinting] = useState(false);
  const [printedOn, setPrintedOn] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function updateProfile(patch: Partial<Profile>) {
    const next = { ...latestProfile.current, ...patch };
    latestProfile.current = next;
    setProfile(next);
  }

  async function runSearch(using: Profile) {
    if (!using.condition.trim()) return;
    const isStillWanted = searches.current.begin();

    setBusy(true);
    setError(null);
    setHasSearched(true);
    // The previous results deliberately stay on screen while this runs. Blanking
    // the page on every chip edit made the whole list flash away and back.
    try {
      const found = await search(toSearchRequest(using));
      if (!isStillWanted()) return;
      setResults(found);
      setSearchedFor(using);
    } catch (problem) {
      if (!isStillWanted()) return;
      setError(problem instanceof Error ? problem.message : "Something went wrong.");
      setResults(null);
    } finally {
      if (isStillWanted()) setBusy(false);
    }
  }

  const place = PLACES[profile.placeIndex];

  if (printing && results) {
    return (
      <main className="print-mode">
        <div className="print-controls no-print">
          <button type="button" onClick={() => setPrinting(false)}>
            Back to results
          </button>
          <button type="button" onClick={() => window.print()}>
            Print or save as PDF
          </button>
        </div>
        <PrintableSummary profile={profile} results={results} printedOn={printedOn} />
      </main>
    );
  }

  return (
    <main>
      <header className="masthead">
        <h1>Why Not This Trial</h1>
        <p className="tagline">
          Clinical trial search that explains what would stop you — and turns everything it
          cannot tell into questions for the study team.
        </p>
      </header>

      {!hasSearched && (
        <form
          onSubmit={(event) => {
            event.preventDefault();
            void runSearch(latestProfile.current);
          }}
        >
          <div className="field">
            <label htmlFor="condition">What condition are you looking for trials for?</label>
            <input
              id="condition"
              value={profile.condition}
              onChange={(e) => updateProfile({ condition: e.target.value })}
              placeholder="e.g. multiple sclerosis"
              required
            />
          </div>

          <div className="field">
            <label htmlFor="place">Near</label>
            <select
              id="place"
              value={profile.placeIndex}
              onChange={(e) => updateProfile({ placeIndex: Number(e.target.value) })}
            >
              {PLACES.map((option, index) => (
                <option key={option.name} value={index}>
                  {option.name}
                </option>
              ))}
            </select>
          </div>

          {place.latitude !== null && (
            <div className="field">
              <label htmlFor="radius">Within (miles)</label>
              <input
                id="radius"
                type="number"
                min={1}
                max={500}
                value={profile.radiusMiles}
                onChange={(e) => updateProfile({ radiusMiles: Number(e.target.value) })}
              />
            </div>
          )}

          <button type="submit" disabled={busy}>
            {busy ? "Searching the registry…" : "Find trials"}
          </button>
          <p className="form-note">
            You&rsquo;ll be able to add your age and anything else afterwards — and leave out
            anything you&rsquo;d rather not say.
          </p>
        </form>
      )}

      {busy && !results && <p className="busy">Searching ClinicalTrials.gov…</p>}

      {hasSearched && (
        <ProfileChips
          profile={profile}
          onChange={updateProfile}
          onCommit={() => void runSearch(latestProfile.current)}
        />
      )}

      {error && (
        <p className="error" role="alert">
          {error}{" "}
          <button type="button" onClick={() => void runSearch(latestProfile.current)}>
            Try again
          </button>
        </p>
      )}

      {results && (
        <section className="results" aria-busy={busy} data-updating={busy ? "yes" : undefined}>
          {busy && (
            <p className="busy" role="status">
              Updating from ClinicalTrials.gov…
            </p>
          )}
          <p className="disclaimer">{results.disclaimer}</p>
          <h2>
            {results.returned} shown
            {results.total_count !== null && results.total_count > results.returned
              ? ` of ${results.total_count} recruiting trials found`
              : " recruiting trials"}
          </h2>
          {results.trials.length === 0 && searchedFor && (
            <p className="empty">
              {PLACES[searchedFor.placeIndex]?.latitude === null ? (
                <>
                  No recruiting trials anywhere matched &ldquo;{searchedFor.condition}
                  &rdquo;. Registry records use clinical names — try the condition&rsquo;s
                  medical name, or a broader one.
                </>
              ) : (
                <>
                  No recruiting trials for &ldquo;{searchedFor.condition}&rdquo; within{" "}
                  {searchedFor.radiusMiles} miles of {PLACES[searchedFor.placeIndex]?.name}.
                  Widen the radius, or search &ldquo;Anywhere&rdquo; to see whether any exist at
                  all.
                </>
              )}
            </p>
          )}
          {results.trials.length > 0 && (
            <p className="take-with-you">
              <button
                type="button"
                onClick={() => {
                  setPrintedOn(new Date().toLocaleDateString());
                  setPrinting(true);
                }}
              >
                Take these to your appointment
              </button>
              <span>
                A one-page summary you can print: what would stop you, what nobody has
                settled, and what to ask the study team.
              </span>
            </p>
          )}

          {results.trials.map((trial) => (
            <TrialCard key={trial.nct_id} trial={trial} />
          ))}
        </section>
      )}

      <footer className="page-footer">
        <p>
          Data from the public{" "}
          <a href="https://clinicaltrials.gov" target="_blank" rel="noreferrer">
            ClinicalTrials.gov
          </a>{" "}
          registry. Nothing you type here is stored or sent anywhere else.
        </p>
      </footer>
    </main>
  );
}
