import { useRef, useState } from "react";
import { search } from "./api";
import type { SearchResponse } from "./api";
import { PLACES } from "./places";
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

  const [results, setResults] = useState<SearchResponse | null>(null);
  const [hasSearched, setHasSearched] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function updateProfile(patch: Partial<Profile>) {
    const next = { ...latestProfile.current, ...patch };
    latestProfile.current = next;
    setProfile(next);
  }

  async function runSearch(using: Profile) {
    if (!using.condition.trim()) return;
    setBusy(true);
    setError(null);
    setHasSearched(true);
    try {
      setResults(await search(toSearchRequest(using)));
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "Something went wrong.");
      setResults(null);
    } finally {
      setBusy(false);
    }
  }

  const place = PLACES[profile.placeIndex];

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

      {hasSearched && (
        <ProfileChips
          profile={profile}
          onChange={updateProfile}
          onCommit={() => void runSearch(latestProfile.current)}
        />
      )}

      {busy && <p className="busy">Searching ClinicalTrials.gov…</p>}

      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}

      {results && !busy && (
        <section className="results">
          <p className="disclaimer">{results.disclaimer}</p>
          <h2>
            {results.returned} shown
            {results.total_count !== null && results.total_count > results.returned
              ? ` of ${results.total_count} recruiting trials found`
              : " recruiting trials"}
          </h2>
          {results.trials.length === 0 && (
            <p className="empty">
              No recruiting trials came back for that search. Try a wider radius, a different
              wording of the condition, or &ldquo;Anywhere&rdquo;.
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
