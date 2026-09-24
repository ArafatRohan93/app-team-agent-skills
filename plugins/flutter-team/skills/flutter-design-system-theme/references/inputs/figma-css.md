# Figma "Copy as CSS"

The designer selects frames in Figma, right-clicks, and picks **Copy/Paste as → Copy as CSS**. Figma then copies one CSS block per layer. It needs no plugin, export settings or paid seat. Save the pasted text as `design/sources/<name>.figma.css.txt`.

## What's in it

```css
/* A1 · Add product — Mobile */   ← screen frame (390 × 844)

/* Button */                      ← layer name

/* Auto layout */
display: flex;
padding: 0px 24px;
width: 358px;
height: 52px;
background: #143F30;
border-radius: 14px;

/* Inside auto layout */
order: 0;                         ← position among its siblings

/* Buy golf equipment */          ← text layers are named after their text
font-family: 'SF Pro';
font-weight: 600;
font-size: 16px;
color: #FFFFFF;
```

- **Exact values:** colours, type, sizes, padding, gap, radius, borders, shadows.
- **Layer names say what things are:** `Button`, `field`, `App bar`, `Status bar`. Text layers carry their text, so every text style comes with a real sample.
- **Named styles and variables:**
  - A colour or effect style appears as a comment right above its declaration (`/* Base / White */`).
  - Bound Figma variables appear as `var(--name, #hex)`.
  - Both become named colours in the evidence.
- **Missing:**
  - **Nesting:** the copy is a flat list.
  - **Roles:** nothing says which colour is `primary`.
  - **States and dark mode:** pressed, disabled or dark versions appear only if the designer drew them.

## What the reader does

```bash
python3 scripts/draft_spec.py --from figma-css design/sources/screens.figma.css.txt -o design/theme.spec.json
# with a token file (best):
python3 scripts/draft_spec.py --from dtcg design/sources/tokens.json --screens design/sources/screens.figma.css.txt -o design/theme.spec.json
```

**Rebuilding the nesting:**
- The layers come depth-first, and auto-layout children carry `order: 0, 1, 2…`. A layer with order 0 is the first child of the layer before it. A layer with order *k* is the next sibling of an earlier layer with order *k−1*.
- When several earlier layers could be that sibling, the reader picks the one whose parent the new layer fits across and overflows least. Scroll content is allowed to overflow.
- Free-floating (absolute) layers attach to the auto-layout layer above them.
- The result is approximate, but good enough to know which label sits on which button.

**Reading the layers:**
- **Screens:** layers 320–1400 wide and at least 560 tall, outside auto layout. A variant such as "A1 … · full content" is merged into the fuller version.
- **Chrome:** the status bar, home indicator and keyboard are skipped, by name.
- **Kinds come from the name first:**
  - `button` → button
  - `input` / `select` / `text field` → field
  - `app bar` / `nav bar` → app bar
  - `tab bar` / `action bar` → bottom bar
  - `chip` / `tag` / `badge` → chip
  - `card` / `tile` / `panel` → card
  - `divider` → divider

  A text layer inside a button, chip or field takes that kind, so a button label counts as "text · button".
- **Icons:** icon frames and vector layers count as icon colours, not fills.
- **Hidden layers** (`display: none`) are skipped.
- **Variable font weights** (SF Pro's 590 and 510) round to 600 and 500.

**Output:**
- **Evidence:** `<file>.evidence.md`, in the same format as the HTML reader (see `html-design.md`), mapped the same way: by usage, per `material-mapping.md`.

## Fonts

**SF Pro** (and SF Compact, New York) is Apple's system font. It can't be bundled in an app, so the draft leaves `typography.fontFamily` unset and adds a note. Unset means iOS shows SF and Android shows Roboto. Ask the user whether that's right, or whether both platforms should use a bundled font.

## Tips for the designer

- **Copy whole screens,** not loose layers. The reader needs screen frames to group the evidence.
- **Name layers by role** (`Button / Primary`, `Card`, `Input`). Figma's defaults like `Frame 37` tell the reader nothing.
- **Bind variables or styles to colours.** The copy then carries their names, and names beat inference.
- **Draw the states** that matter (pressed, disabled, error) if the theme should get them.

## Calibration

The reader was tested on a real Copy as CSS from an ecommerce "sell an item" flow:
- 1,105 layers, 9 screens with 4 "full content" variants;
- SF Pro type;
- one named colour style and one shadow style.

Against that app's DTCG tokens, `--screens` found:
- the text colour (`#0F172B` drawn, `#000000` in the tokens);
- the border grey (`#C8C8C8` drawn, `#E4E7EC` in the tokens);
- brand-green drift (`#143F30` vs `#134030`);
- a warning set that no token covers.
