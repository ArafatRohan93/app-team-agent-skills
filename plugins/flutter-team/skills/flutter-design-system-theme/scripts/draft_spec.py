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
  dtcg    W3C Design Tokens / Figma variables / Tokens Studio JSON ($value or value): palette and
          semantic tiers (roles suggested from semantic names), composite text styles, dimension
          objects, sizes, component radii, modes ($extensions or --dark <file>)
  css     CSS custom properties (--name: value;), e.g. from a web export or Tailwind theme
  claude  Claude Design System (claude.ai): project/tokens.json, or a folder containing it
  html    any HTML design: a Claude Design page export (bundled or rendered), an HTML/CSS
          mock-up, a Tailwind or React prototype. Rendered in a local headless Chrome when
          one is installed (--render auto|always|never), else read statically. Writes
          <input>.evidence.md with how every value is used.
  figma-css  Figma "Copy as CSS" text (layers selected → Copy as CSS). Layer names give kinds,
          nesting is rebuilt from auto-layout order. Writes <input>.evidence.md.

  --screens <figma copy | html>  with any token input: check the tokens against the drawn screens
          (conflicts where a role's drawn colour differs, drift, unused tokens, untokened colours).

Usage:
  python3 draft_spec.py --from stitch design/sources/DESIGN.md -o design/theme.spec.json
  python3 draft_spec.py --from css design/sources/tokens.css --name "Acme" -o design/theme.spec.json
"""

import argparse
import collections
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


def parse_css(text):
    return {m.group(1): m.group(2).strip() for m in re.finditer(r"--([A-Za-z0-9_-]+)\s*:\s*([^;{}]+)(?=[;}])", text)}


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
    if ("screen" in n or "page" in n) and re.search(r"margin|gutter|padding|inset|edge", n):
        return "spacing", "screenPadding"
    if "gutter" in n:
        return "spacing", "spacingGutter"
    if "touch" in n:
        return "sizes", "minTouchTarget"
    core = re.sub(r"^(space|spacing|gap)[-_.]?", "", n)
    return "spacing", "spacing" + (scale_suffix(core) if core else "Base")


def radius_key(name):
    n = name.lower()
    core = re.sub(r"^(rounded|radius|radii|corner)[-_.]?", "", n)
    if core in ("", "default", "base"):
        return "radiusDefault"
    if core in ("pill", "full", "round", "circle", "stadium", "max"):
        return "radiusFull"
    return "radius" + scale_suffix(core)


def numeric_key(prefix, core, value, contract, taken):
    """'4' in a numeric scale → the contract key with that default value (spacing 16 → spacingLg), else spacing4."""
    for key, default in contract.items():
        if key.startswith(prefix) and default == value and key not in taken:
            return key
    return prefix + core.replace(".", "p")


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
    deprecated_seen, primitives = {}, []
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
            primitives.append(f"{token} {value}")
        else:
            spec["unmapped"].append({"token": token, "value": value,
                                     "reason": "no Material role with this name — map by meaning or add as extensionColor"})
    if primitives:
        spec["notes"].append("Palette primitives referenced by semantic tokens (not roles themselves): "
                             + ", ".join(primitives) + ".")
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
            if str(line).strip().endswith(("px", "rem", "em", "%", "pt")):
                lh = to_dp(line, size)
            else:  # a bare number: a multiplier (1.5), or px when it's too big to be one (Tokens Studio "20")
                lh = float(line) if float(line) > 4 else float(line) * size
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
        core = re.sub(r"^(rounded|radius|radii|corner)[-_.]?", "", token.lower())
        key = numeric_key("radius", core, v, ts.CONTRACT_RADIUS, spec["radius"]) if re.fullmatch(r"\d+(\.\d+)?", core) \
            else radius_key(token)
        spec["radius"][key] = {"value": round_dp(v), "token": token,
                               "source": f"{where} {token if '.' in token else 'rounded.' + token}"}
    for token, raw in tokens_by_group.get("spacing", {}).items():
        v = to_dp(raw)
        if v is None:
            spec["unmapped"].append({"token": token, "value": raw, "reason": "spacing not parseable"})
            continue
        core = re.sub(r"^(space|spacing|gap)[-_.]?", "", token.lower())
        group, key = ("spacing", numeric_key("spacing", core, v, ts.CONTRACT_SPACING, spec["spacing"])) \
            if re.fullmatch(r"\d+(\.\d+)?", core) else spacing_key(token)
        spec[group][key] = {"value": round_dp(v), "token": token,
                            "source": f"{where} {token if '.' in token else 'spacing.' + token}"}

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


PLATFORM_FONT = re.compile(r"^(sf pro|sf compact|sf ui|\.sf|san francisco|new york)", re.I)


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
        if PLATFORM_FONT.match(fam):
            spec["notes"].append(
                f"The design uses {fam} ({n} text elements), Apple's system font. It can't be bundled: leave "
                "typography.fontFamily unset so iOS shows SF and Android shows Roboto, or ask the user for a "
                "bundled font to use on both.")
        else:
            spec["typography"]["fontFamily"] = {"value": fam, "source": f"{where} font on {n} text elements"}
    weights = sorted({w for (_, w) in ev["type"]})
    spec["notes"] += [
        f"Drafted from {'the Figma CSS copy' if ev.get('kind') == 'figma-css' else 'HTML'} ({ev['mode']}) on "
        f"{len(ev['screens'])} screens. Roles not named by a CSS variable or style are "
        f"inferences from usage — see {Path(label['file']).stem}.evidence.md.",
        f"Font weights in use: {weights}.",
    ]
    if ev["legends"]:
        spec["notes"].append(f"{len(ev['legends'])} legend cards name roles for their colours — read them before mapping.")
    return spec


def draft_dtcg(data, label, name, dark_data=None):
    """W3C design tokens: palette and semantic tiers, composite text styles, dimensions, sizes, component radii.

    Colours named after Material roles map directly. Semantic colours get a *suggested* role
    (`suggest` in unmapped) for the agent to confirm; palette primitives are kept by name.
    """
    import dtcg_tokens as dt
    toks = dt.tokens(data)
    dark_toks = dt.tokens(dark_data) if dark_data else {}
    where = label["where"]
    value = {p: dt.scalar(dt.resolve(t["value"], toks)) for p, t in toks.items()}
    alias_of = {p: dt.REF_FULL.match(t["value"]).group(1).strip() for p, t in toks.items()
                if isinstance(t["value"], str) and dt.REF_FULL.match(t["value"])}
    referenced = set().union(*(dt.refs_in(t["value"]) for t in toks.values())) if toks else set()
    has_semantic = any(dt.is_semantic(p, t["value"]) for p, t in toks.items())

    def kind(path, tok, v):
        ty, p = (tok["type"] or "").lower(), path.lower()
        if ty == "color" or (not ty and isinstance(v, str) and normalize_hex(v)):
            return "color"
        if ty == "typography" or (isinstance(v, dict) and "fontSize" in v):
            return "typography"
        if ty == "shadow" or re.search(r"shadow|elevation", p) and ty in ("", "shadow"):
            return "shadow"
        if ty in ("fontfamily", "fontweight") or (ty in ("", "dimension", "number") and re.search(
                r"font|line-?height|letter-?spacing|tracking|leading", p)):
            return "typeScale"
        if ty in ("", "dimension", "number"):
            if re.search(r"radius|radii|rounded|corner", p):
                return "radius"
            if re.search(r"spacing|space|gap|gutter|margin|padding|inset", p):
                return "spacing"
            if re.search(r"size|sizing|height|width|icon|dimension", p):
                return "size"
        return "other"

    def describe(path):
        d = toks[path]["description"]
        return f" ({d})" if d else ""

    def src(path):
        return f"{where} {path}" + (f" → {alias_of[path]}" if path in alias_of else "") + describe(path)

    def dark_value(path):
        twin = dark.get(dt.clean_name(path)) if dt.mode_of(path) == "light" else None
        if twin:
            return twin[1]
        tok = toks[path]
        mode = next((v for k, v in tok["modes"].items() if "dark" in k.lower()), None)
        if mode is None and path in dark_toks:
            mode = dark_toks[path]["value"]
        return normalize_hex(dt.scalar(dt.resolve(mode, {**toks, **dark_toks}))) if mode is not None else None

    groups = {"typography": {}, "rounded": {}, "spacing": {}, "typeScale": {}}
    colours, shadows, sizes, others = [], [], [], []
    light, dark = {}, {}
    for path, tok in toks.items():
        k = kind(path, tok, value[path])
        if k == "color":
            colours.append(path)
        elif k == "typography" and isinstance(value[path], dict):
            style = dict(value[path])
            if "fontFamily" in style:
                style["fontFamily"] = dt.font_family(style["fontFamily"])[0]
            groups["typography"][dt.clean_name(re.sub(r"^(typography|type|text-?styles?|font)[.]", "", path))] = style
        elif k == "radius":
            groups["rounded"][path] = value[path]
        elif k == "spacing":
            groups["spacing"][path] = value[path]
        elif k == "typeScale":
            groups["typeScale"][path] = value[path]
        elif k == "shadow":
            shadows.append(path)
        elif k == "size":
            sizes.append(path)
        else:
            others.append(path)

    # Type-scale primitives that composite styles already use aren't open questions.
    type_refs = set().union(*(dt.refs_in(toks[p]["value"]) for p in toks
                              if kind(p, toks[p], value[p]) == "typography")) if groups["typography"] else set()
    scale_used = {p: v for p, v in groups["typeScale"].items() if p in type_refs}
    if groups["typography"]:
        groups["typeScale"] = {p: v for p, v in groups["typeScale"].items() if p not in type_refs}
    spec = draft({k: v for k, v in groups.items() if k != "typeScale" or not groups["typography"]}, label, name)
    if groups["typography"]:
        literal = {str(v) for st in groups["typography"].values() for v in st.values()}
        for p, v in groups["typeScale"].items():
            if str(v) in literal or (isinstance(v, (int, float)) and f"{v}px" in literal):
                scale_used[p] = v  # the styles repeat this value instead of referencing it
                continue
            spec["unmapped"].append({"token": p, "value": v, "reason": "type primitive not used by any text style"})
    if scale_used:
        spec["notes"].append(f"{len(scale_used)} type primitives (font.size / weight / lineHeight / letterSpacing) "
                             "are composed into the text styles; they need no mapping of their own.")

    # --- fonts: the default family and its real fallbacks
    fams = [p for p in toks if (toks[p]["type"] or "").lower() == "fontfamily"]
    fam = spec["typography"].get("fontFamily", {}).get("value")
    for p in fams:
        first, rest = dt.font_family(value[p])
        if first == fam and rest:
            spec["typography"]["fontFamilyFallback"] = rest
    other_fams = sorted({dt.font_family(value[p])[0] for p in fams} - {fam})
    if other_fams:
        users = [n for n, st in groups["typography"].items() if st.get("fontFamily") in other_fams]
        spec["notes"].append(f"Other font families: {', '.join(other_fams)}"
                             + (f" (used by {', '.join(users)})" if users else "")
                             + ". Text styles here can't set their own family: tell the user, or give those "
                               "widgets the family in code.")

    # --- colours
    for path in colours:
        hx = normalize_hex(value[path])
        if not hx:
            spec["unmapped"].append({"token": path, "value": value[path], "reason": "colour value not parseable"})
            continue
        (dark if dt.mode_of(path) == "dark" else light)[dt.clean_name(path)] = (path, hx)
    primitives, suggested = [], collections.defaultdict(list)
    for cname, (path, hx) in light.items():
        dpath = dark.get(cname)
        dhex = dpath[1] if dpath else dark_value(path)
        role = camel(cname)
        role = ROLE_ALIASES.get(role, role)
        if role in ts.COLOR_ROLES:
            spec["colors"]["light"][role] = {"value": hx, "token": path, "source": src(path)}
            if dhex:
                spec["colors"]["dark"][role] = {"value": dhex, "token": dpath[0] if dpath else path,
                                                "source": src(dpath[0] if dpath else path) + " [dark]"}
            continue
        semantic = dt.is_semantic(path, toks[path]["value"]) or not dt.is_raw_palette(path)
        if has_semantic and path in referenced and not dt.is_semantic(path, toks[path]["value"]):
            semantic = False  # a primitive that semantic tokens point at, whatever its name
        if has_semantic and not semantic:
            if path in referenced:
                primitives.append(f"{cname} {hx}")
            else:
                spec["unmapped"].append({"token": path, "value": hx, "reason": "palette colour that no semantic token "
                                         "uses — usually not needed; keep it only if it's a brand or partner colour"
                                         + describe(path)})
            continue
        sug, usage = dt.suggest_role(path)
        entry = {"token": path, "value": hx}
        if dhex:
            entry["dark"] = dhex
        if sug:
            entry["suggest"] = sug
            if usage:
                entry["usage"] = usage
            suggested[sug].append((path, hx))
        entry["reason"] = (("semantic colour" if dt.is_semantic(path, toks[path]["value"]) else "named colour")
                           + describe(path)
                           + (f" — suggested: {sug}" + (f" (usage {usage})" if usage else "") if sug
                              else " — no role suggested: map by meaning or add as an extension colour")
                           + (f" [→ {alias_of[path]}]" if path in alias_of else ""))
        spec["unmapped"].append(entry)
    for path, (cname, hx) in ((p, (c, h)) for c, (p, h) in dark.items() if c not in light):
        spec["unmapped"].append({"token": path, "value": hx, "reason": "dark-mode colour with no light counterpart"})
    if primitives:
        spec["notes"].append("Palette primitives referenced by semantic tokens (use the semantic names, not these): "
                             + ", ".join(primitives) + ".")
    apply_suggestions(spec, suggested, toks, src, dark_value, light, dark)
    if dark or any("dark" in e for e in spec["unmapped"]) or spec["colors"]["dark"]:
        spec["notes"].append("The tokens include dark-mode values: use them for colors.dark instead of deriving.")

    # --- text styles: a purpose-named style becomes the role its name suggests when it's the only candidate
    by_role = collections.defaultdict(list)
    for key, st in spec["typography"]["extras"].items():
        role = dt.suggest_type_role(st.get("token", key), st.get("fontSize"))
        if role and role not in spec["typography"]["roles"]:
            by_role[role].append(key)
    shared = []
    for role, keys in by_role.items():
        if len(keys) == 1:
            st = spec["typography"]["extras"].pop(keys[0])
            st["source"] += f" (role suggested by the name '{st.get('token', keys[0])}' — confirm)"
            spec["typography"]["roles"][role] = st
        else:
            shared.append(f"{role}: {', '.join(keys)}")
    if shared:
        spec["notes"].append("Text styles whose names suggest the same role (they stay extras; pick one per role "
                             "if the Material widgets should use it): " + "; ".join(shared) + ".")
    spec["notes"] = [n for n in spec["notes"] if not n.startswith("Several font families used")]

    # --- component-named radii → components
    for path, raw in groups["rounded"].items():
        v = to_dp(raw)
        for comp, prop in dt.component_targets(path) if v is not None else []:
            spec["components"].setdefault(comp, {})[prop] = round_dp(v)
            spec["components"][comp]["source"] = f"{where} {path}" + describe(path)

    # --- sizes
    for path in sizes:
        v = to_dp(value[path])
        key = dt.size_key(path)
        if v is None:
            spec["unmapped"].append({"token": path, "value": value[path], "reason": "size not parseable"})
        elif key is None:
            spec["notes"].append(f"{path} = {v:g}: a layout fact (the design's frame), not a theme value.")
        else:
            spec["sizes"][key] = {"value": round_dp(v), "token": path, "source": src(path)}

    # --- shadows and everything else
    for path in shadows:
        layers = value[path] if isinstance(value[path], list) else [value[path]]
        text = ", ".join(" ".join(str(layer.get(k, "")) for k in ("offsetX", "offsetY", "blur", "spread", "color"))
                         + (" inset" if layer.get("inset") else "") for layer in layers if isinstance(layer, dict))
        spec["unmapped"].append({"token": path, "value": text or value[path],
                                 "reason": "shadow — Material 3 uses tonal surfaces; keep components.card.elevation 0, "
                                           "or ask whether cards need elevation" + describe(path)})
    for path in others:
        ty = toks[path]["type"] or "untyped"
        spec["unmapped"].append({"token": path, "value": value[path],
                                 "reason": f"{ty} token — not a theme value" + describe(path)})
    if isinstance(data, dict) and data.get("$description"):
        spec["notes"].append(f"Token file: {data['$description']}")
    return spec


# Which drawn usage shows a role. Used by --screens to check tokens against the screens.
ROLE_EVIDENCE = [
    ("primary", ("background · button",), "filled-button fill"),
    ("surface", ("background · screen",), "screen background"),
    ("onSurface", ("text",), "body text"),
    ("outline", ("border · field",), "field border"),
    ("outlineVariant", ("border · card/panel", "background · divider"), "card border / divider"),
]
NEAR = 3.0  # ΔE (CIE76) below which two colours are the same colour drawn twice
CLOSE = 10.0  # ΔE within which a drawn colour's nearest token is worth naming


def _lab(h):
    h = h.lstrip("#")[-6:]
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
           for c in (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))]
    x = (0.4124 * lin[0] + 0.3576 * lin[1] + 0.1805 * lin[2]) / 0.95047
    y = 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]
    z = (0.0193 * lin[0] + 0.1192 * lin[1] + 0.9505 * lin[2]) / 1.08883
    f = [t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116 for t in (x, y, z)]
    return 116 * f[1] - 16, 500 * (f[0] - f[1]), 200 * (f[1] - f[2])


def _dist(a, b):
    """Perceptual difference (ΔE76). Pale colours sit close in RGB but read as different, so RGB won't do."""
    return sum((p - q) ** 2 for p, q in zip(_lab(a), _lab(b))) ** 0.5


def load_screens(path, render="auto"):
    """Evidence for --screens: a Figma Copy-as-CSS text or an HTML page. Writes <file>.evidence.md."""
    import figma_css as fc
    import html_evidence as he
    path = Path(path)
    text = path.read_text(errors="ignore")
    ev = fc.extract(path, normalize_hex) if fc.looks_like(text) else he.extract(path, normalize_hex, render=render)
    ev_path = path.with_name(path.stem + ".evidence.md")
    ev_path.write_text(he.evidence_markdown(ev, path.name))
    return ev, ev_path


def cross_check(spec, ev, where):
    """Compare the drafted token colours with what the screens draw: conflicts where a role's drawn colour differs,
    notes for drift (near-identical values), tokens the screens don't use, and drawn colours with no token."""
    drawn = {h: e for h, e in ev["colours"].items()}
    light = spec["colors"]["light"]
    confirmed = []
    for role, keys, desc in ROLE_EVIDENCE:
        counts = collections.Counter({h: sum(e["by"].get(k, 0) for k in keys) for h, e in drawn.items()})
        counts = +counts
        if not counts:
            continue
        top, n = counts.most_common(1)[0]
        if n < 3:
            continue
        drawn_src = f"{where}: drawn ×{n} as {desc}"
        entry = light.get(role)
        if entry is None:
            spec["notes"].append(f"The screens suggest {role} = {top} ({desc} ×{n}); the tokens have no {role}.")
            continue
        if entry["value"].upper() == top.upper():
            confirmed.append(role)
            continue
        near = _dist(entry["value"], top) <= NEAR
        rec = entry["value"] if near else top
        reason = (f"The tokens give {entry['value']}, the screens draw {top} ×{n} as {desc}. "
                  + ("They're near-identical: the token is recommended and the drawing is drift."
                     if near else "They differ visibly: the drawn value is recommended, since it's what the "
                                  "designer shows. The tokens may be out of date — confirm with the designer."))
        existing = next((c for c in spec["conflicts"] if c["target"] == f"colors.light.{role}"), None)
        if existing:
            if all(c["value"].upper() != top.upper() for c in existing["candidates"]):
                existing["candidates"].append({"value": top, "source": drawn_src})
            existing["recommendation"] = rec if not near else existing["recommendation"]
            existing["reason"] += " " + reason
        else:
            spec["conflicts"].append({"target": f"colors.light.{role}", "status": "open",
                                      "candidates": [{"value": entry["value"], "source": entry["source"]},
                                                     {"value": top, "source": drawn_src}],
                                      "recommendation": rec, "reason": reason})
        if not near:
            entry.update(value=top, source=entry["source"] + f" — screens: {drawn_src} (recommended)")
    # every other token colour: drawn exactly, drawn slightly differently, or not drawn at all
    tokens = [(f"colors.light.{r}", e["value"]) for r, e in light.items()] + \
             [(f"ext.{n}", e["light"]["value"]) for n, e in spec["extensionColors"].items() if e.get("light")]
    drift, unused = [], []
    for name, value in tokens:
        if any(value.upper() == h.upper() for h in drawn):
            continue
        close = sorted((h for h in drawn if _dist(value, h) <= NEAR), key=lambda h: -drawn[h]["count"])
        (drift.append(f"{name} {value} is drawn as {close[0]} ×{drawn[close[0]]['count']}") if close
         else unused.append(f"{name} {value}"))
    orphans = []
    for h, e in sorted(drawn.items(), key=lambda kv: -kv[1]["count"]):
        if e["count"] < 5 or any(_dist(h, v) <= NEAR for _, v in tokens):
            continue
        nearest = min(tokens, key=lambda t: _dist(h, t[1]), default=None)
        hint = (f"; closest token {nearest[0]} {nearest[1]}, ΔE {_dist(h, nearest[1]):.1f}"
                if nearest and _dist(h, nearest[1]) <= CLOSE else "")
        orphans.append(f"{h} ×{e['count']} ({', '.join(k for k, _ in e['by'].most_common(2))}{hint})")
    if confirmed:
        spec["notes"].append(f"Confirmed by the screens ({where}): {', '.join(confirmed)}.")
    if drift:
        spec["notes"].append("Token colours drawn slightly differently in the screens (drift — ask which is right): "
                             + "; ".join(drift) + ".")
    if orphans:
        spec["notes"].append("Colours the screens use often that no token matches (map them, or ask the designer "
                             "which token they should be): " + "; ".join(orphans) + ".")
    if unused:
        spec["notes"].append(f"Token colours not seen in these screens ({len(unused)}): "
                             + ", ".join(unused[:30]) + ("…" if len(unused) > 30 else "") + ".")


NAME_PREFERENCE = ("default", "primary", "base", "page", "body", "main", "regular")


def apply_suggestions(spec, suggested, toks, src, dark_value, light, dark):
    """Map suggested roles: one value → set it; several → open conflict, the others become extension colours."""
    import dtcg_tokens as dt
    unmapped = {u["token"]: u for u in spec["unmapped"] if "suggest" in u}
    mapped = set()

    def ext_usage(path):
        seg = (dt.meaning(path) or [""])[0]
        return {"text": "text", "fg": "text", "foreground": "text", "border": "border", "divider": "border",
                "stroke": "border", "outline": "border", "icon": "icon"}.get(seg, "fill")

    def add_ext(name, path, hx, usage):
        dh = dark_value(path)
        spec["extensionColors"][name] = {"usage": usage, "light": {"value": hx, "token": path, "source": src(path)},
                                         **({"dark": {"value": dh, "source": src(path) + " [dark]"}} if dh else {})}
        mapped.add(path)

    for role, cands in suggested.items():
        values = list(dict.fromkeys(h for _, h in cands))
        if role.startswith("ext."):
            name = role[4:]
            if len(values) == 1:
                add_ext(name, cands[0][0], values[0], unmapped[cands[0][0]].get("usage", ext_usage(cands[0][0])))
            else:
                for path, hx in cands:
                    add_ext(camel(dt.clean_name(path)), path, hx, unmapped[path].get("usage", ext_usage(path)))
            continue
        ranked = sorted(cands, key=lambda c: (not any(w in dt.meaning(c[0]) for w in NAME_PREFERENCE),
                                              len(dt.meaning(c[0]))))
        best_path, best = ranked[0]
        named = spec["colors"]["light"].get(role)
        if named:  # a token named after the role wins; a different suggested value is a conflict
            others = [(p, h) for p, h in cands if h != named["value"]]
            mapped.update(p for p, h in cands if h == named["value"])
            if others:
                spec["conflicts"].append({
                    "target": f"colors.light.{role}", "status": "open",
                    "candidates": [{"value": named["value"], "source": named["source"]}]
                                  + [{"value": h, "source": src(p)} for p, h in others],
                    "recommendation": named["value"],
                    "reason": f"'{named['token']}' is named {role}; {', '.join(p for p, _ in others)} also reads as "
                              f"{role}. The named token is recommended; the others are kept as extension colours."})
                for path, hx in others:
                    add_ext(camel(dt.clean_name(path)), path, hx, ext_usage(path))
            continue
        entry = {"value": best, "token": best_path,
                 "source": src(best_path) + " (role suggested by the semantic name — confirm)"}
        spec["colors"]["light"][role] = entry
        dh = dark_value(best_path)
        if dh:
            spec["colors"]["dark"][role] = {"value": dh, "token": best_path, "source": src(best_path) + " [dark]"}
        mapped.update(p for p, h in cands if h == best)
        if len(values) > 1:
            spec["conflicts"].append({
                "target": f"colors.light.{role}", "status": "open",
                "candidates": [{"value": h, "source": src(p)} for p, h in cands],
                "recommendation": best,
                "reason": f"{len(cands)} semantic tokens suggest {role}. '{best_path}' is recommended by its name; "
                          "the others are kept as extension colours. Confirm against the screens."})
            for path, hx in cands:
                if hx != best:
                    add_ext(camel(dt.clean_name(path)), path, hx, ext_usage(path))
    spec["unmapped"] = [u for u in spec["unmapped"] if u["token"] not in mapped]
    if mapped:
        spec["notes"].append(f"{len(mapped)} colours were mapped from their token names (role sources say "
                             "'suggested' — confirm them against the design). Unmapped entries keep their suggestion.")
    for need, words in (("success", "success|positive|accepted|complete|green"),
                        ("warning", "warning|caution|pending|attention|amber|yellow")):
        if need not in spec["extensionColors"]:
            near = [n for n in spec["extensionColors"] if re.search(words, n, re.I)]
            spec["notes"].append(f"No '{need}' token. The app shell requires ext.{need}: "
                                 + (f"the closest is {', '.join(near)} — propose it " if near else "propose one ")
                                 + "as an assumption (an open conflict with that single candidate).")


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
    ap.add_argument("--from", dest="kind", required=True,
                    choices=["stitch", "dtcg", "css", "claude", "html", "figma-css"])
    ap.add_argument("input", help="Design hand-off file")
    ap.add_argument("-o", "--output", required=True, help="Where to write the draft spec")
    ap.add_argument("--name", help="Design system name (default: from the input or file name)")
    ap.add_argument("--force", action="store_true", help="Overwrite an existing spec")
    ap.add_argument("--render", choices=["auto", "always", "never"], default="auto",
                    help="html only: read computed styles in a headless browser (auto = when one is installed)")
    ap.add_argument("--dark", help="dtcg only: a second token file holding the dark-mode values (same paths)")
    ap.add_argument("--screens", help="token inputs: screens to check the tokens against — a Figma Copy-as-CSS "
                                      "text or an HTML page (writes <file>.evidence.md)")
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
                                         "css": "css-custom-properties", "claude": "claude-design-system", "html": "html",
                                         "figma-css": "figma-css"}[args.kind]}
    aliases = {}
    if args.kind == "stitch":
        fm = parse_front_matter(text)
        groups = {k: fm.get(k, {}) for k in ("colors", "typography", "rounded", "spacing")}
        label["where"] = f"{path.name} front matter"
        name = args.name or fm.get("name") or path.stem
    elif args.kind == "dtcg":
        data = json.loads(text)
        label["where"] = path.name
        name = args.name or path.stem
    elif args.kind in ("html", "figma-css"):
        import html_evidence as he
        if args.kind == "figma-css":
            import figma_css as fc
            ev = fc.extract(path, normalize_hex)
        else:
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
    elif args.kind == "dtcg":
        dark_data = json.loads(Path(args.dark).read_text()) if args.dark else None
        spec = draft_dtcg(data, label, name, dark_data)
    elif args.kind in ("html", "figma-css"):
        spec = draft_html(ev, label, name)
    else:
        spec = draft(groups, label, name, aliases)
    if args.screens:
        if args.kind in ("html", "figma-css"):
            sys.exit("--screens checks a token input against screens; this input already is screens")
        sev, sev_path = load_screens(args.screens, args.render)
        spec["sources"].append({"id": "screens", "type": sev["kind"], "file": str(args.screens)})
        cross_check(spec, sev, Path(args.screens).name)
        print(f"screens: {sev_path} ({sev['mode']}; {len(sev['screens'])} screens, {len(sev['colours'])} colours)")
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
