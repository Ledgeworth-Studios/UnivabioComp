import { useState } from "react";
import { search } from "./api";
import type { SearchResponse } from "./api";
import { PLACES } from "./places";
import { TrialCard } from "./TrialCard";

/**
 * One page, one query path: describe the search, get trials back.
 *
 * This is the skeleton the rest of the product hangs off. The form deliberately
 * asks for very little and marks all of it optional, because the whole argument
 * of this tool is that not knowing something is a real answer — a blank field
 * becomes "ask the study team", never a guess. Extracting these fields from a
 * free-text sentence is W2-1 and needs a model; typing them is the honest
 * fallback that works today.
 *
 * Loading, empty and error states are handled but not designed. Week 5 does the
 * design pass, the accessibility pass, and the mobile layout.
 */

export default function App() {
  const [condition, setCondition] = useState("multiple sclerosis");
  const [placeIndex, setPlaceIndex] = useState(1);
  const [radius, setRadius] = useState(50);
  const [age, setAge] = useState("");
  const [sex, setSex] = useState("");
  const [healthyVolunteer, setHealthyVolunteer] = useState(false);

  const [results, setResults] = useState<SearchResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const place = PLACES[placeIndex];

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      setResults(
        await search({
          condition,
          latitude: place.latitude,
          longitude: place.longitude,
          radius_miles: radius,
          // An empty box means "I didn't say", which is not the same as zero.
          age_years: age === "" ? null : Number(age),
          sex: sex === "" ? null : sex,
          is_healthy_volunteer: healthyVolunteer ? true : null,
        }),
      );
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "Something went wrong.");
      setResults(null);
    } finally {
      setBusy(false);
    }
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

      <form onSubmit={onSubmit}>
        <div className="field">
          <label htmlFor="condition">Condition</label>
          <input
            id="condition"
            value={condition}
            onChange={(e) => setCondition(e.target.value)}
            placeholder="e.g. multiple sclerosis"
            required
          />
        </div>

        <div className="field">
          <label htmlFor="place">Near</label>
          <select
            id="place"
            value={placeIndex}
            onChange={(e) => setPlaceIndex(Number(e.target.value))}
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
              value={radius}
              onChange={(e) => setRadius(Number(e.target.value))}
            />
          </div>
        )}

        <fieldset>
          <legend>About you — every one of these is optional</legend>

          <div className="field">
            <label htmlFor="age">Age</label>
            <input
              id="age"
              type="number"
              min={0}
              max={130}
              value={age}
              onChange={(e) => setAge(e.target.value)}
              placeholder="leave blank if you'd rather not say"
            />
          </div>

          <div className="field">
            <label htmlFor="sex">Sex recorded at birth</label>
            <select id="sex" value={sex} onChange={(e) => setSex(e.target.value)}>
              <option value="">Prefer not to say</option>
              <option value="female">Female</option>
              <option value="male">Male</option>
            </select>
          </div>

          <div className="field field-check">
            <input
              id="healthy"
              type="checkbox"
              checked={healthyVolunteer}
              onChange={(e) => setHealthyVolunteer(e.target.checked)}
            />
            <label htmlFor="healthy">
              I don&rsquo;t have this condition — I want to volunteer as a healthy participant
            </label>
          </div>
        </fieldset>

        <button type="submit" disabled={busy}>
          {busy ? "Searching the registry…" : "Find trials"}
        </button>
      </form>

      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}

      {results && (
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
              wording of the condition, or “Anywhere”.
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
