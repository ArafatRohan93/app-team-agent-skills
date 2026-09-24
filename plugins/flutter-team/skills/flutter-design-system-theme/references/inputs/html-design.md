# HTML designs: Claude Design page exports, mock-ups and prototypes

This guide covers any design delivered as a web page:
- a Claude Design page export, bundled or rendered;
- a hand-written HTML/CSS mock-up;
- a Tailwind page;
- a React or other JavaScript prototype;
- a single responsive page.

Designs vary a lot. Some are boards of phone frames with a legend section, some are one page. Styles may be inline, in classes, in CSS variables, or produced by scripts. The reader doesn't assume any one layout: it records **how every value is used**, and you map roles from that.

## How the page is read

`draft_spec.py --from html` reads the page in one of two ways, and the evidence file says which one it used:

| Read | When | What it sees |
|---|---|---|
| **rendered** (preferred) | Chrome, Chromium, Edge or Brave is installed, or `CHROME_PATH` is set | Loads the page headless, runs its scripts and reads each visible element's **computed style**. It sees class rules, Tailwind, external stylesheets, CSS variables and DOM built by JavaScript. |
| **static** (fallback) | no browser, or `--render never` | The HTML as written: inline styles, plus `<style>` and local stylesheet rules with simple selectors (tag, `.class`, `#id`, `[attr]`, descendant), with `var()` resolved and colour and font inherited. It can't see scripts, remote CSS or Tailwind utilities, and it prints a **check:** line when the page relies on them. |

- **Colour scheme:** the render forces light mode.
- **Dark mode:** if the page has dark rules (`prefers-color-scheme: dark`, `.dark`, `[data-theme=dark]`), it's rendered a second time in dark mode. Each colour is then paired with its dark counterpart, element by element.
- **Bundles:** a downloaded Claude Design export keeps its HTML as a JSON string inside `<script type="__bundler/template">`. The reader unpacks it itself.

**Screens:**
- **Device frames:** phone-sized boxes (320–480px wide and at least 560px tall) and rounded tablet frames count as screens. Each is labelled with the text just before it.
- **Chrome excluded:** the bezel, the status bar (a time such as "9:41" among the frame's first texts) and the home indicator.
- **No frames:** a page without frames is read as **one screen**. A responsive page (one with a viewport `<meta>`) is laid out 390px wide.
- **Wrong frames:** if the detected screens look wrong, re-run with `--whole-page` to read everything as one screen.

## What you get

- **`design/sources/<file>.evidence.md`**, the inventory to map from:
  - **Colours:** for each value, its uses and screens, its **CSS variable** name if one holds it, its **dark-mode counterpart** if it was rendered in dark mode, what it's *used as* and sample text. "Used as" is one of: screen background, button fill, field fill, card, app bar, bottom bar, chip, text, icon, border, placeholder…
  - **Gradients and shadows.**
  - **Type scale:** size, weight, line height, letter spacing, what it sits on, and sample text.
  - **Radii, spacing values and component heights.**
  - **Fonts,** including `@font-face` weights.
  - **Legend cards:** a preview's colours next to role names the designer wrote.
  - **Colours outside the screens:** swatches, style-guide rows and annotations, each with its nearest label.
  - **CSS custom properties,** light and dark.
  - **Interaction-state rules** (`:hover`, `:focus`, `:disabled`, `::placeholder`), from the static read.
- **A draft spec:**
  - CSS variables named after Material roles are mapped directly. Dark values go to `colors.dark`.
  - Everything else is in `unmapped` with its usage summary.
  - The font family is filled in.

## Steps

1. Run `python3 scripts/draft_spec.py --from html design/sources/<file>.html -o design/theme.spec.json`. Read the **check:** lines it prints:
   - "No colours were found": treat the page as a screenshot (`visual-sources.md`).
   - A static read that relies on scripts: install a browser, or say the evidence is partial.
2. **Take the designer's own names first,** in this order of strength:
   1. **Legend cards** (Claude Design's "Unique Components" section, or any card whose text reads like `surface-container (bg), secondary (icon)`). The evidence lists the preview's colours in the same order.
   2. **CSS variable names** (`--brand`, `--ink-2`). They're names, not roles, but they say what the designer meant.
   3. **Labelled swatches** outside the screens ("Primary", "Brand soft").

   If none of these exist, the whole mapping comes from usage (step 3).
3. **Map the rest by usage,** using `material-mapping.md`:

   | Usage | Role |
   |---|---|
   | fill of the main call-to-action buttons | `primary` |
   | text or icon on it | `onPrimary` |
   | screen background | `surface` |
   | cards on that background | `surfaceContainerLowest`… (by tone) |
   | field fill | `surfaceContainer*`, or the input component's `fill` |
   | most-used text | `onSurface` |
   | second text level | `onSurfaceVariant` |
   | further text levels | `ext.onSurfaceDim`, `ext.onSurfaceMuted` |
   | card and divider borders | `outlineVariant` |
   | field and outlined-button borders | `outline` |
   | chip / status pill fill and text pairs | `*Container` / `on*Container`, or extensions for statuses |
   | error text, destructive buttons | `error` |
   | app bar fill | component `appBar.background` (a role) |

   - **Dark column:** where the evidence has one, put those values in `colors.dark` with the same roles. Don't let them be derived.
   - **Drift:** colours with a handful of uses that sit next to a mapped colour are usually drift. List them in `unmapped` with a reason, and use the mapped role.
4. **Record conflicts** wherever the designer's names and the screens disagree. For example, the legend calls `#46DEFD` primary, but the buttons are drawn `#47F4FE`. Record one too when two cards give one colour different roles, or when a variable is defined but the screens use a near-identical hex.
5. **Type:** map roles by size and use:

   | Style | Role |
   |---|---|
   | app bar / screen title | `titleLarge` |
   | button labels | `labelLarge` |
   | field text | `bodyLarge` |
   | paragraphs | `bodyMedium` |
   | helper text | `bodySmall` |
   | chips | `labelMedium` |
   | status pills | `labelSmall` |
   | big page headings | `headline*` / `display*` |

   - Heavy styles with many uses that fit no role become `extras`. Add `fontFeatures: ["tnum","lnum"]` for prices and IDs, and wherever the CSS has `tabular-nums`.
   - Line heights come from the rendered value in px. For unitless values, use `size × value`.
   - Tiny type inside a mocked document (a PDF preview) isn't app UI: leave it out.
6. **Dimensions:**
   - Take radii and heights from the evidence: cards, fields, buttons, chips.
   - Take spacing from the most common padding and gap values.
   - The most common side padding of a screen is `screenPadding`.
7. **Components:**
   - A field drawn with a fill and no border uses `"border": "none"`. The contrast check then tests the fill against the surface.
   - Pressed and hover colours from the interaction-state rules go to `pressedBackground` via an extension colour.
   - A bottom bar, selected versus unselected chip styling and gradients have no spec slot. Use a component `note`, an `unmapped` entry, or extension fills (a gradient becomes two fills).
8. **Fonts:** web exports embed **woff2**, which Flutter can't load. Bundle the TTFs, or use `google_fonts` for Google fonts, and ask the user which.

## Expect these questions for the designer

Mock-up tools don't check contrast, so expect failures, and take each one to the user:
- light icon colours on tinted tiles;
- a white label on a mid-red button;
- green money text;
- grey placeholder text;
- borderless fields that barely differ from the page.

## Calibration

The reader was tested on:
- **A real Claude Design export** ("Apnar Doctor — Phase 1", 66 screens with legend cards). The bundle, the browser-rendered copy, the static read and the rendered read all give the same 46 colours and 29 legend cards.
- **Four test pages built to differ from it:**
  - class-based CSS with variables and a dark mode, on 402px frames without a bezel;
  - the same page built by JavaScript;
  - a Tailwind CDN page;
  - a responsive single page.

When a new kind of export looks wrong in the evidence, fix the reader (`scripts/html_evidence.py`) and add a line here.
