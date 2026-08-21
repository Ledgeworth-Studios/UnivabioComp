import { useState } from "react";
import { findPlaces } from "./api";
import type { FoundPlace } from "./api";
import type { Place } from "./places";

/**
 * Type a place name, press the button, pick from what comes back.
 *
 * **The button is not a style choice.** The OpenStreetMap Foundation's usage
 * policy for Nominatim forbids auto-complete search — their words — and the
 * service runs on donated servers with very limited capacity. So the lookup is
 * something the person asks for, never something a keystroke sets off. There is
 * no `onChange` handler here that touches the network, and there must never be
 * one. See `docs/decisions/0007`.
 *
 * "Portland" really does return Oregon, Maine, Texas, Australia and Indiana, so
 * the candidates are shown and the person chooses. Taking the first result would
 * quietly search Oregon for somebody in Maine.
 */
export function PlaceSearch({ onChoose }: { onChoose: (place: Place) => void }) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<FoundPlace[] | null>(null);
  const [attribution, setAttribution] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function look() {
    if (!query.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const found = await findPlaces(query);
      setResults(found.places);
      setAttribution(found.attribution);
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "The place lookup failed.");
      setResults(null);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="place-search">
      <label htmlFor="place-query">Or search for somewhere else</label>
      <div className="place-search-row">
        <input
          id="place-query"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => {
            // Enter submits, exactly like the button. Typing does nothing.
            if (e.key === "Enter") {
              e.preventDefault();
              void look();
            }
          }}
          placeholder="e.g. Tucson, or Leeds"
        />
        <button type="button" onClick={() => void look()} disabled={busy || !query.trim()}>
          {busy ? "Looking…" : "Find"}
        </button>
      </div>

      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}

      {results !== null && results.length === 0 && (
        <p className="place-empty">
          Nothing found for &ldquo;{query}&rdquo;. Try adding a region or country — or pick a
          city from the list above.
        </p>
      )}

      {results !== null && results.length > 0 && (
        <>
          <ul className="place-results">
            {results.map((place) => (
              <li key={`${place.latitude},${place.longitude}`}>
                <button
                  type="button"
                  onClick={() =>
                    onChoose({
                      name: place.name,
                      latitude: place.latitude,
                      longitude: place.longitude,
                    })
                  }
                >
                  {place.name}
                </button>
              </li>
            ))}
          </ul>
          <p className="place-attribution">{attribution}</p>
        </>
      )}
    </div>
  );
}
