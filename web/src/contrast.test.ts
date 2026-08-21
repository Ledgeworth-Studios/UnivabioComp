import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe as group, expect, test } from "vitest";

/*
 * Read off disk, deliberately. Vite's `?raw` import would be tidier, but vitest
 * stubs CSS imports and hands back an empty string — a version of this test that
 * used it passed every assertion against nothing at all. Reading the file is
 * uglier and cannot do that.
 */
const CSS = readFileSync(fileURLToPath(new URL("./index.css", import.meta.url)), "utf8");

/**
 * Contrast is measured here, against the real stylesheet, so that changing a
 * colour cannot quietly make text unreadable.
 *
 * This test reads `index.css` rather than a copy of the palette kept beside it.
 * A duplicated list of colours would drift, and the day it drifted this test
 * would go on passing while the page it claims to be about failed.
 *
 * Thresholds are WCAG 2.2: **4.5:1** for body text, **3:1** for large text and
 * for anything non-text that has to be seen to identify a control.
 */

/** Pull a custom property out of the stylesheet by name. */
function token(name: string): string {
  const match = CSS.match(new RegExp(`--${name}:\\s*(#[0-9a-fA-F]{3,8})`));
  if (!match) throw new Error(`--${name} is not defined in index.css`);
  return match[1];
}

function channel(value: number): number {
  const c = value / 255;
  return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
}

function luminance(hex: string): number {
  const h = hex.replace("#", "");
  const full = h.length === 3 ? [...h].map((c) => c + c).join("") : h;
  const [r, g, b] = [0, 2, 4].map((i) => parseInt(full.slice(i, i + 2), 16));
  return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b);
}

export function contrast(a: string, b: string): number {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
}

// Backgrounds that are written as literals in the stylesheet rather than tokens.
const CARD = "#ffffff";
const PILL = "#eef2f6";
const CHIP = "#f2f6fa";
const DISCLAIMER = "#eef4f9";
const CAUTION = "#fdf8ec";
const ERROR = "#fdf1f0";

group("the stylesheet was actually read", () => {
  /*
   * The control on everything below. An earlier version of this file imported
   * the CSS through Vite's `?raw`, which vitest stubs to an empty string — every
   * assertion in the file passed while measuring nothing whatsoever. A test that
   * cannot tell the difference between "all colours pass" and "there are no
   * colours" is not a test.
   */
  test("it is not empty", () => {
    expect(CSS.length).toBeGreaterThan(1000);
  });

  test("it contains the token block these tests are about", () => {
    expect(CSS).toContain(":root");
    expect(CSS).toMatch(/--ink:\s*#/);
  });

  test("asking for a token that does not exist is an error, not a silent pass", () => {
    expect(() => token("not-a-real-token")).toThrow();
  });
});

group("body text reaches 4.5:1 wherever it is used", () => {
  const ink = () => token("ink");
  const muted = () => token("muted");
  const page = () => token("page");

  test.each([
    ["ink on the page", () => contrast(ink(), page())],
    ["ink on a card", () => contrast(ink(), CARD)],
    ["ink on the disclaimer panel", () => contrast(ink(), DISCLAIMER)],
    ["ink on the caution panel", () => contrast(ink(), CAUTION)],
    ["ink on the error panel", () => contrast(ink(), ERROR)],
    // The muted grey carries every "registry says" line — the source quotes that
    // rigor rule 2 exists for. If any pairing were going to fail, this is it.
    ["muted on the page", () => contrast(muted(), page())],
    ["muted on a card", () => contrast(muted(), CARD)],
    ["muted on a chip", () => contrast(muted(), CHIP)],
    ["muted on a status pill", () => contrast(muted(), PILL)],
    ["muted on the disclaimer panel", () => contrast(muted(), DISCLAIMER)],
  ])("%s", (_label, measure) => {
    expect(measure()).toBeGreaterThanOrEqual(4.5);
  });
});

group("verdict colours reach 4.5:1, because they are used on text", () => {
  test.each([["met"], ["not-met"], ["unknown"], ["accent"]])("%s on a card", (name) => {
    expect(contrast(token(name), CARD)).toBeGreaterThanOrEqual(4.5);
  });

  test("white on the primary button", () => {
    expect(contrast("#ffffff", token("accent"))).toBeGreaterThanOrEqual(4.5);
  });
});

group("things you must see to find a control reach 3:1", () => {
  // WCAG 1.4.11. The border of an input is the only thing showing where the
  // input is, so it is held to this; a panel's decorative edge is not.
  test.each([
    ["a control border on white", CARD],
    ["a control border on the page", "#f7f9fb"],
    ["a control border inside a chip", CHIP],
  ])("%s", (_label, background) => {
    expect(contrast(token("control-border"), background)).toBeGreaterThanOrEqual(3);
  });

  test("the dashed underline showing a chip value is editable", () => {
    expect(contrast(token("muted"), CHIP)).toBeGreaterThanOrEqual(3);
  });

  test("the focus ring against the surfaces it is drawn on", () => {
    // It is drawn outside the control via outline-offset, so what matters is the
    // background behind, never the button's own fill.
    expect(contrast(token("accent"), CARD)).toBeGreaterThanOrEqual(3);
    expect(contrast(token("accent"), token("page"))).toBeGreaterThanOrEqual(3);
  });
});

group("the stylesheet does not undo any of this", () => {
  test("focus is never removed", () => {
    // `outline: none` and `outline: 0` are how a focus ring dies. If one is ever
    // needed, it must be paired with a replacement — and this test rewritten to
    // say so deliberately.
    expect(CSS).not.toMatch(/outline:\s*(none|0)\s*;/);
  });

  test("a focus style exists at all", () => {
    expect(CSS).toContain(":focus-visible");
  });

  test("the control border is not quietly swapped back to the decorative one", () => {
    expect(CSS).toMatch(/\.field input,\s*\n\.field select \{[^}]*--control-border/);
  });
});
