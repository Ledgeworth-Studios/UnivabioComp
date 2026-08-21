import { useEffect, useRef, useState } from "react";
import type { Place } from "./places";
import { describe } from "./profile";
import type { Profile } from "./profile";

/**
 * What we are searching with, shown back as chips you can correct.
 *
 * This is step 2 of the pipeline in `docs/PLAN.md`, and it exists because of
 * step 1. Once a model reads a free-text sentence and decides you are 41 and
 * female, you have to be able to see that it decided that, and disagree. A
 * profile the user cannot inspect is a profile the user cannot trust, and the
 * chips are half of this project's answer to "why should I believe your tool".
 *
 * A field nobody has stated renders as a "not said" chip rather than being
 * hidden. Hiding it would make the absence invisible; showing it makes the
 * offer — you can tell us, or you can leave it, and leaving it produces a
 * question for the study team rather than a rejection.
 */

function ChipEditor({
  field,
  profile,
  choices,
  onChange,
  onDone,
}: {
  field: keyof Profile;
  profile: Profile;
  /** Every place currently known — the presets, plus anything looked up. */
  choices: Place[];
  onChange: (patch: Partial<Profile>) => void;
  onDone: () => void;
}) {
  // Enter and Escape both close the editor; the value is already committed on
  // every keystroke, so there is nothing to save or cancel.
  function onKeyDown(event: React.KeyboardEvent) {
    if (event.key === "Enter" || event.key === "Escape") {
      event.preventDefault();
      onDone();
    }
  }

  switch (field) {
    case "condition":
      return (
        <input
          autoFocus
          aria-label="Condition"
          value={profile.condition}
          onChange={(e) => onChange({ condition: e.target.value })}
          onBlur={onDone}
          onKeyDown={onKeyDown}
        />
      );
    case "place":
      // Only the preset cities are offered here. Looking up a new place needs a
      // network request, and the OpenStreetMap policy forbids doing that from a
      // keystroke — so that lives on the opening form, behind a button, and this
      // chip switches between places already known. See docs/decisions/0007.
      return (
        <select
          autoFocus
          aria-label="Near"
          value={choices.findIndex((p) => p.name === profile.place.name)}
          onChange={(e) => onChange({ place: choices[Number(e.target.value)] })}
          onBlur={onDone}
        >
          {choices.map((place, index) => (
            <option key={place.name} value={index}>
              {place.name}
            </option>
          ))}
        </select>
      );
    case "radiusMiles":
      return (
        <input
          autoFocus
          type="number"
          min={1}
          max={500}
          aria-label="Within, in miles"
          value={profile.radiusMiles}
          onChange={(e) => onChange({ radiusMiles: Number(e.target.value) })}
          onBlur={onDone}
          onKeyDown={onKeyDown}
        />
      );
    case "ageYears":
      return (
        <input
          autoFocus
          type="number"
          min={0}
          max={130}
          aria-label="Age in years"
          placeholder="leave blank if you'd rather not say"
          value={profile.ageYears ?? ""}
          onChange={(e) =>
            onChange({ ageYears: e.target.value === "" ? null : Number(e.target.value) })
          }
          onBlur={onDone}
          onKeyDown={onKeyDown}
        />
      );
    case "sex":
      return (
        <select
          autoFocus
          aria-label="Sex recorded at birth"
          value={profile.sex ?? ""}
          onChange={(e) => onChange({ sex: e.target.value === "" ? null : e.target.value })}
          onBlur={onDone}
        >
          <option value="">Prefer not to say</option>
          <option value="female">Female</option>
          <option value="male">Male</option>
        </select>
      );
    case "isHealthyVolunteer":
      return (
        <select
          autoFocus
          aria-label="Are you volunteering without the condition being studied?"
          value={profile.isHealthyVolunteer ? "yes" : ""}
          onChange={(e) => onChange({ isHealthyVolunteer: e.target.value === "yes" ? true : null })}
          onBlur={onDone}
        >
          <option value="">Not said</option>
          <option value="yes">I don&rsquo;t have this condition</option>
        </select>
      );
  }
}

//  Clearing a chip means "I'd rather not say", which is a real answer rather
//  than a blank, so each clearable field has a null to go back to.
const CLEARED: Partial<Record<keyof Profile, Partial<Profile>>> = {
  ageYears: { ageYears: null },
  sex: { sex: null },
  isHealthyVolunteer: { isHealthyVolunteer: null },
};

export function ProfileChips({
  profile,
  choices,
  onChange,
  onCommit,
}: {
  profile: Profile;
  choices: Place[];
  onChange: (patch: Partial<Profile>) => void;
  /** Called when an edit finishes. The search re-runs here, not on every
   *  keystroke — typing "41" should not fire two searches at the registry. */
  onCommit: () => void;
}) {
  const [editing, setEditing] = useState<keyof Profile | null>(null);

  /*
   * Give the keyboard back where it came from.
   *
   * Editing a chip replaces its button with an input. When the edit finishes the
   * input is removed from the page — and the browser, having nowhere to put the
   * focus, drops it on the document body. For anyone using a keyboard that means
   * correcting one chip throws them back to the top of the page and they have to
   * tab all the way down again for the next one. It is invisible with a mouse
   * and miserable without one.
   *
   * So each chip's button registers itself here, and when an edit ends the
   * button that started it is focused again.
   */
  const buttons = useRef(new Map<keyof Profile, HTMLButtonElement | null>());
  const returnFocusTo = useRef<keyof Profile | null>(null);

  // Runs after the edit has closed and the button is back in the page. The
  // target is held in a ref rather than in state: it is not something the page
  // renders, and putting it in state would make finishing an edit cause a second
  // render for no visible reason.
  useEffect(() => {
    if (editing !== null || returnFocusTo.current === null) return;
    buttons.current.get(returnFocusTo.current)?.focus();
    returnFocusTo.current = null;
  }, [editing]);

  function finishEditing(field: keyof Profile) {
    returnFocusTo.current = field;
    setEditing(null);
    onCommit();
  }

  return (
    <section className="chips" aria-label="What we are searching with">
      <h2>What we&rsquo;re searching with</h2>
      <ul>
        {describe(profile).map((chip) => (
          <li
            key={chip.key}
            className={`chip ${chip.value === null ? "chip-unsaid" : ""}`.trim()}
          >
            <span className="chip-label">{chip.label}</span>
            {editing === chip.key ? (
              <ChipEditor
                field={chip.key}
                profile={profile}
                choices={choices}
                onChange={onChange}
                onDone={() => finishEditing(chip.key)}
              />
            ) : (
              <>
                <button
                  type="button"
                  className="chip-value"
                  ref={(node) => {
                    buttons.current.set(chip.key, node);
                  }}
                  onClick={() => setEditing(chip.key)}
                  aria-label={`Change ${chip.label}`}
                >
                  {chip.value ?? chip.absentLabel}
                </button>
                {chip.clearable && chip.value !== null && (
                  <button
                    type="button"
                    className="chip-clear"
                    onClick={() => {
                      onChange(CLEARED[chip.key] ?? {});
                      onCommit();
                    }}
                    aria-label={`Clear ${chip.label}, back to not said`}
                    title="I'd rather not say"
                  >
                    ×
                  </button>
                )}
              </>
            )}
          </li>
        ))}
      </ul>
      <p className="chips-note">
        Anything marked <em>not said</em> is not held against you. It becomes a question to ask
        the study team, never a reason you were ruled out. Correct anything that&rsquo;s wrong —
        the results update when you do.
      </p>
    </section>
  );
}
