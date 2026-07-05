// Shared helpers for the browser tests.
//
// Chip readability is asserted as the real invariant — WCAG contrast between
// the computed text color and background — rather than exact RGB identity.
// Two reasons, both learned from a CI failure:
//   1. Exact-color equality is brittle: it asserts implementation detail
//      (which exact palette value the stylesheet used), not the property we
//      care about (a human can read the label).
//   2. The chips animate (`transition: color .15s, background-color .15s`),
//      so a getComputedStyle read immediately after a click samples a
//      MID-TRANSITION frame — CI saw rgb(148,156,168), which is slate-600
//      partway to white. The assertions below therefore POLL until the
//      contrast requirement holds, letting the transition settle instead of
//      judging an intermediate frame.
const { expect } = require('@playwright/test');

// ---------------------------------------------------------------- colors ---

// Parse "rgb(r, g, b)" / "rgba(r, g, b, a)" into channel values.
function parseRgb(str) {
  const m = /rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)(?:\s*,\s*([\d.]+))?\s*\)/.exec(str);
  if (!m) throw new Error(`Unparseable CSS color: ${JSON.stringify(str)}`);
  return { r: +m[1], g: +m[2], b: +m[3], a: m[4] === undefined ? 1 : +m[4] };
}

// WCAG 2.x relative luminance (0 = black, 1 = white).
function relativeLuminance({ r, g, b }) {
  const lin = (c) => {
    const s = c / 255;
    return s <= 0.03928 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4);
  };
  return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b);
}

// WCAG contrast ratio between two CSS color strings (1..21).
function contrastRatio(fg, bg) {
  const l1 = relativeLuminance(parseRgb(fg));
  const l2 = relativeLuminance(parseRgb(bg));
  const [hi, lo] = l1 >= l2 ? [l1, l2] : [l2, l1];
  return (hi + 0.05) / (lo + 0.05);
}

// ------------------------------------------------------------ chip checks ---

async function snapshotChip(chip) {
  const s = await chip.evaluate((el) => {
    const cs = getComputedStyle(el);
    // Resolve a non-transparent background by walking up if needed.
    let bg = cs.backgroundColor;
    let node = el;
    while (node && (bg === 'transparent' || bg === 'rgba(0, 0, 0, 0)')) {
      node = node.parentElement;
      if (node) bg = getComputedStyle(node).backgroundColor;
    }
    return {
      color: cs.color,
      backgroundColor: bg || 'rgb(255, 255, 255)',
      opacity: cs.opacity,
      text: (el.textContent || '').trim(),
      ariaPressed: el.getAttribute('aria-pressed'),
    };
  });
  return { ...s, contrast: contrastRatio(s.color, s.backgroundColor) };
}

function describe(snap) {
  return (
    `text=${JSON.stringify(snap.text)} aria-pressed=${snap.ariaPressed} ` +
    `fg=${snap.color} bg=${snap.backgroundColor} ` +
    `contrast=${snap.contrast.toFixed(2)} opacity=${snap.opacity}`
  );
}

const MIN_CONTRAST = 4.5;   // WCAG AA for normal text
const DARK_BG_MAX_LUM = 0.3;   // "selected looks dark/navy-ish"
const LIGHT_BG_MIN_LUM = 0.7;  // "rest looks light"

/**
 * Assert a chip is genuinely readable: visible, non-empty label, opacity 1,
 * foreground != background, and WCAG contrast >= 4.5 — POLLED, so the .15s
 * color transition settles instead of an intermediate frame being judged.
 *
 * opts.background: 'dark' additionally requires a dark background (selected
 * state, deep/navy-ish); 'light' requires a light background (rest state).
 * Neither pins an exact color.
 *
 * Returns the final settled snapshot for any extra assertions.
 */
async function expectChipReadable(chip, opts = {}) {
  await expect(chip).toBeVisible();

  let last;
  const settled = (snap) => {
    if (!snap.text) return false;
    if (snap.opacity !== '1') return false;
    if (snap.color === snap.backgroundColor) return false;
    if (snap.contrast < MIN_CONTRAST) return false;
    const bgLum = relativeLuminance(parseRgb(snap.backgroundColor));
    if (opts.background === 'dark' && bgLum > DARK_BG_MAX_LUM) return false;
    if (opts.background === 'light' && bgLum < LIGHT_BG_MIN_LUM) return false;
    return true;
  };

  try {
    await expect
      .poll(async () => { last = await snapshotChip(chip); return settled(last); },
            { timeout: 3_000 })
      .toBe(true);
  } catch (e) {
    throw new Error(
      `Chip failed readability (need contrast >= ${MIN_CONTRAST}` +
      (opts.background ? `, ${opts.background} background` : '') +
      `). Last observed: ${last ? describe(last) : 'no snapshot'}`
    );
  }
  return last;
}

// Select a bundled pack through the app's real endpoint, then land on a page.
async function selectPack(page, slug, hash = '#/categories') {
  const res = await page.request.post('/api/v1/packs/select', { data: { slug } });
  expect(res.ok()).toBeTruthy();
  await page.goto('/' + hash);
  await page.waitForSelector('#app h1');
}

module.exports = {
  selectPack,
  expectChipReadable,
  parseRgb,
  relativeLuminance,
  contrastRatio,
};
