"""Theme spec rules shared by validate_theme_spec.py and generate_theme.py.

The theme spec (design/theme.spec.json in the app) is the single hand-off
between the AI extraction step and the deterministic generator. See
references/spec-format.md for the format.
"""

import json
import re
from pathlib import Path

SPEC_VERSION = 1

# Material 3 ColorScheme roles supported by Flutter's ColorScheme.fromSeed.
COLOR_ROLES = [
    "primary", "onPrimary", "primaryContainer", "onPrimaryContainer",
    "primaryFixed", "primaryFixedDim", "onPrimaryFixed", "onPrimaryFixedVariant",
    "secondary", "onSecondary", "secondaryContainer", "onSecondaryContainer",
    "secondaryFixed", "secondaryFixedDim", "onSecondaryFixed", "onSecondaryFixedVariant",
    "tertiary", "onTertiary", "tertiaryContainer", "onTertiaryContainer",
    "tertiaryFixed", "tertiaryFixedDim", "onTertiaryFixed", "onTertiaryFixedVariant",
    "error", "onError", "errorContainer", "onErrorContainer",
    "surface", "onSurface", "surfaceDim", "surfaceBright",
    "surfaceContainerLowest", "surfaceContainerLow", "surfaceContainer",
    "surfaceContainerHigh", "surfaceContainerHighest", "onSurfaceVariant",
    "outline", "outlineVariant", "shadow", "scrim",
    "inverseSurface", "onInverseSurface", "inversePrimary", "surfaceTint",
]
DEPRECATED_ROLES = {
    "background": "surface",
    "onBackground": "onSurface",
    "surfaceVariant": "surfaceContainerHighest",
}

# Extension colors the flutter-app-structure shell's widgets and tests rely on.
REQUIRED_EXTENSION_COLORS = ["success", "warning"]

TYPE_ROLES = [
    "displayLarge", "displayMedium", "displaySmall",
    "headlineLarge", "headlineMedium", "headlineSmall",
    "titleLarge", "titleMedium", "titleSmall",
    "bodyLarge", "bodyMedium", "bodySmall",
    "labelLarge", "labelMedium", "labelSmall",
]

# Material 3 (2021) type scale — used for any role the design system omits.
# (fontSize, lineHeight, fontWeight, letterSpacing)
MATERIAL_TYPE_SCALE = {
    "displayLarge": (57, 64, 400, -0.25),
    "displayMedium": (45, 52, 400, 0.0),
    "displaySmall": (36, 44, 400, 0.0),
    "headlineLarge": (32, 40, 400, 0.0),
    "headlineMedium": (28, 36, 400, 0.0),
    "headlineSmall": (24, 32, 400, 0.0),
    "titleLarge": (22, 28, 400, 0.0),
    "titleMedium": (16, 24, 500, 0.15),
    "titleSmall": (14, 20, 500, 0.1),
    "bodyLarge": (16, 24, 400, 0.5),
    "bodyMedium": (14, 20, 400, 0.25),
    "bodySmall": (12, 16, 400, 0.4),
    "labelLarge": (14, 20, 500, 0.1),
    "labelMedium": (12, 16, 500, 0.5),
    "labelSmall": (11, 16, 500, 0.5),
}

# Dimension names the shell's widgets use. Missing ones fall back to these.
CONTRACT_SPACING = {
    "spacingXxs": 2, "spacingXs": 4, "spacingSm": 8, "spacingMd": 12,
    "spacingLg": 16, "spacingXl": 24, "spacing2xl": 32, "spacing3xl": 48,
    "screenPadding": 24,
}
CONTRACT_RADIUS = {
    "radiusSm": 6, "radiusMd": 12, "radiusLg": 16, "radiusXl": 24, "radiusFull": 9999,
}
CONTRACT_SIZES = {
    "buttonHeight": 48, "inputHeight": 48, "iconSm": 16, "iconMd": 24, "iconLg": 32,
}

SCHEME_VARIANTS = ["tonalSpot", "fidelity", "monochrome", "neutral", "vibrant",
                   "expressive", "content", "rainbow", "fruitSalad"]

# Component tokens the generator understands: key → allowed properties.
COMPONENTS = {
    "filledButton": {"height", "radius", "textStyle", "background", "foreground", "pressedBackground"},
    "outlinedButton": {"height", "radius", "textStyle", "background", "foreground", "border", "borderWidth"},
    "textButton": {"textStyle", "foreground", "horizontalPadding"},
    "input": {"height", "radius", "fill", "border", "focusBorder", "focusBorderWidth", "errorBorder",
              "paddingHorizontal", "paddingVertical"},
    "appBar": {"background", "foreground", "titleStyle", "elevation", "centerTitle"},
    "card": {"radius", "color", "border", "elevation"},
    "chip": {"radius", "background", "border", "label", "textStyle"},
    "divider": {"color", "thickness"},
    "bottomSheet": {"background", "topRadius", "barrierColor", "barrierOpacity"},
}
COMPONENT_TEXT_PROPS = {"textStyle", "titleStyle"}
COMPONENT_BOOL_PROPS = {"centerTitle"}
# Defaults the generator uses when a component property is left out.
COMPONENT_DEFAULTS = {
    "filledButton": {"height": "sizes.buttonHeight", "radius": "9999 (pill)", "textStyle": "labelLarge",
                     "background": "primary", "foreground": "onPrimary"},
    "outlinedButton": {"height": "filledButton.height", "radius": "filledButton.radius", "textStyle": "filledButton.textStyle",
                       "foreground": "onSurface", "border": "outline", "borderWidth": 1},
    "textButton": {"textStyle": "labelLarge", "foreground": "primary"},
    "input": {"height": "sizes.inputHeight", "radius": "radius.radiusMd", "fill": "surfaceContainer", "border": "outline",
              "focusBorder": "primary", "focusBorderWidth": 2, "errorBorder": "error", "paddingHorizontal": 16, "paddingVertical": 12},
    "card": {"radius": "radius.radiusMd", "elevation": 0},
    "chip": {"radius": "radius.radiusSm", "textStyle": "labelLarge"},
    "divider": {"color": "outlineVariant", "thickness": 1},
    "bottomSheet": {"background": "surfaceContainerLow", "topRadius": "radius.radiusXl", "barrierColor": "scrim", "barrierOpacity": 0.32},
    "appBar": {"background": "surface", "foreground": "onSurface", "titleStyle": "titleLarge", "elevation": 0, "centerTitle": False},
}
COMPONENT_COLOR_PROPS = {"background", "foreground", "pressedBackground", "border", "fill",
                         "focusBorder", "errorBorder", "color", "label", "barrierColor"}

# WCAG pairs checked in both modes: (background, foreground, minimum ratio).
CONTRAST_PAIRS = [
    ("primary", "onPrimary", 4.5),
    ("primaryContainer", "onPrimaryContainer", 4.5),
    ("secondary", "onSecondary", 4.5),
    ("secondaryContainer", "onSecondaryContainer", 4.5),
    ("tertiary", "onTertiary", 4.5),
    ("tertiaryContainer", "onTertiaryContainer", 4.5),
    ("error", "onError", 4.5),
    ("errorContainer", "onErrorContainer", 4.5),
    ("surface", "onSurface", 4.5),
    ("surface", "onSurfaceVariant", 4.5),
    ("surfaceContainerLowest", "onSurface", 4.5),
    ("surfaceContainerLow", "onSurface", 4.5),
    ("surfaceContainer", "onSurface", 4.5),
    ("surfaceContainerHigh", "onSurface", 4.5),
    ("surfaceContainerHighest", "onSurface", 4.5),
    ("inverseSurface", "onInverseSurface", 4.5),
    ("surface", "outline", 3.0),
]
# Interactive boundaries (WCAG 1.4.11, 3:1): (component, border prop, default border, bg prop, default bg).
COMPONENT_BOUNDARY_PAIRS = [
    ("input", "border", "outline", "fill", "surfaceContainer"),
    ("outlinedButton", "border", "outline", "background", "surface"),
]


def component_boundary_pairs(spec):
    """[(pair_id, bg_ref, fg_ref)] for interactive borders the theme actually uses."""
    comps = spec.get("components") or {}
    out = []
    for comp, bprop, bdef, gprop, gdef in COMPONENT_BOUNDARY_PAIRS:
        c = comps.get(comp) or {}
        if c.get(bprop) == "none":
            # Borderless control: its fill is the boundary, so check the fill against the surface.
            out.append((f"{comp}.{gprop}", "surface", c.get(gprop, gdef)))
        else:
            out.append((f"{comp}.{bprop}", c.get(gprop, gdef), c.get(bprop, bdef)))
    return out


# usage → WCAG minimum against surface. largeText = ≥24dp, or ≥18.66dp bold.
EXTENSION_USAGE_MIN = {"text": 4.5, "largeText": 3.0, "icon": 3.0, "border": None, "fill": None}

HEX_RE = re.compile(r"^#([0-9A-Fa-f]{6}|[0-9A-Fa-f]{8})$")
IDENT_RE = re.compile(r"^[a-z][A-Za-z0-9]*$")


class SpecError(Exception):
    pass


def load_spec(path):
    path = Path(path)
    if not path.exists():
        raise SpecError(f"Spec not found: {path}")
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as e:
        raise SpecError(f"{path} is not valid JSON: {e}") from e


# ---------------------------------------------------------------- colour maths


def hex_to_rgb(value):
    h = value.lstrip("#")
    if len(h) == 8:  # #AARRGGBB
        h = h[2:]
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def argb_literal(value):
    h = value.lstrip("#").upper()
    return f"0x{h}" if len(h) == 8 else f"0xFF{h}"


def relative_luminance(value):
    def channel(c):
        c = c / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (channel(c) for c in hex_to_rgb(value))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(a, b):
    la, lb = relative_luminance(a), relative_luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


# ---------------------------------------------------------------- accessors


def color_value(entry):
    return entry.get("value") if isinstance(entry, dict) else None


def mode_colors(spec, mode):
    return (spec.get("colors") or {}).get(mode) or {}


def extension_colors(spec):
    return spec.get("extensionColors") or {}


def component_color_refs(spec):
    for name, props in (spec.get("components") or {}).items():
        for prop, value in props.items():
            if prop in COMPONENT_COLOR_PROPS and value != "none":
                yield name, prop, value


def accepted_exception(spec, mode, pair_id):
    for exc in spec.get("acceptedContrastExceptions") or []:
        if exc.get("pair") == pair_id and exc.get("mode") in (mode, "both"):
            return exc
    return None


def contrast_results(spec):
    """Contrast for pairs whose colours are both provided in the spec.

    Derived colours (dark mode, unprovided roles) are checked by the generated
    Dart test instead, because Flutter computes them at runtime.
    """
    results = []
    ext = extension_colors(spec)
    for mode in ("light", "dark"):
        colors = mode_colors(spec, mode)
        pairs = [(bg, fg, minimum, f"{bg}/{fg}") for bg, fg, minimum in CONTRAST_PAIRS]
        for name, entry in ext.items():
            minimum = EXTENSION_USAGE_MIN.get(entry.get("usage", "text"))
            if minimum:
                pairs.append(("surface", f"ext.{name}", minimum, f"surface/ext.{name}"))
        for pair_id, bg, fg in component_boundary_pairs(spec):
            pairs.append((bg, fg, 3.0, pair_id))

        def value_of(ref):
            if ref.startswith("ext."):
                return color_value((ext.get(ref[4:]) or {}).get(mode))
            return color_value(colors.get(ref))

        for bg, fg, minimum, pair_id in pairs:
            bg_value, fg_value = value_of(bg), value_of(fg)
            if not (bg_value and fg_value):
                continue
            ratio = contrast_ratio(bg_value, fg_value)
            exc = accepted_exception(spec, mode, pair_id)
            status = "pass" if ratio >= minimum else ("accepted" if exc else "fail")
            results.append({
                "mode": mode, "pair": pair_id, "ratio": ratio, "min": minimum,
                "status": status, "reason": (exc or {}).get("reason", ""),
            })
    return results


# ---------------------------------------------------------------- validation


def validate(spec, allow_open_conflicts=False):
    """Return (errors, warnings). Errors block generation."""
    errors, warnings = [], []
    err, warn = errors.append, warnings.append

    if spec.get("specVersion") != SPEC_VERSION:
        err(f"specVersion must be {SPEC_VERSION}")
    if not spec.get("name"):
        err("name is required")

    policy = spec.get("policy") or {}
    variant = policy.get("schemeVariant", "fidelity")
    if variant not in SCHEME_VARIANTS:
        err(f"policy.schemeVariant '{variant}' is not one of {', '.join(SCHEME_VARIANTS)}")

    # --- colours
    colors = spec.get("colors") or {}
    for mode in colors:
        if mode not in ("light", "dark"):
            err(f"colors.{mode}: only 'light' and 'dark' are allowed")
    for mode in ("light", "dark"):
        for role, entry in mode_colors(spec, mode).items():
            where = f"colors.{mode}.{role}"
            if role in DEPRECATED_ROLES:
                err(f"{where}: deprecated Material role — map it to '{DEPRECATED_ROLES[role]}' "
                    "(or record a conflict if the values differ)")
                continue
            if role not in COLOR_ROLES:
                err(f"{where}: not a Material ColorScheme role — put it in extensionColors")
                continue
            _check_color_entry(entry, where, err, warn)

    if not color_value(mode_colors(spec, "light").get("primary")):
        err("colors.light.primary is required (it is also the default seed)")
    seed = spec.get("seed")
    if seed is not None:
        _check_color_entry(seed, "seed", err, warn)

    derive_dark = policy.get("deriveMissingDark", True)
    dark = mode_colors(spec, "dark")
    if not dark and not derive_dark:
        err("colors.dark is empty and policy.deriveMissingDark is false — provide dark colours or allow derivation")
    missing_light = [r for r in COLOR_ROLES if r not in mode_colors(spec, "light")]
    if missing_light:
        warn(f"{len(missing_light)} light role(s) not provided — derived from the seed: {', '.join(missing_light)}")
    if not dark:
        warn("no dark colours provided — the whole dark scheme is derived from the seed (review in the preview screen)")

    # --- extension colours
    ext = extension_colors(spec)
    for name in REQUIRED_EXTENSION_COLORS:
        if name not in ext:
            err(f"extensionColors.{name} is required by the app shell")
    for name, entry in ext.items():
        where = f"extensionColors.{name}"
        if not IDENT_RE.match(name):
            err(f"{where}: name must be lowerCamelCase")
        if name in COLOR_ROLES:
            err(f"{where}: '{name}' is a ColorScheme role — put it in colors instead")
        if not isinstance(entry, dict) or "light" not in entry:
            err(f"{where}: needs a 'light' entry")
            continue
        _check_color_entry(entry["light"], f"{where}.light", err, warn)
        if entry.get("dark"):
            _check_color_entry(entry["dark"], f"{where}.dark", err, warn)
        elif not derive_dark:
            err(f"{where}.dark missing and policy.deriveMissingDark is false")
        if entry.get("usage", "text") not in EXTENSION_USAGE_MIN:
            err(f"{where}.usage must be one of {', '.join(EXTENSION_USAGE_MIN)}")

    # --- typography
    typo = spec.get("typography") or {}
    roles = typo.get("roles") or {}
    for role, style in roles.items():
        if role not in TYPE_ROLES:
            err(f"typography.roles.{role}: not a Material TextTheme role — put it in typography.extras")
            continue
        _check_text_style(style, f"typography.roles.{role}", err, warn)
    for name, style in (typo.get("extras") or {}).items():
        if not IDENT_RE.match(name):
            err(f"typography.extras.{name}: name must be lowerCamelCase")
        if name in TYPE_ROLES:
            err(f"typography.extras.{name}: is a TextTheme role — put it in typography.roles")
        _check_text_style(style, f"typography.extras.{name}", err, warn)
    missing_type = [r for r in TYPE_ROLES if r not in roles]
    if missing_type:
        warn(f"{len(missing_type)} text role(s) not provided — Material 3 defaults used: {', '.join(missing_type)}")
    font = typo.get("fontFamily")
    if font is not None and not isinstance(font, dict):
        err("typography.fontFamily must be an object {value, source}")

    # --- dimensions
    for group, contract in (("spacing", CONTRACT_SPACING), ("radius", CONTRACT_RADIUS), ("sizes", CONTRACT_SIZES)):
        values = spec.get(group) or {}
        for key, entry in values.items():
            where = f"{group}.{key}"
            if not IDENT_RE.match(key):
                err(f"{where}: key must be a lowerCamelCase Dart identifier")
            v = entry.get("value") if isinstance(entry, dict) else None
            if not isinstance(v, (int, float)) or v < 0:
                err(f"{where}: value must be a non-negative number (dp)")
            if isinstance(entry, dict) and not entry.get("source"):
                warn(f"{where}: no source recorded")
        missing = [k for k in contract if k not in values]
        if missing:
            warn(f"{group}: shell defaults used for {', '.join(missing)}")

    # --- components
    extras = set((typo.get("extras") or {}).keys())
    for name, props in (spec.get("components") or {}).items():
        if name not in COMPONENTS:
            err(f"components.{name}: unknown component (supported: {', '.join(COMPONENTS)})")
            continue
        for prop, value in props.items():
            where = f"components.{name}.{prop}"
            if prop in ("source", "note"):
                continue
            if prop not in COMPONENTS[name]:
                err(f"{where}: unknown property (supported: {', '.join(sorted(COMPONENTS[name]))})")
            elif prop in COMPONENT_COLOR_PROPS:
                if value == "none" and prop in ("border", "errorBorder"):
                    pass  # borderless (filled) control
                elif not _is_color_ref(value, spec):
                    err(f"{where}: '{value}' must be a ColorScheme role or ext.<extensionColor> — "
                        "register raw hex values as colours first")
            elif prop in COMPONENT_TEXT_PROPS:
                if value not in TYPE_ROLES and value not in extras:
                    err(f"{where}: '{value}' must be a Material text role or a name in typography.extras")
            elif prop in COMPONENT_BOOL_PROPS:
                if not isinstance(value, bool):
                    err(f"{where}: must be true or false")
            elif not isinstance(value, (int, float)) or value < 0:
                err(f"{where}: must be a non-negative number")

    comps = spec.get("components") or {}
    if comps:
        for name in ("filledButton", "input", "card", "chip"):
            if "radius" not in (comps.get(name) or {}):
                warn(f"components.{name}.radius not set — default {COMPONENT_DEFAULTS[name]['radius']} "
                     "(set it explicitly if the design specifies shapes)")
    light = mode_colors(spec, "light")
    for main in ("primary", "secondary", "tertiary"):
        a, b = color_value(light.get(main)), color_value(light.get(main + "Container"))
        if a and b and a.upper() == b.upper():
            warn(f"colors.light.{main} equals {main}Container ({a}) — tonal distinction is lost; "
                 "confirm with the designer or let the container derive (remove it)")

    # --- conflicts
    for i, conflict in enumerate(spec.get("conflicts") or []):
        where = f"conflicts[{i}] ({conflict.get('target', '?')})"
        if not conflict.get("target") or not conflict.get("candidates"):
            err(f"{where}: needs 'target' and 'candidates'")
        status = conflict.get("status", "open")
        if status == "open":
            (warn if allow_open_conflicts else err)(
                f"{where}: unresolved — ask the user, then set status 'resolved' and 'resolution'"
                + (" (generating with the recommendation — output is PROVISIONAL)" if allow_open_conflicts else ""))
        elif status == "resolved":
            if "resolution" not in conflict:
                err(f"{where}: resolved conflicts need a 'resolution'")
            else:
                actual = _lookup(spec, conflict["target"])
                if actual is not None and _norm(actual) != _norm(conflict["resolution"]):
                    err(f"{where}: resolution {conflict['resolution']} does not match the value at "
                        f"{conflict['target']} ({actual})")
        else:
            err(f"{where}: status must be 'open' or 'resolved'")

    # --- contrast (provided values only)
    for r in contrast_results(spec):
        if r["status"] == "fail":
            warn(f"contrast {r['mode']} {r['pair']}: {r['ratio']:.2f}:1 < {r['min']}:1 — fix the colour or add "
                 "an acceptedContrastExceptions entry with a reason (the generated test will fail otherwise)")

    return errors, warnings


def _check_color_entry(entry, where, err, warn):
    if not isinstance(entry, dict):
        err(f"{where}: must be an object {{value, source}}")
        return
    value = entry.get("value")
    if not isinstance(value, str) or not HEX_RE.match(value):
        err(f"{where}: value '{value}' must be #RRGGBB or #AARRGGBB")
    if not entry.get("source"):
        warn(f"{where}: no source recorded")


def _check_text_style(style, where, err, warn):
    if not isinstance(style, dict):
        err(f"{where}: must be an object")
        return
    size = style.get("fontSize")
    if not isinstance(size, (int, float)) or size <= 0:
        err(f"{where}.fontSize must be a positive number (dp)")
    weight = style.get("fontWeight", 400)
    if weight not in range(100, 1000, 100):
        err(f"{where}.fontWeight must be 100–900 in steps of 100")
    line = style.get("lineHeight")
    if line is not None and (not isinstance(line, (int, float)) or line <= 0):
        err(f"{where}.lineHeight must be a positive number (dp, not a ratio)")
    ls = style.get("letterSpacing", 0)
    if not isinstance(ls, (int, float)):
        err(f"{where}.letterSpacing must be a number (dp — convert em by multiplying by fontSize)")
    for feature in style.get("fontFeatures") or []:
        if not re.match(r"^[a-z0-9]{4}$", str(feature)):
            err(f"{where}.fontFeatures: '{feature}' must be a 4-letter OpenType tag like 'tnum'")
    if not style.get("source"):
        warn(f"{where}: no source recorded")


def _is_color_ref(value, spec):
    if not isinstance(value, str):
        return False
    if value.startswith("ext."):
        return value[4:] in extension_colors(spec)
    return value in COLOR_ROLES


def _lookup(spec, target):
    node = spec
    for part in target.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    if isinstance(node, dict):
        return node.get("value")
    return node


def _norm(v):
    return v.upper() if isinstance(v, str) else v
