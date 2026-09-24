#!/usr/bin/env python3
"""Reading W3C Design Tokens (DTCG) files for draft_spec.py --from dtcg.

Handles the shapes real exports use:
  - `$value` / `$type` / `$description` (DTCG) and `value` / `type` (Tokens Studio)
  - `$type` set on a group and inherited by its tokens
  - references `{a.b.c}` anywhere, including inside composite values (typography, shadow)
  - dimension objects `{"value": 16, "unit": "px"}`, colour objects
    `{"colorSpace": "srgb", "components": [...], "alpha": 1, "hex": "#…"}` and font-family arrays
  - modes in `$extensions` (`mode` / `modes`, e.g. {"dark": "#…"}), or a separate dark-mode file
  - two tiers: a palette of primitives and semantic tokens that reference them

It doesn't decide roles. `suggest_role` and `suggest_type_role` turn common semantic
vocabulary (`action.primary`, `text.muted`, `border.divider`, `screen-title`) into a
*suggested* Material role, which the agent confirms against the design.
"""

import re

REF_FULL = re.compile(r"^\s*\{([^{}]+)\}\s*$")
REF_ANY = re.compile(r"\{([^{}]+)\}")
# Leading path segments that name a tier or a namespace, not the token's meaning.
TIER_WORDS = {"semantic", "semantics", "sys", "system", "alias", "aliases", "theme", "tokens", "token", "ref",
              "global", "primitive", "primitives", "palette", "md", "color", "colors", "colour", "colours"}
MODE_WORDS = {"light", "dark"}
# Palette names: a hue plus a step ('green.900', 'gray-50', 'ink'). These are raw material, not meanings.
HUES = {"red", "orange", "amber", "yellow", "lime", "green", "emerald", "teal", "cyan", "sky", "blue", "indigo",
        "violet", "purple", "fuchsia", "pink", "rose", "brown", "gray", "grey", "slate", "zinc", "neutral", "stone",
        "sand", "sage", "ink", "black", "white", "cream", "beige", "navy", "mint", "olive", "coral", "gold", "silver"}
SYSTEM_FONTS = {"sans-serif", "serif", "monospace", "system-ui", "-apple-system", "blinkmacsystemfont",
                "sf pro text", "sf pro display", "sf pro", "segoe ui", "roboto", "helvetica neue", "helvetica",
                "arial", "ui-sans-serif", "ui-serif", "ui-monospace", "apple color emoji", "segoe ui emoji",
                "noto sans", "inherit"}
MATERIAL_SIZES = {"display": (57, 45, 36), "headline": (32, 28, 24), "title": (22, 16, 14),
                  "body": (16, 14, 12), "label": (14, 12, 11)}


def tokens(node, prefix="", inherited_type=None):
    """{path: {"value", "type", "description", "modes"}} for every token in a DTCG / Tokens Studio tree."""
    out = {}
    if not isinstance(node, dict):
        return out
    own_type = node.get("$type") or (node.get("type") if isinstance(node.get("type"), str) else None)
    is_token = "$value" in node or ("value" in node and (isinstance(node.get("type"), str)
                                                         or not isinstance(node["value"], dict)))
    if is_token:
        ext = node.get("$extensions") or {}
        modes = {}
        for key in ("mode", "modes"):
            if isinstance(ext.get(key), dict):
                modes.update(ext[key])
        out[prefix] = {"value": node.get("$value", node.get("value")), "type": own_type or inherited_type,
                       "description": node.get("$description") or node.get("description") or "", "modes": modes}
        return out
    for k, v in node.items():
        if not k.startswith("$"):
            out.update(tokens(v, f"{prefix}.{k}" if prefix else k, own_type or inherited_type))
    return out


def resolve(value, toks, seen=()):
    """Resolve {a.b} references anywhere in a value; unknown references are left as written."""
    if isinstance(value, str):
        m = REF_FULL.match(value)
        if m:
            path = m.group(1).strip()
            if path in toks and path not in seen:
                return resolve(toks[path]["value"], toks, seen + (path,))
            return value

        def sub(mm):
            p = mm.group(1).strip()
            if p in toks and p not in seen:
                r = scalar(resolve(toks[p]["value"], toks, seen + (p,)))
                return str(r) if not isinstance(r, (dict, list)) else mm.group(0)
            return mm.group(0)
        return REF_ANY.sub(sub, value)
    if isinstance(value, list):
        return [resolve(v, toks, seen) for v in value]
    if isinstance(value, dict):
        return {k: resolve(v, toks, seen) for k, v in value.items()}
    return value


def refs_in(value):
    """Every referenced path inside a raw value."""
    if isinstance(value, str):
        return {m.strip() for m in REF_ANY.findall(value)}
    if isinstance(value, list):
        return set().union(*(refs_in(v) for v in value)) if value else set()
    if isinstance(value, dict):
        return set().union(*(refs_in(v) for v in value.values())) if value else set()
    return set()


def scalar(value):
    """DTCG objects in the string forms the drafter parses: '16px', '#RRGGBB' / 'rgba(…)', font lists kept."""
    if isinstance(value, dict):
        keys = set(value)
        if keys <= {"value", "unit"} and "value" in value:
            return f"{value['value']}{value.get('unit', 'px')}"
        if "colorSpace" in value or ("hex" in value and keys <= {"hex", "alpha", "components", "colorSpace"}):
            alpha = float(value.get("alpha", 1))
            if value.get("hex") and alpha >= 1:
                return value["hex"]  # exact; components may be rounded
            comps = value.get("components")
            if value.get("colorSpace", "srgb") == "srgb" and isinstance(comps, list) and len(comps) >= 3:
                r, g, b = (round(float(c) * 255) for c in comps[:3])
                return f"rgba({r},{g},{b},{alpha})" if alpha < 1 else f"#{r:02X}{g:02X}{b:02X}"
            if value.get("hex"):
                return value["hex"] if alpha >= 1 else f"{value['hex']}{round(alpha * 255):02X}"
            return value
        return {k: scalar(v) for k, v in value.items()}
    if isinstance(value, list):
        return [scalar(v) for v in value]
    return value


def font_family(value):
    """(family, fallbacks) from a string stack or an array; platform and generic names are dropped."""
    names = value if isinstance(value, list) else str(value).split(",")
    names = [str(n).strip().strip("'\"") for n in names]
    real = [n for n in names if n and n.lower() not in SYSTEM_FONTS]
    return (real[0] if real else (names[0] if names else None)), real[1:]


def meaning(path):
    """Path segments without tier / namespace / mode words: 'semantic.text.on-brand' → ['text', 'on', 'brand']."""
    segs = [s for s in re.split(r"[.\-_/\s]+", path.lower()) if s]
    while segs and segs[0] in TIER_WORDS:
        segs = segs[1:]
    return [s for s in segs if s not in MODE_WORDS]


def mode_of(path):
    return "dark" if "dark" in re.split(r"[.\-_/\s]+", path.lower()) else "light"


def clean_name(path):
    """'semantic.text.on-brand' → 'text-on-brand' (tier and mode words dropped)."""
    segs = [s for s in re.split(r"[.]", path) if s]
    while segs and segs[0].lower() in TIER_WORDS:
        segs = segs[1:]
    segs = [s for s in segs if s.lower() not in MODE_WORDS]
    return "-".join(segs) or path


def is_raw_palette(path):
    """A hue scale step ('color.green.900', 'gray-50', 'white'), as opposed to a named colour ('success.500', 'swish.fg')."""
    s = meaning(path)
    return bool(s) and s[0] in HUES and all(x in HUES or re.fullmatch(r"\d+|a\d+|[a-z]?\d+", x) for x in s)


def is_semantic(path, raw):
    first = re.split(r"[.\-_/]", path.lower())[0]
    return bool(REF_FULL.match(raw) if isinstance(raw, str) else False) or first in {
        "semantic", "semantics", "sys", "system", "alias", "aliases", "theme"}


# ------------------------------------------------------------------ suggestions


def suggest_role(path):
    """(suggested role, extension usage) for a semantic colour name, or (None, None). A suggestion, not a mapping."""
    s = meaning(path)
    has = lambda *w: any(x in s for x in w)  # noqa: E731
    fg = has("fg", "foreground", "text", "label", "on", "content", "icon", "ink")
    soft = has("soft", "subtle", "bg", "background", "container", "surface", "light", "tint", "weak", "muted")
    if has("scrim", "overlay", "backdrop", "barrier"):
        return "scrim", None
    if s and s[0] == "status" and len(s) > 1:  # data statuses are not the error role
        return f"ext.{camel(clean_name(path))}", "text" if fg else "icon"
    if has("success", "positive", "valid", "accepted", "complete", "completed"):
        return ("ext.successContainer", "fill") if soft and not fg else ("ext.success", "text" if fg else "icon")
    if has("warning", "caution", "pending", "attention"):
        return ("ext.warningContainer", "fill") if soft and not fg else ("ext.warning", "text" if fg else "icon")
    if has("info", "informative"):
        return ("ext.infoContainer", "fill") if soft and not fg else ("ext.info", "text" if fg else "icon")
    if has("danger", "error", "critical", "destructive", "declined", "negative"):
        if soft and not (has("text", "fg", "foreground") and not has("bg", "background")):
            return "errorContainer", None
        return "error", None
    if has("badge", "notification", "count") and not soft:
        return "error", None
    if has("disabled"):
        return f"ext.{camel(clean_name(path))}", "text" if fg else "fill"
    if has("inverse"):
        return ("onInverseSurface" if fg else "inverseSurface"), None
    if s and s[0] in ("text", "fg", "foreground", "content", "ink", "type", "typography"):
        if has("on") and has("brand", "primary", "accent", "action"):
            return "onPrimary", None
        if has("link", "hyperlink"):
            return "ext.link", "text"
        if has("placeholder", "hint"):
            return "ext.onSurfaceMuted", "text"
        if has("brand", "accent"):
            return "primary", None
        if has("secondary", "muted", "subtle", "subdued", "tertiary", "low", "medium", "caption", "meta", "weak"):
            return "onSurfaceVariant", None
        return "onSurface", None
    if s and s[0] in ("action", "button", "btn", "cta", "interactive", "brand", "primary", "control"):
        if fg or has("on"):
            return ("onSecondary" if has("secondary") else "onPrimary"), None
        if has("hover", "pressed", "active", "press"):
            return f"ext.{camel(clean_name(path))}", "fill"
        if has("secondary"):
            return "secondary", None
        if has("tertiary"):
            return "tertiary", None
        if soft:
            return "primaryContainer", None
        return "primary", None
    if s and s[0] in ("accent", "highlight"):
        return "secondary", None
    if s and s[0] in ("surface", "background", "bg", "canvas", "layer", "elevation", "page", "fill"):
        if len(s) == 1 or has("page", "base", "default", "primary", "body", "main"):
            return "surface", None
        if has("canvas", "sunken", "recessed", "inset", "alt", "secondary", "muted", "subtle", "gray", "grey"):
            return "surfaceContainerLow", None
        if has("app"):
            return "surface", None
        if has("card", "raised", "elevated", "sheet", "modal", "paper", "popover", "dialog", "menu"):
            return "surfaceContainerLowest", None
        if has("selected", "active", "hover", "pressed", "highlight", "brand"):
            return "secondaryContainer", None
        if has("strong", "high", "emphasis", "tertiary"):
            return "surfaceContainerHigh", None
        return f"ext.{camel(clean_name(path))}", "fill"
    if s and s[0] in ("border", "stroke", "outline", "divider", "line", "separator", "hairline"):
        if has("focus", "brand", "active", "selected", "primary", "accent"):
            return "primary", None
        if s[0] in ("divider", "separator", "hairline") or has("divider", "subtle", "card", "muted", "light",
                                                                "hairline", "weak", "separator", "decorative"):
            return "outlineVariant", None
        return "outline", None
    if has("focus", "ring"):
        return "primary", None
    if len(s) > 1 and s[-1] in ("fg", "foreground", "text", "on", "bg", "background", "fill", "surface"):
        # a named pair such as a partner brand: 'swish.fg' / 'swish.bg'
        return f"ext.{camel(clean_name(path))}", "text" if s[-1] in ("fg", "foreground", "text", "on") else "fill"
    return None, None


def suggest_type_role(name, size):
    """A suggested Material text role for a purpose-named style, by name and size, or None."""
    n = name.lower()
    if re.search(r"wordmark|logo|brand|price|amount|number|numeric|metric|stat|code|mono|otp|pin", n):
        return None
    if re.search(r"caption|meta|helper|footnote|hint|timestamp|fine", n):
        return "bodySmall"
    if re.search(r"display|hero|jumbo", n):
        family = "display"
    elif re.search(r"title|heading|header|h[1-6]\b|section|subtitle|subhead|modal|dialog|sheet", n):
        family = "headline" if size and size >= 24 else "title"
    elif re.search(r"label|button|btn|tag|badge|chip|tab|overline|nav|pill", n):
        family = "label"
    elif re.search(r"body|paragraph|text|chat|message|row|list|description|input|field|content|copy", n):
        family = "body"
    else:
        return None
    if not size:
        return family + "Medium"
    sizes = MATERIAL_SIZES[family]
    idx = min(range(3), key=lambda i: abs(sizes[i] - size))
    return family + ("Large", "Medium", "Small")[idx]


def size_key(name):
    """sizes key for a size token: 'size.button' → buttonHeight; None for layout facts (screen width)."""
    n = clean_name(name).lower()
    if re.search(r"screen|viewport|frame|artboard|device|breakpoint|container|max-width", n):
        return None
    if re.search(r"touch|tap|hit", n):
        return "minTouchTarget"
    if "icon" in n:
        return "iconSm" if re.search(r"\b(sm|small|xs)\b", n.replace("-", " ")) else \
            "iconLg" if re.search(r"\b(lg|large|xl)\b", n.replace("-", " ")) else "iconMd"
    if re.search(r"search", n):
        return "searchHeight"
    if re.search(r"input|field|text-?field|textbox", n):
        return "inputHeight"
    if re.search(r"button|btn|cta", n):
        return "buttonHeight"
    if re.search(r"tab-?bar|bottom-?nav|nav-?bar|navigation", n):
        return "navigationBarHeight"
    if re.search(r"app-?bar|toolbar|top-?bar|header", n):
        return "appBarHeight"
    if "avatar" in n:
        return "avatarSize"
    return camel(re.sub(r"^(size|sizes|sizing|height|dimension)[-.]?", "", n)) or None


# Component-named radius tokens → component properties.
COMPONENT_RADII = [
    (r"\b(button|btn|cta)\b", [("filledButton", "radius"), ("outlinedButton", "radius")]),
    (r"\b(input|field|text-?field|textbox)\b", [("input", "radius")]),
    (r"\bcard\b", [("card", "radius")]),
    (r"\b(chip|tag)\b", [("chip", "radius")]),
    (r"\b(sheet|bottom-?sheet|drawer)\b", [("bottomSheet", "topRadius")]),
]


def component_targets(name):
    n = clean_name(name).lower().replace("_", "-")
    n = re.sub(r"^(radius|radii|rounded|corner|corners|border-radius)-?", "", n)
    for pattern, targets in COMPONENT_RADII:
        if re.search(pattern, n.replace("-", " ")):
            return targets
    return []


def camel(text):
    words = re.findall(r"[A-Za-z0-9]+", text)
    return words[0].lower() + "".join(w[:1].upper() + w[1:] for w in words[1:]) if words else text
