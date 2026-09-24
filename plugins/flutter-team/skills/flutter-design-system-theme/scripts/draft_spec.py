#!/usr/bin/env python3
"""Turn the STRUCTURED part of a design hand-off into a draft theme spec.

Deterministic, so the same input always gives the same draft. It maps what can
be mapped by name (Material role names, type-scale names, spacing/radius
scales), converts units (px, rem, em → dp) and records a source for every
value. Everything it can't place goes to `unmapped` for the agent to decide.

The agent then reads the rest of the hand-off (prose, component specs,
screenshots), adds extension colours, conflicts and components, and validates.

Supported inputs:
  stitch  Google Stitch DESIGN.md (YAML front matter: colors, typography, rounded, spacing)
  dtcg    W3C Design Tokens / Figma variables / Tokens Studio JSON ($value or value)
  css     CSS custom properties (--name: value;), e.g. from a web export or Tailwind theme
  claude  Claude Design System (claude.ai): project/tokens.json, or a folder containing it
  html    any HTML design: a Claude Design page export (bundled or rendered), an HTML/CSS
          mock-up, a Tailwind or React prototype. Rendered in a local headless Chrome when
          one is installed (--render auto|always|never), else read statically. Writes
          <input>.evidence.md with how every value is used.

Usage:
  python3 draft_spec.py --from stitch design/sources/DESIGN.md -o design/theme.spec.json
  python3 draft_spec.py --from css design/sources/tokens.css --name "Acme" -o design/theme.spec.json
"""

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import theme_spec as ts  # noqa: E402

ROOT_FONT_SIZE = 16.0
SIZE_WORDS = {"lg": "Large", "large": "Large", "l": "Large", "md": "Medium", "medium": "Medium", "m": "Medium",
              "sm": "Small", "small": "Small", "s": "Small"}
TYPE_GROUPS = ("display", "headline", "title", "body", "label")
# Source names that differ from Flutter's ColorScheme role names.
ROLE_ALIASES = {"inverseOnSurface": "onInverseSurface", "onSurfaceInverse": "onInverseSurface",
                "surfaceInverse": "inverseSurface", "primaryInverse": "inversePrimary"}


# ---------------------------------------------------------------- parsing


def parse_front_matter(text):
    """Minimal YAML subset used by Stitch: nested maps of scalars, 2-space indent."""
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.S)
    if not m:
        sys.exit("No YAML front matter (--- … ---) found")
    root, stack = {}, [(-1, None)]
    stack[0] = (-1, root)
    for raw in m.group(1).splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip())
        key, _, value = raw.strip().partition(":")
        key, value = key.strip().strip("'\""), value.strip()
        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]
        if value == "":
            parent[key] = {}
            stack.append((indent, parent[key]))
        else:
            parent[key] = value.strip("'\"")
    return root


def flatten_dtcg(node, prefix=""):
    out = {}
    if isinstance(node, dict):
        if "$value" in node or ("value" in node and not isinstance(node.get("value"), dict)):
            out[prefix] = node.get("$value", node.get("value"))
            return out
        for k, v in node.items():
            if k.startswith("$"):
                continue
            out.update(flatten_dtcg(v, f"{prefix}.{k}" if prefix else k))
    return out


def parse_css(text):
    return {m.group(1): m.group(2).strip() for m in re.finditer(r"--([A-Za-z0-9_-]+)\s*:\s*([^;]+);", text)}


ALIAS_RE = re.compile(r"^\{([^}]+)\}$|^var\(\s*--([A-Za-z0-9_-]+)\s*(?:,\s*([^)]+))?\)$")


def resolve_aliases(flat):
    """Resolve DTCG `{a.b}` and CSS `var(--x)` references. Returns (values, alias_of)."""
    resolved, alias_of = {}, {}

    def resolve(key, depth=0):
        value = flat.get(key)
        m = ALIAS_RE.match(value.strip()) if isinstance(value, str) else None
        if not m or depth > 10:
            return value
        target = m.group(1) or m.group(2)
        if target not in flat:
            return m.group(3).strip() if m.group(3) else value  # CSS fallback, else leave unresolved
        alias_of.setdefault(key, target)
        return resolve(target, depth + 1)

    for key in flat:
        resolved[key] = resolve(key)
    return resolved, alias_of


# ---------------------------------------------------------------- units


def to_dp(value, font_size=None):
    """'16px' | '1rem' | '0.02em' (needs font_size) | '600' | 12 → float dp."""
    if isinstance(value, (int, float)):
        return float(value)
    v = str(value).strip()
    m = re.match(r"^(-?[0-9.]+)\s*(px|rem|em|pt|dp|%)?$", v)
    if not m:
        return None
    n, unit = float(m.group(1)), m.group(2) or "px"
    if unit in ("px", "dp", "pt"):
        return n
    if unit == "rem":
        return n * ROOT_FONT_SIZE
    if unit == "em":
        return n * font_size if font_size else None
    if unit == "%":
        return n / 100 * font_size if font_size else None
    return None


def round_dp(v):
    return round(v, 2) if v is not None else None


def css_color_to_hex(value):
    """rgb()/rgba()/hsl()/hsla() → #RRGGBB or #AARRGGBB; None for anything else."""
    v = str(value).strip().lower()
    ok = re.match(r"^oklch\(\s*([^)]+)\)$", v)
    if ok:
        return oklch_to_hex(ok.group(1))
    m = re.match(r"^(rgba?|hsla?)\(\s*([^)]+)\)$", v)
    if not m:
        return None
    parts = [p for p in re.split(r"[\s,/]+", m.group(2)) if p]
    if len(parts) < 3:
        return None

    def alpha(p):
        return float(p[:-1]) / 100 if p.endswith("%") else float(p)

    a = alpha(parts[3]) if len(parts) > 3 else 1.0
    if m.group(1).startswith("rgb"):
        r, g, b = (round(float(x[:-1]) * 2.55) if x.endswith("%") else round(float(x)) for x in parts[:3])
    else:
        import colorsys
        h = float(parts[0].replace("deg", "")) / 360
        l_, s_ = float(parts[2].rstrip("%")) / 100, float(parts[1].rstrip("%")) / 100
        r, g, b = (round(c * 255) for c in colorsys.hls_to_rgb(h, l_, s_))
    rgb = f"{r:02X}{g:02X}{b:02X}"
    return f"#{rgb}" if a >= 1 else f"#{round(a * 255):02X}{rgb}"


def oklch_to_hex(args):
    """oklch(L C H [/ A]) → hex via OKLab → linear sRGB (clamped to gamut)."""
    import math
    parts = [p for p in re.split(r"[\s,/]+", args.strip()) if p]
    if len(parts) < 3:
        return None
    L = float(parts[0][:-1]) / 100 if parts[0].endswith("%") else float(parts[0])
    C = float(parts[1][:-1]) / 100 * 0.4 if parts[1].endswith("%") else float(parts[1])
    H = math.radians(float(parts[2].replace("deg", "")))
    a_ = float(parts[3][:-1]) / 100 if len(parts) > 3 and parts[3].endswith("%") else (float(parts[3]) if len(parts) > 3 else 1.0)
    a, b = C * math.cos(H), C * math.sin(H)
    l_, m_, s_ = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3, (L - 0.1055613458 * a - 0.0638541728 * b) ** 3, \
        (L - 0.0894841775 * a - 1.2914855480 * b) ** 3
    lin = (4.0767416621 * l_ - 3.3077115913 * m_ + 0.2309699292 * s_,
           -1.2684380046 * l_ + 2.6097574011 * m_ - 0.3413193965 * s_,
           -0.0041960863 * l_ - 0.7034186147 * m_ + 1.7076147010 * s_)

    def gamma(c):
        c = min(max(c, 0.0), 1.0)
        return 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055
    rgb = "".join(f"{round(gamma(c) * 255):02X}" for c in lin)
    return f"#{rgb}" if a_ >= 1 else f"#{round(a_ * 255):02X}{rgb}"


def normalize_hex(value):
    converted = css_color_to_hex(value)
    if converted:
        return converted
    v = str(value).strip()
    if re.match(r"^#[0-9A-Fa-f]{3}$", v):
        v = "#" + "".join(ch * 2 for ch in v[1:])
    if re.match(r"^#[0-9A-Fa-f]{8}$", v):  # CSS #RRGGBBAA → Flutter #AARRGGBB
        v = "#" + v[7:9] + v[1:7]
    return v.upper() if ts.HEX_RE.match(v) else None


def camel(text):
    words = re.findall(r"[A-Za-z0-9]+", text)
    return words[0].lower() + "".join(w[:1].upper() + w[1:] for w in words[1:]) if words else text


def weight(value):
    names = {"thin": 100, "extralight": 200, "light": 300, "regular": 400, "normal": 400, "medium": 500,
             "semibold": 600, "bold": 700, "extrabold": 800, "black": 900}
    v = str(value).strip().lower().replace(" ", "").replace("-", "")
    return names.get(v) or (int(v) if v.isdigit() else 400)


# ---------------------------------------------------------------- mapping


NAMED_TYPE_ROLES = {"h1": "headlineLarge", "h2": "headlineMedium", "h3": "headlineSmall", "h4": "titleLarge",
                    "h5": "titleMedium", "h6": "titleSmall", "subtitle": "titleMedium", "caption": "bodySmall",
                    "overline": "labelSmall", "button": "labelLarge", "paragraph": "bodyMedium"}


def type_role(name):
    """'headline-lg' → headlineLarge, 'body' → bodyMedium, 'h2' → headlineMedium; None if no match."""
    parts = re.findall(r"[a-z0-9]+", name.lower())
    if len(parts) == 2 and parts[0] in TYPE_GROUPS and parts[1] in SIZE_WORDS:
        return parts[0] + SIZE_WORDS[parts[1]]
    if len(parts) == 1 and parts[0] in TYPE_GROUPS:
        return parts[0] + "Medium"
    if len(parts) == 1 and parts[0] in NAMED_TYPE_ROLES:
        return NAMED_TYPE_ROLES[parts[0]]
    joined = camel(name)
    return joined if joined in ts.TYPE_ROLES else None


SCALE_WORDS = {"xxsmall": "Xxs", "xxs": "Xxs", "xsmall": "Xs", "xs": "Xs", "small": "Sm", "sm": "Sm",
               "medium": "Md", "md": "Md", "large": "Lg", "lg": "Lg", "xlarge": "Xl", "xl": "Xl",
               "xxlarge": "2xl", "xxl": "2xl", "2xl": "2xl", "3xl": "3xl"}


def scale_suffix(core):
    """'small' → 'Sm', 'x-large' → 'Xl', 'base' → 'Base', '2xl' → '2xl'."""
    word = core.replace("-", "").replace("_", "").lower()
    if word in SCALE_WORDS:
        return SCALE_WORDS[word]
    c = camel(core)
    return c[:1].upper() + c[1:]


def spacing_key(name):
    n = name.lower()
    if "screen" in n and "margin" in n:
        return "spacing", "screenPadding"
    if "gutter" in n:
        return "spacing", "spacingGutter"
    if "touch" in n:
        return "sizes", "minTouchTarget"
    core = re.sub(r"^(space|spacing|gap)[-_.]?", "", n)
    return "spacing", "spacing" + (scale_suffix(core) if core else "Base")


def radius_key(name):
    n = name.lower()
    core = re.sub(r"^(rounded|radius|corner)[-_.]?", "", n)
    if core in ("", "default", "base"):
        return "radiusDefault"
    return "radius" + scale_suffix(core)


def draft(tokens_by_group, source_label, name, aliases=None):
    aliases = aliases or {}
    referenced = {re.sub(r"^(colou?rs?)[-_.]", "", t).replace(".", "-") for t in aliases.values()}
    aliases = {re.sub(r"^(colou?rs?)[-_.]", "", k).replace(".", "-"): v for k, v in aliases.items()}
    spec = {
        "specVersion": ts.SPEC_VERSION,
        "name": name,
        "sources": [{"id": source_label["type"].split("-")[0], "type": source_label["type"], "file": source_label["file"]}],
        "policy": {"deriveMissingDark": True, "schemeVariant": "fidelity"},
        "colors": {"light": {}, "dark": {}},
        "extensionColors": {},
        "typography": {"roles": {}, "extras": {}},
        "spacing": {}, "radius": {}, "sizes": {},
        "components": {},
        "conflicts": [],
        "unmapped": [],
        "acceptedContrastExceptions": [],
        "notes": [],
    }
    where = source_label["where"]

    # --- colours
    colors = tokens_by_group.get("colors", {})
    deprecated_seen = {}
    for token, raw in colors.items():
        value = normalize_hex(raw)
        src = f"{where} colors.{token}"
        alias = aliases.get(token)
        if alias:
            src += f" → {alias}"
        if not value:
            spec["unmapped"].append({"token": token, "value": raw, "reason": "not a hex colour"})
            continue
        dark = bool(re.search(r"(^|[-_.])dark($|[-_.])", token))
        role = camel(re.sub(r"(^|[-_.])(dark|light)($|[-_.])", r"\1", token).strip("-_."))
        role = ROLE_ALIASES.get(role, role)
        if role in ts.DEPRECATED_ROLES:
            deprecated_seen[role] = (token, value, src, dark)
            continue
        if role in ts.COLOR_ROLES:
            entry = {"value": value, "token": token, "source": src}
            if alias:
                entry["name"] = re.split(r"[.-]", alias.replace("color-", "").replace("color.", ""))[-1]
            spec["colors"]["dark" if dark else "light"][role] = entry
        elif token in referenced:
            spec["notes"].append(f"{token} ({value}) is a primitive referenced by a semantic token; kept as the palette name.")
        else:
            spec["unmapped"].append({"token": token, "value": value,
                                     "reason": "no Material role with this name — map by meaning or add as extensionColor"})
    for role, (token, value, src, dark) in deprecated_seen.items():
        target = ts.DEPRECATED_ROLES[role]
        mode = "dark" if dark else "light"
        existing = spec["colors"][mode].get(target)
        if existing and existing["value"] == value:
            spec["notes"].append(f"{token} ({value}) is a deprecated Material role equal to {target}; dropped.")
        elif existing:
            spec["conflicts"].append({
                "target": f"colors.{mode}.{target}", "status": "open",
                "candidates": [{"value": existing["value"], "source": existing["source"]},
                               {"value": value, "source": src + f" (deprecated '{role}')"}],
                "recommendation": existing["value"], "reason": f"'{role}' is deprecated; {target} is the M3 role",
            })
        else:
            spec["colors"][mode][target] = {"value": value, "token": token, "source": src + f" (deprecated '{role}')"}

    # --- typography
    families = {}
    for token, style in tokens_by_group.get("typography", {}).items():
        if not isinstance(style, dict):
            spec["unmapped"].append({"token": token, "value": style, "reason": "typography token is not a style object"})
            continue
        size = to_dp(style.get("fontSize"))
        if size is None:
            spec["unmapped"].append({"token": token, "value": style, "reason": "fontSize missing or unparseable"})
            continue
        entry = {"token": token, "fontSize": round_dp(size), "fontWeight": weight(style.get("fontWeight", 400)),
                 "source": f"{where} typography.{token}"}
        line = style.get("lineHeight")
        if line is not None:
            lh = to_dp(line, size) if str(line).strip().endswith(("px", "rem", "em", "%", "pt")) else float(line) * size
            entry["lineHeight"] = round_dp(lh)
        ls = style.get("letterSpacing")
        if ls is not None:
            entry["letterSpacing"] = round_dp(to_dp(ls, size) or 0)
        if style.get("fontFamily"):
            families[style["fontFamily"]] = families.get(style["fontFamily"], 0) + 1
        role = type_role(token)
        if role:
            spec["typography"]["roles"][role] = entry
        else:
            spec["typography"]["extras"][camel(token)] = entry
    if families:
        family = max(families, key=families.get)
        spec["typography"]["fontFamily"] = {"value": family, "source": f"{where} typography.*.fontFamily"}
        if len(families) > 1:
            spec["notes"].append(f"Several font families used: {', '.join(families)} — only '{family}' is the default.")

    # --- radius / spacing
    for token, raw in tokens_by_group.get("rounded", {}).items():
        v = to_dp(raw)
        if v is None:
            spec["unmapped"].append({"token": token, "value": raw, "reason": "radius not parseable"})
            continue
        spec["radius"][radius_key(token)] = {"value": round_dp(v), "token": token, "source": f"{where} rounded.{token}"}
    for token, raw in tokens_by_group.get("spacing", {}).items():
        v = to_dp(raw)
        if v is None:
            spec["unmapped"].append({"token": token, "value": raw, "reason": "spacing not parseable"})
            continue
        group, key = spacing_key(token)
        spec[group][key] = {"value": round_dp(v), "token": token, "source": f"{where} spacing.{token}"}

    scale = tokens_by_group.get("typeScale", {})
    if scale:
        listed = ", ".join(f"{k}={v}" for k, v in scale.items())
        spec["notes"].append(
            "Separate type-scale primitives, no composite text styles: " + listed +
            ". Compose typography.roles from them (see references/inputs/design-tokens-json.md › Separate scales).")
        for token, raw in scale.items():
            spec["unmapped"].append({"token": token, "value": raw,
                                     "reason": "type-scale primitive — use it to compose typography.roles"})

    for token, raw in tokens_by_group.get("other", {}).items():
        spec["unmapped"].append({"token": token, "value": raw, "reason": "not recognised as colour, type, radius or spacing"})
    return spec


def draft_claude(data, label, name):
    """Claude Design System (claude.ai Design System type) project/tokens.json.

    Shape: color {themes:[{id,name}], tokens:[{name, value: str | {themeId: str}, usage}]},
    type {fonts, families, groups:[{name, family, styles:[{name, fontSize, lineHeight, fontWeight}]}]},
    spacing/radius/shadow {tokens:[{name, value, usage}]}. Aliases are "{other-token}".
    """
    spec = draft({}, label, name)
    spec["notes"] = []
    where = label["where"]
    color = data.get("color") or {}
    themes = color.get("themes") or [{"id": "light", "name": "Light"}]
    first = themes[0]["id"]
    dark_ids = [t["id"] for t in themes if "dark" in f"{t.get('id', '')} {t.get('name', '')}".lower()]
    light_id = next((t["id"] for t in themes if t["id"] not in dark_ids), first)
    dark_id = dark_ids[0] if dark_ids else None
    extra_themes = [t.get("name", t["id"]) for t in themes if t["id"] not in (light_id, dark_id)]
    if extra_themes:
        spec["notes"].append(f"Themes beyond light/dark ({', '.join(extra_themes)}) are not mapped — "
                             "treat each as another brand/contrast spec (references/runtime-theming.md).")
    by_name = {t.get("name"): t for t in color.get("tokens") or []}

    def mode_value(tok, theme, depth=0):
        v = tok.get("value")
        if isinstance(v, dict):
            v = v.get(theme, v.get(first))
        elif theme != first and theme is not None:
            v = v  # a plain string applies to every theme (inherits the first)
        m = re.match(r"^\{([^}]+)\}$", str(v).strip()) if v is not None else None
        if m and m.group(1) in by_name and depth < 10:
            return mode_value(by_name[m.group(1)], theme, depth + 1)
        return v

    for tname, tok in by_name.items():
        light_v = normalize_hex(mode_value(tok, light_id) or "")
        dark_raw = mode_value(tok, dark_id) if dark_id else None
        dark_v = normalize_hex(dark_raw) if dark_raw else None
        usage = tok.get("usage", "")
        src = f"{where} color.{tname}" + (f" — usage: {usage}" if usage else "")
        if not light_v:
            spec["unmapped"].append({"token": tname, "value": tok.get("value"),
                                     "reason": "colour not parseable (named colour, var() or color-mix()?)"})
            continue
        role = ROLE_ALIASES.get(camel(tname), camel(tname))
        if role in ts.COLOR_ROLES:
            spec["colors"]["light"][role] = {"value": light_v, "token": tname, "source": src + " [light]"}
            if dark_v and dark_id:
                spec["colors"]["dark"][role] = {"value": dark_v, "token": tname, "source": src + " [dark]"}
        else:
            entry = {"token": tname, "value": light_v, "reason": "map by its usage note to a Material role or an extensionColor"}
            if dark_v and dark_v != light_v:
                entry["dark"] = dark_v
            if usage:
                entry["usage"] = usage
            spec["unmapped"].append(entry)

    typ = data.get("type") or {}
    families = {}
    for alias, stack in (typ.get("families") or {}).items():
        first_family = str(stack).split(",")[0].strip().strip("'\"")
        families[alias] = first_family
    counts, fonts_with_files = {}, []
    for font in typ.get("fonts") or []:
        if font.get("file"):
            fonts_with_files.append(f"{font.get('family')} {font.get('weight', '')} → {font['file']}")
    for group in typ.get("groups") or []:
        gname = group.get("name", "")
        family = families.get(group.get("family"), group.get("family"))
        for style in group.get("styles") or []:
            sname = style.get("name", "")
            size = to_dp(style.get("fontSize"))
            if size is None:
                spec["unmapped"].append({"token": f"{gname}/{sname}", "value": style, "reason": "fontSize not parseable"})
                continue
            fw = str(style.get("fontWeight", 400)).split()[0]
            entry = {"token": f"{gname}/{sname}", "fontSize": round_dp(size), "fontWeight": weight(fw),
                     "source": f"{where} type.groups[{gname}].styles[{sname}]"}
            lh = style.get("lineHeight")
            if lh is not None:
                entry["lineHeight"] = round_dp(float(lh) * size if re.match(r"^[0-9.]+$", str(lh)) else to_dp(lh, size))
            if style.get("letterSpacing") is not None:
                entry["letterSpacing"] = round_dp(to_dp(style["letterSpacing"], size) or 0)
            if family:
                counts[family] = counts.get(family, 0) + 1
            role = type_role(sname) or type_role(f"{gname}-{sname}")
            if role and role not in spec["typography"]["roles"]:
                spec["typography"]["roles"][role] = entry
            else:
                key = camel(sname) if camel(sname) not in spec["typography"]["extras"] else camel(f"{gname} {sname}")
                spec["typography"]["extras"][key] = entry
    if counts:
        fam = max(counts, key=counts.get)
        spec["typography"]["fontFamily"] = {"value": fam, "source": f"{where} type.families"}
    if fonts_with_files:
        spec["notes"].append("Font files ship with the design system (project/fonts/): " + "; ".join(fonts_with_files) +
                             ". Copy them to assets/fonts/ and declare them in pubspec.yaml.")

    numeric = []
    for fam_name, group in (("spacing", "spacing"), ("radius", "rounded")):
        for tok in (data.get(fam_name) or {}).get("tokens") or []:
            v = to_dp(tok.get("value"))
            if v is None:
                spec["unmapped"].append({"token": tok.get("name"), "value": tok.get("value"), "reason": f"{fam_name} not parseable"})
                continue
            if fam_name == "spacing":
                key_group, key = spacing_key(tok["name"])
            else:
                key_group, key = "radius", radius_key(tok["name"])
            if re.search(r"\d$", key) and not re.search(r"\d?x?l$", key.lower()):
                numeric.append(tok["name"])
            spec[key_group][key] = {"value": round_dp(v), "token": tok["name"],
                                    "source": f"{where} {fam_name}.{tok['name']}" + (f" — usage: {tok['usage']}" if tok.get("usage") else "")}
    if numeric:
        spec["notes"].append("Numeric scale steps (" + ", ".join(numeric) + ") don't name the contract keys "
                             "(spacingSm/Md/Lg…, radiusSm/Md/Lg…): map the contract keys by value and usage when completing the spec.")
    for fam_name, fam in data.items():
        if fam_name in ("name", "version", "color", "type", "spacing", "radius", "meta"):
            continue
        for tok in (fam or {}).get("tokens") or [] if isinstance(fam, dict) else []:
            spec["unmapped"].append({"token": f"{fam_name}.{tok.get('name')}", "value": tok.get("value"),
                                     "reason": f"'{fam_name}' has no Flutter theme token (Material 3 uses tonal surfaces, not shadows)"
                                     if fam_name == "shadow" else f"'{fam_name}' is not a theme token family"})
    return spec


def draft_html(ev, label, name):
    """No token names exist in inline CSS: record evidence, map nothing by guesswork.

    Custom properties (if any) are drafted like CSS tokens; every other colour goes
    to `unmapped` with its usage summary. The font family is the most used one.
    """
    import html_evidence as he
    props = {k.lstrip("-"): v for k, v in ev["customProps"].items() if normalize_hex(v.strip())}
    props.update({k.lstrip("-") + "-dark": v for k, v in ev["customPropsDark"].items() if normalize_hex(v.strip())})
    spec = draft({"colors": props} if props else {}, label, name)
    where = label["where"]
    for h, e in sorted(ev["colours"].items(), key=lambda kv: -kv[1]["count"]):
        spec["unmapped"].append({"token": h, "value": h, "reason": "colour — map by usage: " + he.usage_summary(e)})
    for g, n in ev["gradients"].most_common():
        spec["unmapped"].append({"token": "gradient", "value": g,
                                 "reason": f"gradient ×{n} — Material has no gradient role; model stops as extension fills"})
    if ev["families"]:
        fam, n = ev["families"].most_common(1)[0]
        spec["typography"]["fontFamily"] = {"value": fam, "source": f"{where} font on {n} text elements"}
    weights = sorted({w for (_, w) in ev["type"]})
    spec["notes"] += [
        f"Drafted from HTML ({ev['mode']}) on {len(ev['screens'])} screens. Roles not named by a CSS variable are "
        f"inferences from usage — see {Path(label['file']).stem}.evidence.md.",
        f"Font weights in use: {weights}.",
    ]
    if ev["legends"]:
        spec["notes"].append(f"{len(ev['legends'])} legend cards name roles for their colours — read them before mapping.")
    return spec


def group_flat_tokens(flat):
    """Bucket flat 'a.b.c' / 'a-b-c' tokens into colors / typography / rounded / spacing / other."""
    groups = {"colors": {}, "typography": {}, "rounded": {}, "spacing": {}, "typeScale": {}, "other": {}}
    for path, value in flat.items():
        p = path.lower()
        leaf = re.split(r"[.]", path)[-1]
        if normalize_hex(value) or p.startswith(("color", "colour")):
            key = re.sub(r"^(colou?rs?|color-scheme)[-_.]", "", path)
            groups["colors"][key.replace(".", "-")] = value
        elif re.search(r"(font[-_.]?size|font[-_.]?weight|line[-_.]?height|letter[-_.]?spacing|font[-_.]?family)", p):
            groups["typeScale"][path] = value
        elif isinstance(value, dict) and "fontSize" in value:
            groups["typography"][re.sub(r"^(typography|font|text)[-_.]", "", path).replace(".", "-")] = value
        elif re.search(r"(radius|rounded|corner)", p):
            groups["rounded"][leaf if "." in path else path] = value
        elif re.search(r"(space|spacing|gap|gutter|margin|touch)", p):
            groups["spacing"][leaf if "." in path else path] = value
        else:
            groups["other"][path] = value
    return groups


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--from", dest="kind", required=True, choices=["stitch", "dtcg", "css", "claude", "html"])
    ap.add_argument("input", help="Design hand-off file")
    ap.add_argument("-o", "--output", required=True, help="Where to write the draft spec")
    ap.add_argument("--name", help="Design system name (default: from the input or file name)")
    ap.add_argument("--force", action="store_true", help="Overwrite an existing spec")
    ap.add_argument("--render", choices=["auto", "always", "never"], default="auto",
                    help="html only: read computed styles in a headless browser (auto = when one is installed)")
    ap.add_argument("--whole-page", action="store_true",
                    help="html only: read the whole page as one screen instead of detecting device frames")
    args = ap.parse_args()

    path = Path(args.input)
    if args.kind == "claude" and path.is_dir():
        found = [c for c in (path / "project" / "tokens.json", path / "tokens.json") if c.exists()]
        if not found:
            sys.exit(f"No project/tokens.json or tokens.json under {path}")
        path = found[0]
    text = path.read_text()
    label = {"file": str(path), "type": {"stitch": "stitch-design-md", "dtcg": "design-tokens-json",
                                         "css": "css-custom-properties", "claude": "claude-design-system", "html": "html"}[args.kind]}
    aliases = {}
    if args.kind == "stitch":
        fm = parse_front_matter(text)
        groups = {k: fm.get(k, {}) for k in ("colors", "typography", "rounded", "spacing")}
        label["where"] = f"{path.name} front matter"
        name = args.name or fm.get("name") or path.stem
    elif args.kind == "dtcg":
        flat, aliases = resolve_aliases(flatten_dtcg(json.loads(text)))
        groups = group_flat_tokens(flat)
        label["where"] = path.name
        name = args.name or path.stem
    elif args.kind == "html":
        import html_evidence as he
        ev = he.extract(path, normalize_hex, render=args.render, whole_page=args.whole_page)
        label["type"] = ev["kind"]
        label["where"] = path.name
        name = args.name or path.stem
        ev_path = path.with_name(path.stem + ".evidence.md")
        ev_path.write_text(he.evidence_markdown(ev, path.name))
        print(f"evidence: {ev_path}\n  read: {ev['mode']}\n  {len(ev['screens'])} screens, {len(ev['colours'])} colours, "
              f"{len(ev['type'])} type styles, {len(ev['legends'])} legend cards, "
              f"{len(ev['customProps'])} CSS variables")
        for w in ev["warnings"]:
            print(f"  check: {w}")
    elif args.kind == "claude":
        data = json.loads(text)
        label["where"] = path.name
        name = args.name or data.get("name") or path.stem
    else:
        flat, aliases = resolve_aliases(parse_css(text))
        groups = group_flat_tokens(flat)
        label["where"] = path.name
        name = args.name or path.stem

    out = Path(args.output)
    if out.exists() and not args.force:
        sys.exit(f"{out} exists — pass --force to overwrite (your manual edits would be lost)")
    if args.kind == "claude":
        spec = draft_claude(data, label, name)
    elif args.kind == "html":
        spec = draft_html(ev, label, name)
    else:
        spec = draft(groups, label, name, aliases)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(spec, indent=2, ensure_ascii=False) + "\n")

    c = spec["colors"]
    print(f"Draft written to {out}")
    print(f"  colours: {len(c['light'])} light, {len(c['dark'])} dark · text roles: {len(spec['typography']['roles'])}"
          f" · extras: {len(spec['typography']['extras'])} · spacing: {len(spec['spacing'])}"
          f" · radius: {len(spec['radius'])} · sizes: {len(spec['sizes'])}")
    print(f"  unmapped: {len(spec['unmapped'])} · conflicts: {len(spec['conflicts'])} · notes: {len(spec['notes'])}")
    print("Next: read the rest of the hand-off (prose, components, screenshots) and complete the spec —\n"
          "extensionColors (success, warning required), conflicts, components — then run validate_theme_spec.py.")


if __name__ == "__main__":
    main()
