#!/usr/bin/env python3
"""Figma "Copy as CSS" text for draft_spec.py --from figma-css (and --screens).

Selecting layers in Figma and choosing Copy as CSS gives one block per layer:

    /* Button */                      ← layer name (text layers are named after their text)

    /* Auto layout */                 ← section markers
    display: flex;
    …
    background: #143F30;
    border-radius: 14px;

    /* Inside auto layout */
    flex: none;
    order: 0;                         ← position among its auto-layout siblings

The copy is flat: nesting isn't written. It's rebuilt from the auto-layout `order`
values (depth-first order, 0 = first child, k = next sibling of the k-1 layer), and
absolutely positioned layers attach to the last auto-layout layer. That's approximate,
but good enough for usage evidence.

The layers are then written as HTML that html_evidence reads, with what the layer
*names* state: `data-x-frame` for screens, `data-x-chrome` for the status bar and
home indicator, `data-x-kind` for buttons, fields, app bars, cards, chips… Icon
layers become SVG shapes, so their fills count as icon colours. Colour and text
style names written as comments above a declaration (`/* Brand/Green 900 */`), and
Figma variables (`var(--brand-900, #143F30)`), become CSS custom properties, so the
evidence can name the colours.
"""

import html as _html
import re
from pathlib import Path

COMMENT = re.compile(r"^/\*\s*(.*?)\s*\*/$")
DECL = re.compile(r"^([a-z-]+)\s*:\s*(.+?);?\s*$")
LH_NOTE = re.compile(r"identical to box height|^or \d+%|^\d+(\.\d+)?%$", re.I)
SECTIONS = {"auto layout", "inside auto layout"}
FIGMA_VAR = re.compile(r"var\(\s*(--[\w-]+)\s*,\s*([^)]+?)\s*\)")
CHROME = re.compile(r"status ?bar|home ?indicator|notch|dynamic ?island|keyboard|device ?frame|bezel", re.I)
ICON = re.compile(r"\bicons?\b|^ic[_-]|glyph|symbol|logo", re.I)
SHAPE = re.compile(r"^(vector|union|subtract|intersect|exclude|path|star|polygon|arrow|line|shape)\b", re.I)
KIND_BY_NAME = [
    (re.compile(r"status ?bar|home ?indicator", re.I), None),
    (re.compile(r"\b(app ?bar|nav(igation)? ?bar|top ?bar|header|toolbar)\b", re.I), "app bar"),
    (re.compile(r"\b(tab ?bar|bottom ?(nav|bar)|action ?bar)\b", re.I), "bottom bar"),
    (re.compile(r"\b(button|btn|cta)\b", re.I), "button"),
    (re.compile(r"\b(input|text ?field|select|dropdown|search ?(field|bar|box)|textarea)\b", re.I), "field"),
    (re.compile(r"\b(chip|tag|pill|badge)\b", re.I), "pill/chip"),
    (re.compile(r"\b(card|tile|panel|sheet)\b", re.I), "card/panel"),
    (re.compile(r"\b(divider|separator|hairline)\b", re.I), "divider"),
]
VARIANT_SUFFIX = re.compile(r"\s*[·\-–—|]\s*(full content|full|scrolled|expanded|long|extended)\s*$", re.I)


def looks_like(text):
    """Copy-as-CSS text: layer comments and bare declarations, no `{…}` rule blocks."""
    head = text[:20000]
    return bool(re.search(r"^/\* .+ \*/$", head, re.M) and re.search(r"^[a-z-]+: [^;]+;$", head, re.M)
                and not re.search(r"\{\s*$", head, re.M))


def parse(text):
    """[{"name", "decls", "styles"}] per layer, in document order."""
    lines = [ln.rstrip() for ln in text.splitlines()]
    layers, cur, style_name = [], None, None
    for i, raw in enumerate(lines):
        line = raw.strip()
        prev_blank = i == 0 or not lines[i - 1].strip()
        next_line = lines[i + 1].strip() if i + 1 < len(lines) else ""
        m = COMMENT.match(line)
        if m:
            txt = m.group(1)
            if LH_NOTE.search(txt):
                continue  # "identical to box height, or 133%"
            if txt.lower() in SECTIONS:
                style_name = None
            elif prev_blank and not next_line:
                cur = {"name": txt, "decls": {}, "styles": {}}
                layers.append(cur)
                style_name = None
            else:
                style_name = txt  # a colour / text style named above its declarations
            continue
        if not line:
            style_name = None
            continue
        d = DECL.match(line)
        if d and cur is not None:
            prop, val = d.group(1), d.group(2)
            cur["decls"][prop] = val
            if style_name:
                cur["styles"][prop] = style_name
    return layers


def _num(v):
    m = re.match(r"^-?\d+(\.\d+)?", v or "")
    return float(m.group(0)) if m else None


def _is_screen(decls):
    w, h = _num(decls.get("width")), _num(decls.get("height"))
    return bool(w and h and 320 <= w <= 1400 and h >= 560 and "order" not in decls
                and decls.get("position") != "absolute")


def _fill(node_decls, parent):
    """How full `parent` would be along its auto-layout direction with this layer added (1.0 = exactly full),
    or None if the layer can't fit across it. Picks the right one of several same-order candidates."""
    if parent["parent"] is None:
        return 0.0  # the root holds anything
    pd = parent["decls"]
    row = pd.get("display") == "flex" and pd.get("flex-direction", "row") == "row"
    main, cross = ("width", "height") if row else ("height", "width")
    a, b = _num(node_decls.get(cross)), _num(pd.get(cross))
    if a is not None and b is not None and a > b + 0.5:
        return None
    if pd.get("display") != "flex" or pd.get("flex-wrap") == "wrap" or node_decls.get("position") == "absolute":
        return 0.0
    size, limit = _num(node_decls.get(main)), _num(pd.get(main))
    if size is None or not limit:
        return 0.0
    gap = _num(pd.get("gap")) or 0
    used = [_num(c["decls"].get(main)) or 0 for c in parent["children"]
            if c["decls"].get("position") != "absolute" and c["decls"].get("display") != "none"]
    return (sum(used) + gap * len(used) + size) / limit


def build_tree(layers):
    """Rebuild nesting from auto-layout order. Returns the root's children (screens and stray layers)."""
    root = {"name": "", "decls": {}, "styles": {}, "children": [], "parent": None, "order": None}
    last = root
    for layer in layers:
        d = layer["decls"]
        order = int(d["order"]) if re.fullmatch(r"\d+", d.get("order", "")) else None
        node = {**layer, "children": [], "order": order}
        if _is_screen(d) and order is None:
            parent = root
        elif order is None:
            parent = last
            if d.get("position") == "absolute":
                # a free-floating layer belongs to the last auto-layout layer (or screen) above it
                while parent is not root and parent["order"] is None and parent["decls"].get("position") == "absolute":
                    parent = parent["parent"]
        elif order == 0:
            parent = last  # depth-first: a first child comes right after its parent
        else:
            # the next sibling of the deepest earlier layer with order-1 whose parent has room for it
            candidates, probe = [], last
            while probe is not root:
                if probe["order"] == order - 1:
                    candidates.append(probe)
                probe = probe["parent"]
            # it must fit across; of those, the parent it overflows least (scroll content overflows a bit)
            scored = [(f, i, c) for i, c in enumerate(candidates) if (f := _fill(d, c["parent"])) is not None]
            best = min(scored, key=lambda x: (max(x[0], 1.0), x[1]))[2] if scored else \
                (candidates[0] if candidates else last)
            parent = best["parent"] or root
        while parent is not root and "font-size" in parent["decls"]:
            parent = parent["parent"]  # text layers have no children
        node["parent"] = parent
        parent["children"].append(node)
        last = node
    return root


def _kind(name, decls):
    visual = any(k.startswith(("background", "border")) for k in decls)
    for pattern, kind in KIND_BY_NAME:
        if pattern.search(name):
            if kind in ("field", "button", "pill/chip", "card/panel") and not visual:
                return None  # a wrapper named "field" around the real box
            return kind
    return None


def _style(decls, weights):
    out = []
    for k, v in decls.items():
        if k in ("order", "flex", "flex-grow", "align-self", "font-stretch", "font-style"):
            continue
        if k == "font-weight" and re.fullmatch(r"\d+", v) and int(v) % 100:
            weights.add(int(v))
            v = str(min(900, max(100, round(int(v) / 100) * 100)))  # SF Pro's 590 / 510 → 600 / 500
        out.append(f"{k}:{v}")
    return ";".join(out)


def to_html(text):
    """(html, info) — info has screens, merged variants and rounded weights."""
    layers = parse(text)
    tree = build_tree(layers)
    props, weights = {}, set()
    for layer in layers:
        for prop, name in layer["styles"].items():
            if prop in ("color", "background", "background-color", "border", "fill"):
                m = re.search(r"#[0-9A-Fa-f]{6,8}\b|rgba?\([^)]*\)", layer["decls"].get(prop, ""))
                if m:
                    props["--" + re.sub(r"[^\w-]+", "-", name).strip("-")] = m.group(0)
        for val in layer["decls"].values():
            for var, fallback in FIGMA_VAR.findall(val):
                props[var] = fallback

    screens = [n for n in tree["children"] if _is_screen(n["decls"])]
    # "A1 · Add product — Mobile · full content" repeats "A1 · Add product — Mobile": keep the fuller one
    best, merged = {}, []
    for s in screens:
        base = VARIANT_SUFFIX.sub("", s["name"])
        size = _count(s)
        if base in best:
            merged.append(s["name"] if size <= best[base][1] else best[base][0]["name"])
            if size <= best[base][1]:
                continue
        best[base] = (s, size)
    keep = {id(s) for s, _ in best.values()}

    def emit(node, in_icon=False, host=None):
        d, name = node["decls"], node["name"]
        esc = _html.escape(name)
        if in_icon:
            fill = d.get("background") or d.get("background-color")
            stroke = re.search(r"(#[0-9A-Fa-f]{6,8}\b|rgba?\([^)]*\))", d.get("border", ""))
            parts = [f"fill:{fill}" if fill else "fill:none"] + ([f"stroke:{stroke.group(1)}"] if stroke else [])
            own = f'<path data-layer="{esc}" style="{";".join(parts)}"/>' if (fill or stroke) else ""
            return own + "".join(emit(c, True) for c in node["children"])
        is_icon = bool(ICON.search(name)) or (SHAPE.match(name) and not node["children"])
        attrs = [f'data-layer="{esc}"']
        if CHROME.search(name):
            attrs.append("data-x-chrome")
        kind = _kind(name, d)
        text_layer = "font-size" in d and not node["children"]
        if kind or (text_layer and host):
            attrs.append(f'data-x-kind="{kind or host}"')  # a label takes the kind of the button / chip it sits in
        if kind in ("button", "pill/chip", "field", "app bar", "bottom bar"):
            host = kind
        style = _style(d, weights)
        if re.match(r"^ellipse\b", name, re.I) and "border-radius" not in d:
            style += ";border-radius:9999px"
        attr = " ".join(attrs)
        if is_icon:  # an icon frame, or a lone vector: its shapes' fills are icon colours
            shapes = node["children"] if node["children"] else [node]
            return f'<svg {attr} style="{_html.escape(style)}">' + "".join(emit(c, True) for c in shapes) + "</svg>"
        text = esc if text_layer else ""
        return (f'<div {attr} style="{_html.escape(style)}">{text}'
                + "".join(emit(c, host=host) for c in node["children"]) + "</div>")

    body = []
    for n in tree["children"]:
        if _is_screen(n["decls"]):
            if id(n) not in keep:
                continue
            body.append(f"<p>{_html.escape(n['name'])}</p>" + emit(n).replace("<div ", "<div data-x-frame ", 1))
        else:
            body.append(emit(n))
    css = ":root{" + "".join(f"{k}:{v};" for k, v in props.items()) + "}" if props else ""
    html = f"<html><head><style>{css}</style></head><body>" + "\n".join(body) + "</body></html>"
    return html, {"layers": len(layers), "screens": [s["name"] for s, _ in best.values()], "merged": merged,
                  "weights": sorted(weights), "styleNames": len(props)}


def _count(node):
    return 1 + sum(_count(c) for c in node["children"])


def extract(path, to_hex):
    """Evidence for a Copy-as-CSS file, in html_evidence's shape."""
    import html_evidence as he
    text = Path(path).read_text(errors="ignore")
    html, info = to_html(text)
    ev = he.collect(html, to_hex)
    warnings = [] if looks_like(text) else [
        "This doesn't look like Figma's Copy as CSS output (layer comments with bare declarations). "
        "For an HTML page use --from html; for a stylesheet with custom properties use --from css."]
    if info["merged"]:
        warnings.append(f"{len(info['merged'])} screen variants were merged into their fuller version: "
                        + "; ".join(info["merged"]) + ".")
    if info["weights"]:
        warnings.append(f"Variable font weights {info['weights']} were rounded to the nearest 100 "
                        "(Flutter's FontWeight steps).")
    if not ev["framesFound"]:
        warnings.append("No screen-sized frame was selected, so all layers were read as one screen. "
                        "Copy whole screens for the best evidence.")
    if not info["styleNames"]:
        warnings.append("No colour styles or variables are named in the copy: every role is an inference from "
                        "usage. If the designer binds Figma variables, the copied CSS carries their names.")
    if not ev["colours"]:
        warnings.append("No colours were found. Check that the selection was copied with Copy as CSS.")
    ev.update(kind="figma-css", warnings=warnings,
              mode=f"Figma Copy as CSS: {info['layers']} layers, nesting rebuilt from auto-layout order (approximate)")
    return ev
