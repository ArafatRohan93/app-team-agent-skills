# PDF style guides and screenshots

For HTML designs, including Claude Design page exports, use `html-design.md`: `draft_spec.py --from html` extracts exact values from the CSS.

These are the **lowest-confidence** sources. Nothing from them is exact unless the document prints the value.

## Rules

- **Printed values win.** Use a hex code, pt size or spacing printed in the document as-is: `source: "brand.pdf p.4, printed '#10564F'"`.
- **Sampled values are provisional.** A colour sampled from pixels (compression, anti-aliasing, colour profiles) or a size measured from a screenshot gets `source: "sampled from screenshot home.png at (120,48) — confirm with designer"`. Add a conflict with the sampled value as the only candidate and status `open`, so the user has to confirm it.
- **Only measure screenshots at a known scale.** If the device or scale factor is unknown, don't convert pixels to dp. Ask.
- **Ask for the source file.** A screenshot is never the only source for typography: ask for font names and sizes, or the Figma or Stitch link.
- **Read usage from the visuals.** Which colour fills the main button, which is the page background, which colours the secondary text? Map roles from that, per `material-mapping.md`.

## Steps

1. Write the spec by hand from `spec-format.md`. There's no draft script for images.
2. For a PDF, record the page number for every value. For HTML, record the CSS selector or class.
3. Validate, then list every sampled value for the user alongside the real conflicts.
