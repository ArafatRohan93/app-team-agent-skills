#!/usr/bin/env python3
"""Usage evidence from an HTML design: a Claude Design page export (bundled or
rendered), an HTML/CSS mock-up, a Tailwind or React prototype. Any page whose
styles carry no token names, or only some.

The page is read in one of two ways:
  render  (preferred) a headless Chrome / Chromium / Edge / Brave loads the page,
          runs its scripts, and every visible element's *computed* style is read.
          This sees class rules, Tailwind, CSS variables, external stylesheets
          and DOM built by JavaScript.
  static  (fallback, no browser) the HTML as written: inline styles plus
          `<style>` and local stylesheet rules with simple selectors (tag, .class,
          #id, [attr], descendant), var() resolved, inherited colour and font.

It doesn't guess roles. It records how each value is *used* (button fill, field
fill, card, screen background, text, icon, border…), on which screens, with
sample text, so the agent maps by meaning (references/material-mapping.md).
Also collected, when present:
  - CSS custom properties, light and dark (`prefers-color-scheme`, `.dark`, `[data-theme=dark]`)
  - interaction-state rules (:hover, :focus, :active, :disabled). Static read only
  - legend cards that name roles next to a preview ("Colors: primary (fill), …")
  - colours outside the screens (swatches, style-guide rows) with their labels
  - @font-face families and weights, shadows, gradients

Screens are device frames: phone-sized boxes (320–480 wide, tall or rounded) and
rounded tablet frames. The bezel, the status bar (a time such as "9:41" at the
top) and the home indicator are excluded. A page without frames is read as one
screen.
"""

import bisect
import collections
import json
import os
import re
import shutil
import subprocess
import tempfile
from html.parser import HTMLParser
from pathlib import Path

COLOR = re.compile(r"#[0-9a-fA-F]{8}\b|#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b|(?:rgba?|hsla?|oklch)\([^)]*\)"
                   r"|\b(?:white|black|currentcolor)\b", re.I)
NAMED = {"white": "#FFFFFF", "black": "#000000"}
LENGTH = re.compile(r"(-?\d*\.?\d+)(px|rem|em)\b")
VAR = re.compile(r"var\(\s*(--[\w-]+)\s*(?:,\s*((?:[^()]|\([^()]*\))*))?\)")
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr",
        "use", "path", "circle", "rect", "ellipse", "line", "polyline", "polygon", "stop"}
SHAPES = {"path", "circle", "rect", "ellipse", "line", "polyline", "polygon", "use"}
SKIP_CONTENT = {"script", "style", "template", "noscript", "title", "head"}
FIELDS = {"input", "textarea", "select"}
INHERITED = ("color", "font-size", "font-weight", "font-family", "line-height", "letter-spacing", "fill", "stroke")
SYSTEM_FONTS = {"sans-serif", "serif", "monospace", "system-ui", "-apple-system", "blinkmacsystemfont",
                "ui-monospace", "ui-sans-serif", "ui-serif", "menlo", "segoe ui", "roboto", "helvetica",
                "helvetica neue", "arial", "inherit", "initial", "apple color emoji", "segoe ui emoji",
                "segoe ui symbol", "noto color emoji"}
MONO = re.compile(r"mono|courier|consolas|menlo", re.I)
TIME = re.compile(r"^\d{1,2}:\d{2}(?:\s?[AP]M)?$", re.I)
ROLE_WORD = re.compile(r"\b(?:on-)?(?:primary|secondary|tertiary|surface|background|outline|border|container|"
                       r"error|accent|brand|ink|neutral|success|warning|info|muted)\b", re.I)
LEGEND_PAIR = re.compile(r"\b[a-z][\w-]*\s*\((?:bg|fill|background|text|label|icon|border|stroke|divider|dot|"
                         r"name|title|value|badge|base|[^)]{0,24}\b(?:bg|text|icon|border|fill))\)", re.I)
DARK = re.compile(r"prefers-color-scheme\s*:\s*dark|\.dark\b|\[data-[\w-]*=['\"]?dark|\bdark-(?:mode|theme)\b|"
                  r"\.theme-dark\b", re.I)
STATES = {"hover", "focus", "focus-visible", "focus-within", "active", "disabled", "checked", "selected",
          "invalid", "placeholder"}


def unpack(text):
    """Return the page HTML: the `__bundler/template` of a Claude Design bundle, else the text."""
    m = re.search(r'<script type="__bundler/template">\s*(.*?)\s*</script>', text, re.S)
    if m:
        try:
            return json.loads(m.group(1)), "claude-design-bundle"
        except ValueError:
            pass
    return text, "html"


def parse_style(value):
    out = {}
    for part in re.split(r";(?![^(]*\))", value or ""):
        k, _, v = part.partition(":")
        if k.strip() and v.strip():
            out[k.strip().lower()] = re.sub(r"\s*!important\s*$", "", v.strip())
    return out


def px(value):
    """First length in px (rem/em × 16), or None."""
    m = LENGTH.search(value or "")
    if not m:
        return None
    n = float(m.group(1))
    return n * 16 if m.group(2) in ("rem", "em") else n


def lengths(value):
    return [float(n) * (16 if u in ("rem", "em") else 1) for n, u in LENGTH.findall(value or "")]


def expand_font(style):
    """Expand the `font` shorthand into longhands (explicit longhands win)."""
    f = style.get("font")
    if not f:
        return style
    m = re.match(r"^\s*(?:(?:italic|oblique|small-caps|normal)\s+)*(?:(\d{3}|bold|bolder|lighter)\s+)?"
                 r"(\d*\.?\d+(?:px|rem|em))(?:\s*/\s*([\d.]+(?:px|rem|em|%)?))?\s+(.+)$", f, re.I)
    if not m:
        return style
    out = dict(style)
    for k, v in (("font-weight", m.group(1) or "400"), ("font-size", m.group(2)),
                 ("line-height", m.group(3) or "normal"), ("font-family", m.group(4))):
        out.setdefault(k, v)
    return out


def font_weight(value):
    v = (value or "").strip().lower()
    return {"bold": 700, "bolder": 700, "normal": 400, "lighter": 300}.get(v, int(float(v)) if re.match(r"^\d+(\.\d+)?$", v) else 400)


def font_family(value):
    names = [n.strip().strip("'\"") for n in (value or "").split(",")]
    return next((n for n in names if n and n.lower() not in SYSTEM_FONTS), None)


def radius_px(style, w=None, h=None):
    v = style.get("border-radius") or style.get("border-top-left-radius")
    if not v:
        return 0
    if "%" in v.split()[0]:
        return 9999 if float(re.sub(r"[^\d.]", "", v.split()[0]) or 0) >= 50 else 0
    r = px(v) or 0
    if r and w and h and r >= min(w, h) / 2 - 0.5:
        return 9999
    return r


def resolve_vars(value, props, depth=0):
    if "var(" not in value or depth > 8:
        return value

    def sub(m):
        v = props.get(m.group(1).lower())
        return v if v is not None else (m.group(2) or "").strip()
    return resolve_vars(VAR.sub(sub, value), props, depth + 1)


# ------------------------------------------------------------------ static CSS


def css_blocks(css):
    """[(prelude, body, context)] for every rule; @media/@supports/@layer bodies are recursed into."""
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    out = []

    def scan(text, ctx):
        depth, start, prelude, body_start = 0, 0, "", 0
        for i, ch in enumerate(text):
            if ch == "{":
                if depth == 0:
                    prelude, body_start = text[start:i].strip(), i + 1
                depth += 1
            elif ch == "}" and depth:
                depth -= 1
                if depth == 0:
                    body = text[body_start:i]
                    if re.match(r"@(media|supports|layer|container)\b", prelude):
                        scan(body, ctx + (prelude,))
                    else:
                        out.append((prelude, body, ctx))
                    start = i + 1
            elif ch == ";" and depth == 0:
                start = i + 1
    scan(css, ())
    return out


SIMPLE = re.compile(r"^(\*|[a-zA-Z][\w-]*)?((?:[.#][\w-]+|\[[^\]]+\])*)((?::{1,2}[\w-]+(?:\([^)]*\))?)*)$")
ATTR = re.compile(r"\[\s*([\w-]+)\s*(?:([~|^$*]?=)\s*[\"']?([^\"'\]]*)[\"']?)?\s*\]")


def parse_selector(sel):
    """'.card > h3.title:hover' → (chain, state, specificity), or None when the static read can't evaluate it."""
    sel = sel.strip()
    if not sel or re.search(r"[+~](?![^\[]*\])", sel):
        return None
    parts = [p for p in re.split(r"\s*>\s*|\s+", sel) if p]
    chain, state = [], None
    for i, p in enumerate(parts):
        m = SIMPLE.match(p)
        if not m:
            return None
        tag, quals, pseudos = m.groups()
        ps = [x for x in re.findall(r"::?([\w-]+)", pseudos or "") if x != "root"]
        if ":root" in (pseudos or ""):
            tag = "html"
        if ps:
            if i != len(parts) - 1 or any(x not in STATES for x in ps):
                return None
            state = ps[0]
        chain.append((None if tag in (None, "*") else tag.lower(), re.findall(r"\.([\w-]+)", quals),
                      re.findall(r"#([\w-]+)", quals), ATTR.findall(quals)))
    spec = (sum(len(c[2]) for c in chain), sum(len(c[1]) + len(c[3]) for c in chain) + bool(state),
            sum(1 for c in chain if c[0]))
    return chain, state, spec


def _match_compound(c, tag, a):
    t, classes, ids, attrs = c
    if t and t != tag:
        return False
    if classes and not set(classes) <= set((a.get("class") or "").split()):
        return False
    if any(a.get("id") != x for x in ids):
        return False
    for name, op, val in attrs:
        if name not in a:
            return False
        v = a[name] or ""
        if (op == "=" and v != val) or (op == "~=" and val not in v.split()) or (op == "*=" and val not in v) \
                or (op == "^=" and not v.startswith(val)) or (op == "$=" and not v.endswith(val)):
            return False
    return True


def _match_chain(chain, tag, a, ancestors):
    if not _match_compound(chain[-1], tag, a):
        return False
    i = len(ancestors) - 1
    for c in reversed(chain[:-1]):
        while i >= 0 and not _match_compound(c, *ancestors[i]):
            i -= 1
        if i < 0:
            return False
        i -= 1
    return True


def _rule_key(c):
    return ("#" + c[2][0]) if c[2] else ("." + c[1][0]) if c[1] else (c[0] or "*")


class Stylesheet:
    """Custom properties (light / dark / scoped), font faces, state rules and, for the static read, element rules."""

    def __init__(self, css, element_rules=True):
        self.index, self.states = collections.defaultdict(list), []
        self.light, self.dark, self.scoped = {}, {}, {}
        self.faces = collections.defaultdict(set)
        self.skipped = 0
        order = 0
        for prelude, body, ctx in css_blocks(css):
            if prelude.lower().startswith("@font-face"):
                d = parse_style(body)
                fam = (d.get("font-family") or "").strip("'\" ")
                if fam:
                    self.faces[fam].add(font_weight(d.get("font-weight", "400").split()[0]))
                continue
            if prelude.startswith("@"):
                continue
            decls = parse_style(body)
            media = " ".join(ctx)
            dark = bool(DARK.search(media) or DARK.search(prelude))
            sels = [s.strip() for s in re.split(r",(?![^(\[]*[)\]])", prelude) if s.strip()]
            rootish = any(re.match(r"^(:root|html|body|\*)(?![\w-])", s) for s in sels)
            for k, v in decls.items():
                if k.startswith("--"):
                    (self.dark if dark else self.light if rootish else self.scoped)[k] = v
            if dark or not element_rules or re.search(r"\bprint\b", media) \
                    or any(int(x) > 480 for x in re.findall(r"min-width\s*:\s*(\d+)", media)):
                continue  # element styling: the light, phone-width rendering only
            el = {k: v for k, v in decls.items() if not k.startswith("--")}
            if not el:
                continue
            for s in sels:
                parsed = parse_selector(s)
                if not parsed:
                    self.skipped += 1
                    continue
                chain, state, spec = parsed
                order += 1
                if state:
                    self.states.append((s, state, el))
                else:
                    self.index[_rule_key(chain[-1])].append((spec, order, chain, el))
        self.vars = {**self.scoped, **self.light}

    def match(self, tag, a, ancestors):
        keys = [tag, "*"] + ["." + c for c in (a.get("class") or "").split()] + (["#" + a["id"]] if a.get("id") else [])
        hits = [r for k in dict.fromkeys(keys) for r in self.index.get(k, ()) if _match_chain(r[2], tag, a, ancestors)]
        style = {}
        for _, _, _, el in sorted(hits, key=lambda r: (r[0], r[1])):
            style.update(el)
        return style


# ------------------------------------------------------------------ DOM walk


class _Node:
    __slots__ = ("tag", "attrs", "style", "inh", "id", "end", "parent", "children", "frame", "root", "direct",
                 "text", "chrome", "hidden", "skip", "in_svg", "rect", "has_input")

    def __init__(self, tag, attrs, style, nid, parent):
        self.tag, self.attrs, self.style, self.id, self.parent = tag, attrs, style, nid, parent
        self.end, self.children, self.direct, self.text = nid, [], [], []
        self.inh, self.frame, self.root, self.chrome = {}, None, False, False
        self.hidden = self.skip = self.in_svg = self.has_input = False
        self.rect = None

    def size(self):
        return px(self.style.get("width")), px(self.style.get("height")) or px(self.style.get("min-height"))


class _Walker(HTMLParser):
    def __init__(self, sheet, rendered, whole_page):
        super().__init__(convert_charrefs=True)
        self.sheet, self.rendered, self.whole_page = sheet, rendered, whole_page
        self.stack, self.nodes, self.texts = [], [], []
        self.skip_depth = 0
        self.last_label = ""
        self.frames = {}  # label → root node

    @staticmethod
    def _is_frame(style):
        w, h = px(style.get("width")), px(style.get("height")) or px(style.get("min-height")) or 0
        r = radius_px(style)
        visible = any((k.startswith(("background", "border")) and "radius" not in k or k == "box-shadow")
                      and not re.search(r"\b(none|transparent)\b|^0(px)?$", v) for k, v in style.items())
        if not w or not visible:
            return False  # a plain wrapper (label + frame) is not the device
        return (320 <= w <= 480 and (h >= 560 or (not h and 32 <= r < 200))) or (600 <= w <= 1400 and h >= 700 and r >= 16)

    def handle_starttag(self, tag, attrs):
        if tag in SKIP_CONTENT:
            self.skip_depth += 1
            return
        if self.skip_depth:
            return
        a = {k: (v if v is not None else "") for k, v in attrs}
        parent = self.stack[-1] if self.stack else None
        in_svg = tag == "svg" or bool(parent and parent.in_svg)
        if self.rendered:
            style = expand_font(parse_style(a.get("data-x-style")))
            hide = a.get("data-x-hidden")
            hidden, skip = bool(parent and parent.hidden) or hide == "none", hide == "empty"
        else:
            style = self.sheet.match(tag, a, [(n.tag, n.attrs) for n in self.stack])
            style.update(parse_style(a.get("style")))
            if in_svg:
                for attr in ("fill", "stroke"):
                    if a.get(attr) and attr not in style:
                        style[attr] = a[attr]
                for attr in ("width", "height"):
                    if tag == "svg" and re.match(r"^\d+(\.\d+)?$", a.get(attr, "")) and attr not in style:
                        style[attr] = a[attr] + "px"
            style = {k: resolve_vars(v, self.sheet.vars) for k, v in expand_font(style).items()}
            hidden = bool(parent and parent.hidden) or style.get("display") == "none" \
                or style.get("visibility") == "hidden"
            skip = False
        node = _Node(tag, a, style, len(self.nodes), parent)
        node.in_svg, node.hidden, node.skip = in_svg, hidden, skip
        if self.rendered:
            node.inh = {k: style[k] for k in INHERITED if k in style}
            if a.get("data-x-rect"):
                node.rect = tuple(float(x) for x in a["data-x-rect"].split())
        else:
            node.inh = dict(parent.inh) if parent else {}
            node.inh.update({k: style[k] for k in INHERITED if k in style})
            cur = node.inh.get("color")
            for k in ("fill", "stroke"):
                if cur and node.inh.get(k, "").lower() == "currentcolor":
                    node.inh[k] = cur
        node.frame = parent.frame if parent else None
        if node.frame is None and not hidden and not self.whole_page and self._is_frame(style):
            label = self.last_label or f"screen {len(self.frames) + 1}"
            n = 2
            while label in self.frames:
                label, n = f"{label.rsplit(' #', 1)[0]} #{n}", n + 1
            node.frame, node.root = label, True
            self.frames[label] = node
            bw = max([px(v) or 0 for k, v in style.items() if k.startswith("border") and "radius" not in k] or [0])
            node.style = {k: v for k, v in style.items()
                          if k not in ("box-shadow", "outline") and not (bw >= 6 and k.startswith("border")
                                                                          and "radius" not in k)}
            node.style["border-radius"] = style.get("border-radius", "0")
        if tag in FIELDS:
            txt = a.get("data-x-text") if self.rendered else (a.get("value") or a.get("placeholder"))
            if txt:
                node.direct.append(txt)
                node.text.append(txt)
            for n in self.stack:
                n.has_input = True
        if parent:
            parent.children.append(node)
        self.nodes.append(node)
        if tag not in VOID:
            self.stack.append(node)

    def handle_endtag(self, tag):
        if tag in SKIP_CONTENT:
            self.skip_depth = max(0, self.skip_depth - 1)
            return
        if self.skip_depth or not any(n.tag == tag for n in self.stack):
            return  # stray or void close tag (e.g. </use>): leave the stack alone
        while self.stack:
            node = self.stack.pop()
            node.end = len(self.nodes) - 1
            if node.tag == tag:
                break

    def handle_data(self, data):
        if self.skip_depth or not self.stack:
            return
        text = " ".join(data.split())
        top = self.stack[-1]
        if not text or top.hidden:
            return
        top.direct.append(text)
        for n in self.stack:
            if len(" ".join(n.text)) < 60:
                n.text.append(text)
        if top.frame is None and len(text) < 70:
            self.last_label = text
        self.texts.append((top.id, text))

    def finish(self):
        self.close()
        while self.stack:
            self.stack.pop().end = len(self.nodes) - 1


# ------------------------------------------------------------------ classification


def node_colours(n, to_hex):
    """[(usage, value)] painted by one node: background, gradient, border, outline, placeholder, text, icon."""
    s, out = n.style, []
    cur = n.inh.get("color")

    def hexes(v):
        for c in COLOR.findall(v):
            c = cur if c.lower() == "currentcolor" else NAMED.get(c.lower(), c)
            h = to_hex(c) if c else None
            if h and not (len(h) == 9 and h[1:3] == "00"):
                yield h
    for prop, val in s.items():
        if prop in ("background", "background-color", "background-image"):
            if "gradient" in val:
                out.append(("gradient", " → ".join(hexes(val))))
            else:
                out += [("background", h) for h in hexes(re.sub(r"url\([^)]*\)", "", val))]
        elif prop.startswith("border") and not any(x in prop for x in ("radius", "spacing", "collapse", "width",
                                                                         "style", "image")):
            if not re.search(r"\b(none|hidden)\b|^0(px)?\b", val):
                out += [("border", h) for h in hexes(val)]
        elif prop == "outline" and not re.search(r"\bnone\b|^0(px)?\b", val):
            out += [("outline", h) for h in hexes(val)]
        elif prop == "placeholder-color":
            out += [("placeholder", h) for h in hexes(val)]
    if n.in_svg:
        if n.tag == "use":  # the symbol draws with currentColor
            out += [("icon", h) for h in hexes(cur or "")]
        elif n.tag in SHAPES or n.direct:
            for k in ("fill", "stroke"):
                v = n.inh.get(k, "")
                if v and v.lower() != "none" and "url(" not in v:
                    out += [("icon", h) for h in hexes(v)]
    elif n.direct and cur and (n.tag not in FIELDS or n.attrs.get("value")
                               or ("data-x-style" in n.attrs and "color" in s)):  # a field's text, not its placeholder
        out += [("text", h) for h in hexes(cur)]
    return out


def classify(n, frame):
    """What kind of element is this? Groups colour usage in the evidence."""
    s = n.style
    w, h = n.size()
    r = radius_px(s, w, h)
    has_bg = any(k.startswith("background") and not re.search(r"\b(none|transparent)\b", v) for k, v in s.items())
    bordered = any(k.startswith("border") and "radius" not in k and not re.search(r"\b(none|hidden)\b|^0(px)?\b", v)
                   for k, v in s.items())
    fw, fh = frame.size() if frame is not None else (None, None)
    if n.in_svg:
        return "icon"
    if n.tag in FIELDS:
        return "field"
    if n.root or n.tag in ("html", "body") or (fw and fh and w and h and w >= 0.9 * fw and h >= 0.6 * fh):
        return "screen"
    if r >= 999 and w and h and abs(w - h) < 1.5:
        return "dot/avatar"
    if r >= 999 and h and (has_bg or bordered):
        return "button" if h >= 40 else "pill/chip"
    if h and h <= 2 and w and w > 24 and has_bg:
        return "divider"
    if fw and w and w >= 0.9 * fw and r < 4 and (has_bg or bordered) and h:
        if n.rect and frame.rect:
            top, bottom = n.rect[1] - frame.rect[1], frame.rect[1] + frame.rect[3] - (n.rect[1] + n.rect[3])
        else:
            top = bottom = None
        if 44 <= h <= 72 and (top is None and (s.get("flex") == "none" or s.get("flex-shrink") == "0")
                              or top is not None and top <= 110):
            return "app bar"
        if 48 <= h <= 100 and (bottom is not None and bottom <= 40
                               or bottom is None and re.match(r"^0(px)?$", s.get("bottom", "x"))):
            return "bottom bar"
    buttonish = n.tag == "button" or n.attrs.get("role") in ("button", "tab") or s.get("cursor") == "pointer"
    if (has_bg or bordered) and h and 32 <= h <= 64 and r < 999:
        if n.has_input:
            return "field"
        if buttonish or (n.tag == "a" and has_bg):
            return "button"
        if r >= 4:
            centred = s.get("justify-content") == "center" or s.get("text-align") == "center"
            return "button" if centred else "field"
    if buttonish and (has_bg or bordered):
        return "button"
    if r >= 4 and (has_bg or bordered):
        return "card/panel"
    if r >= 999:
        return "dot/avatar"
    return "element"


# ------------------------------------------------------------------ collection


def _assign_page(w):
    """No device frames: the page is the one screen, measured by its <html>/<body> box. Returns frames_found."""
    if w.frames:
        return True
    for n in w.nodes:
        n.frame = "page"
    box = next((n for n in w.nodes if n.tag in ("html", "body") and n.size()[0]), None)
    if box is not None:
        w.frames["page"] = box
    return False


def _mark_chrome(w):
    """Status bar (a time among a frame's first texts), home indicator and dynamic island."""
    firsts = collections.defaultdict(list)
    for nid, text in w.texts:
        n = w.nodes[nid]
        if n.frame and len(firsts[n.frame]) < 3:
            firsts[n.frame].append((n, text))
    for items in firsts.values():
        for n, text in items:
            if not TIME.match(text):
                continue
            cur = n
            while cur.parent and not cur.parent.root and cur.parent.frame == n.frame \
                    and (cur.parent.size()[1] or 999) <= 60:
                cur = cur.parent
            for m in w.nodes[cur.id:cur.end + 1]:
                m.chrome = True
    for n in w.nodes:
        if n.frame and not n.root:
            wd, h = n.size()
            if wd and h and ((90 <= wd <= 160 and h <= 6) or (90 <= wd <= 140 and 25 <= h <= 40
                             and radius_px(n.style, wd, h) >= 999
                             and (n.style.get("background") or n.style.get("background-color", "")).lower()
                             in ("#000", "#000000", "black", "rgb(0, 0, 0)"))):
                for m in w.nodes[n.id:n.end + 1]:
                    m.chrome = True


def _subtree_text(w, n, ids):
    lo, hi = bisect.bisect_left(ids, n.id), bisect.bisect_right(ids, n.end)
    return " ".join(t for _, t in w.texts[lo:hi])


def _find_legends(w, to_hex):
    """Cards outside the screens that pair a preview with role names ("Colors: primary (fill), on-primary…")."""
    ids = [nid for nid, _ in w.texts]
    legend_nodes = []
    for n in w.nodes:
        if n.frame is not None or n.hidden or n.in_svg:
            continue
        fam = n.inh.get("font-family", "")
        top_of_mono = MONO.search(fam) and not (n.parent and MONO.search(n.parent.inh.get("font-family", "")))
        text = _subtree_text(w, n, ids) if (top_of_mono or n.direct) else ""
        if not text or len(text) > 600:
            continue
        score = len(ROLE_WORD.findall(text)) + len(LEGEND_PAIR.findall(text))
        if score >= 2 and (top_of_mono or re.match(r"^\s*(colou?rs?|tokens?|roles?)\s*:", text, re.I)):
            if not any(p.id <= n.id <= p.end for p in legend_nodes):
                legend_nodes.append(n)
    legends = []
    for L in legend_nodes:
        card, preview = L.parent, None
        while card is not None and card.frame is None:
            if sum(1 for x in legend_nodes if card.id <= x.id <= card.end) > 1:
                card = None
                break
            scored = [(sum(1 for m in w.nodes[c.id:c.end + 1] for u, _ in node_colours(m, to_hex) if u != "text"), c)
                      for c in card.children if not c.id <= L.id <= c.end]
            scored = [x for x in scored if x[0]]
            if scored:
                preview = max(scored, key=lambda x: x[0])[1]
                break
            card = card.parent
        if card is None or preview is None:
            continue
        inner = w.nodes[preview.id + 1:preview.end + 1]
        canvas = any(u in ("background", "gradient") for m in inner for u, _ in node_colours(m, to_hex))  # preview box holds the sample
        cols = []
        for m in (inner if canvas else [preview] + inner):
            for usage, h in node_colours(m, to_hex):
                cols.append((usage, h))
        title = next((t for nid, t in w.texts if card.id <= nid <= card.end
                      and not preview.id <= nid <= preview.end and not L.id <= nid <= L.end), None)
        legends.append({"title": title or "(untitled)", "colors": list(dict.fromkeys(cols)),
                        "legend": _subtree_text(w, L, ids)})
    return legends


def collect(html, to_hex, rendered=False, whole_page=False, extra_css=""):
    if rendered:
        m = re.search(r'<style id="__x_css">(.*?)</style>', html, re.S)
        sheet = Stylesheet(m.group(1) if m else "", element_rules=False)
    else:
        css = "\n".join(re.findall(r"<style[^>]*>(.*?)</style>", html, re.S | re.I)) + "\n" + extra_css
        sheet = Stylesheet(css)
    w = _Walker(sheet, rendered, whole_page)
    w.feed(html)
    w.finish()
    frames_found = _assign_page(w)
    _mark_chrome(w)

    colours = collections.defaultdict(lambda: {"count": 0, "by": collections.Counter(), "screens": set(),
                                               "samples": []})
    gradients, shadows = collections.Counter(), collections.Counter()
    type_scale = collections.defaultdict(lambda: {"count": 0, "samples": [], "kinds": collections.Counter(),
                                                  "colours": collections.Counter(), "lineHeights": collections.Counter(),
                                                  "letterSpacing": collections.Counter()})
    radii, heights, families = collections.Counter(), collections.defaultdict(collections.Counter), collections.Counter()
    spacing = collections.Counter()
    annotations = collections.defaultdict(collections.Counter)
    frame_ids = [f.id for f in w.frames.values()]

    for n in w.nodes:
        if n.hidden or n.skip or n.chrome:
            continue
        if n.frame is None:
            if frames_found and not any(n.id <= f <= n.end for f in frame_ids):
                label = " ".join(n.text)[:50] or (" ".join(n.parent.text)[:50] if n.parent else "")
                for usage, h in node_colours(n, to_hex):
                    if usage in ("background", "border") and label:
                        annotations[h][label] += 1
            continue
        frame = w.frames.get(n.frame)
        kind = classify(n, frame)
        sample = " ".join(n.text)[:40]
        for usage, h in node_colours(n, to_hex):
            if usage == "gradient":
                if h:
                    gradients[h] += 1
                continue
            key = usage if usage in ("text", "icon") and kind in ("element", "icon") else f"{usage} · {kind}"
            e = colours[h]
            e["count"] += 1
            e["by"][key] += 1
            e["screens"].add(n.frame)
            if sample and len(e["samples"]) < 4 and sample not in e["samples"]:
                e["samples"].append(sample)
        if n.style.get("box-shadow") and n.style["box-shadow"] != "none":
            shadows[(n.style["box-shadow"], kind)] += 1
        if n.direct and not n.in_svg:
            size = px(n.inh.get("font-size"))
            if size:
                t = type_scale[(size, font_weight(n.inh.get("font-weight")))]
                t["count"] += 1
                t["kinds"][kind] += 1
                if n.inh.get("line-height"):
                    t["lineHeights"][n.inh["line-height"]] += 1
                if n.inh.get("letter-spacing") not in (None, "normal", "0", "0px"):
                    t["letterSpacing"][n.inh["letter-spacing"]] += 1
                txt = " ".join(n.direct)[:32]
                if len(t["samples"]) < 3 and txt not in t["samples"]:
                    t["samples"].append(txt)
                for usage, h in node_colours(n, to_hex):
                    if usage == "text":
                        t["colours"][h] += 1
                fam = font_family(n.inh.get("font-family"))
                if fam:
                    families[fam] += 1
        wd, hg = n.size()
        r = radius_px(n.style, wd, hg)
        if r and not n.root:
            radii[(r, kind)] += 1
        vals = set()
        for prop in ("padding", "padding-top", "padding-right", "padding-bottom", "padding-left", "gap", "row-gap",
                     "column-gap", "margin-top", "margin-bottom"):
            vals.update(v for v in lengths(n.style.get(prop, "")) if 0 < v <= 64)
        for v in vals:
            spacing[v] += 1
        if hg and kind in ("button", "field", "pill/chip", "app bar", "bottom bar"):
            heights[kind][hg] += 1

    props = {k: resolve_vars(v, sheet.vars) for k, v in sheet.light.items() if not k.startswith("--tw-")}
    dark = {k: resolve_vars(v, {**sheet.vars, **sheet.dark}) for k, v in sheet.dark.items()}
    var_names = collections.defaultdict(list)
    for k, v in props.items():
        h = to_hex(v.strip()) if COLOR.fullmatch(v.strip() or "-") else None
        if h:
            var_names[h].append(k)
    for h, e in colours.items():
        e["vars"] = var_names.get(h, [])
    states = []
    for sel, state, decls in sheet.states:
        cols = {k: v for k, v in ((k, resolve_vars(v, sheet.vars)) for k, v in decls.items()) if COLOR.search(v)}
        if cols:
            states.append((sel, state, cols))
    return {
        "screens": list(w.frames) or ["page"], "framesFound": frames_found, "colours": colours, "spacing": spacing,
        "gradients": gradients, "shadows": shadows, "type": type_scale, "radii": radii, "heights": heights,
        "families": families, "fontFaces": sheet.faces, "legends": _find_legends(w, to_hex) if frames_found else [],
        "customProps": props, "customPropsDark": dark, "states": states, "annotations": annotations,
        "skippedSelectors": sheet.skipped,
    }


def _walk(html, whole_page):
    m = re.search(r'<style id="__x_css">(.*?)</style>', html, re.S)
    w = _Walker(Stylesheet(m.group(1) if m else "", element_rules=False), True, whole_page)
    w.feed(html)
    w.finish()
    return w


def pair_dark(ev, light_dom, dark_dom, to_hex, whole_page):
    """Add each colour's dark-mode counterparts, matching elements one to one. False if the DOMs differ."""
    lw, dw = _walk(light_dom, whole_page), _walk(dark_dom, whole_page)
    if [n.tag for n in lw.nodes] != [n.tag for n in dw.nodes]:
        return False
    _assign_page(lw)
    _mark_chrome(lw)
    for h in ev["colours"].values():
        h["dark"] = collections.Counter()
    for ln, dn in zip(lw.nodes, dw.nodes):
        if ln.hidden or ln.skip or ln.chrome or ln.frame is None:
            continue  # count only what the evidence counts
        lc, dc = node_colours(ln, to_hex), node_colours(dn, to_hex)
        for (lu, lh), (du, dh) in zip(lc, dc):
            if lu == du and lu != "gradient" and lh in ev["colours"]:
                ev["colours"][lh]["dark"][dh] += 1
    return True


# ------------------------------------------------------------------ rendering

FLATTEN_JS = r"""
(function () {
  var done = false;
  function n(v) { return parseFloat(v) || 0; }
  function clear(c) { return !c || c === 'transparent' || /rgba\(.*,\s*0\)$/.test(c) || /\/\s*0\)$/.test(c); }
  function run() {
    if (done) return; done = true;
    var SKIP = {script: 1, style: 1, template: 1, noscript: 1, link: 1, meta: 1, head: 1, title: 1, base: 1};
    var SHAPES = {path: 1, circle: 1, rect: 1, ellipse: 1, line: 1, polyline: 1, polygon: 1, use: 1, text: 1};
    var all = document.querySelectorAll('*');
    for (var i = 0; i < all.length; i++) {
      var el = all[i], tag = el.tagName.toLowerCase();
      if (SKIP[tag] || (el.closest && el.closest('head'))) continue;
      var cs = getComputedStyle(el), r = el.getBoundingClientRect(), s = [];
      if (cs.display === 'none' || cs.visibility === 'hidden' || n(cs.opacity) === 0) { el.setAttribute('data-x-hidden', 'none'); continue; }
      if (r.width === 0 && r.height === 0) { el.setAttribute('data-x-hidden', 'empty'); continue; }
      el.setAttribute('data-x-rect', [Math.round(r.left + scrollX), Math.round(r.top + scrollY), Math.round(r.width), Math.round(r.height)].join(' '));
      s.push('width:' + Math.round(r.width) + 'px', 'height:' + Math.round(r.height) + 'px');
      if (!clear(cs.backgroundColor)) s.push('background-color:' + cs.backgroundColor);
      if (cs.backgroundImage.indexOf('gradient') >= 0) s.push('background-image:' + cs.backgroundImage);
      var direct = false;
      for (var c = el.firstChild; c; c = c.nextSibling) if (c.nodeType === 3 && c.textContent.trim()) { direct = true; break; }
      var field = tag === 'input' || tag === 'textarea' || tag === 'select';
      if (field) {
        var ph = el.getAttribute('placeholder') || '';
        el.setAttribute('data-x-text', el.value || ph);
        if (!el.value && ph) { try { s.push('placeholder-color:' + getComputedStyle(el, '::placeholder').color); } catch (e) {} }
      }
      if (direct || (field && el.value)) {
        s.push('color:' + cs.color, 'font-size:' + cs.fontSize, 'font-weight:' + cs.fontWeight,
               'line-height:' + cs.lineHeight, 'font-family:' + cs.fontFamily);
        if (cs.letterSpacing !== 'normal') s.push('letter-spacing:' + cs.letterSpacing);
      } else if (field) {
        s.push('font-size:' + cs.fontSize, 'font-weight:' + cs.fontWeight, 'font-family:' + cs.fontFamily);
      }
      if (tag === 'use') s.push('color:' + cs.color);
      else if (el instanceof SVGElement && SHAPES[tag]) {
        if (cs.fill && cs.fill !== 'none' && cs.fill.indexOf('url') < 0 && n(cs.fillOpacity) > 0) s.push('fill:' + cs.fill);
        if (cs.stroke && cs.stroke !== 'none' && cs.stroke.indexOf('url') < 0 && n(cs.strokeWidth) > 0) s.push('stroke:' + cs.stroke);
      }
      var sides = ['top', 'right', 'bottom', 'left'], b = [];
      for (var k = 0; k < 4; k++) {
        var sd = sides[k], bw = n(cs.getPropertyValue('border-' + sd + '-width')), st = cs.getPropertyValue('border-' + sd + '-style'),
            col = cs.getPropertyValue('border-' + sd + '-color');
        if (bw > 0 && st !== 'none' && st !== 'hidden' && !clear(col)) b.push([sd, bw, col]);
      }
      if (b.length === 4 && b.every(function (x) { return x[1] === b[0][1] && x[2] === b[0][2]; })) s.push('border:' + b[0][1] + 'px solid ' + b[0][2]);
      else b.forEach(function (x) { s.push('border-' + x[0] + ':' + x[1] + 'px solid ' + x[2]); });
      if (n(cs.outlineWidth) > 0 && cs.outlineStyle !== 'none' && !clear(cs.outlineColor)) s.push('outline:' + n(cs.outlineWidth) + 'px solid ' + cs.outlineColor);
      if (cs.boxShadow && cs.boxShadow !== 'none') s.push('box-shadow:' + cs.boxShadow);
      var rad = cs.borderTopLeftRadius, rv = rad.indexOf('%') >= 0 ? n(rad) / 100 * Math.min(r.width, r.height) : n(rad);
      if (rv > 0) s.push('border-radius:' + (rv >= Math.min(r.width, r.height) / 2 - 0.5 ? 9999 : Math.round(rv * 10) / 10) + 'px');
      var pad = [cs.paddingTop, cs.paddingRight, cs.paddingBottom, cs.paddingLeft];
      if (pad.some(function (p) { return n(p) > 0; })) s.push('padding:' + pad.join(' '));
      if (/flex|grid/.test(cs.display)) {
        if (n(cs.rowGap) > 0) s.push('row-gap:' + cs.rowGap);
        if (n(cs.columnGap) > 0) s.push('column-gap:' + cs.columnGap);
        if (cs.justifyContent === 'center') s.push('justify-content:center');
      }
      if (cs.textAlign === 'center') s.push('text-align:center');
      if (cs.cursor === 'pointer') s.push('cursor:pointer');
      if (n(cs.marginTop) > 0) s.push('margin-top:' + cs.marginTop);
      if (n(cs.marginBottom) > 0) s.push('margin-bottom:' + cs.marginBottom);
      el.setAttribute('data-x-style', s.join(';'));
    }
    var light = {}, dark = {}, faces = [];
    var rcs = getComputedStyle(document.documentElement);
    for (var j = 0; j < rcs.length; j++) if (rcs[j].indexOf('--') === 0) light[rcs[j]] = rcs.getPropertyValue(rcs[j]).trim();
    var DARK = /prefers-color-scheme:\s*dark|\.dark\b|\[data-[\w-]*=['"]?dark|dark-(mode|theme)|\.theme-dark/i;
    function walk(rules, isDark) {
      for (var q = 0; q < rules.length; q++) {
        var ru = rules[q];
        if (ru.type === 5) { faces.push('@font-face{font-family:' + ru.style.getPropertyValue('font-family') + ';font-weight:' + (ru.style.getPropertyValue('font-weight') || '400') + '}'); continue; }
        if (ru.cssRules && !ru.style) { walk(ru.cssRules, isDark || (ru.media && DARK.test(ru.media.mediaText))); continue; }
        if (!ru.style) continue;
        var dk = isDark || DARK.test(ru.selectorText || '');
        for (var z = 0; z < ru.style.length; z++) {
          var nm = ru.style[z];
          if (nm.indexOf('--') !== 0) continue;
          if (dk) dark[nm] = ru.style.getPropertyValue(nm).trim(); else if (!(nm in light)) light[nm] = ru.style.getPropertyValue(nm).trim();
        }
      }
    }
    for (var t = 0; t < document.styleSheets.length; t++) { try { walk(document.styleSheets[t].cssRules, false); } catch (e) {} }
    if (document.fonts) document.fonts.forEach(function (f) { faces.push('@font-face{font-family:' + f.family + ';font-weight:' + f.weight + '}'); });
    function block(o) { return Object.keys(o).map(function (k) { return k + ':' + o[k] + ';'; }).join(''); }
    var st = document.createElement('style');
    st.id = '__x_css';
    st.textContent = ':root{' + block(light) + '}\n@media (prefers-color-scheme: dark){:root{' + block(dark) + '}}\n' + faces.join('\n');
    document.body.appendChild(st);
    document.documentElement.setAttribute('data-x-flat', '1');
  }
  window.addEventListener('load', function () { setTimeout(run, 1500); });
  setTimeout(run, 10000);
})();
"""

BROWSER_PATHS = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
]


def find_browser():
    env = os.environ.get("CHROME_PATH")
    if env and Path(env).exists():
        return env
    for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome", "msedge",
                 "microsoft-edge", "brave-browser"):
        found = shutil.which(name)
        if found:
            return found
    return next((p for p in BROWSER_PATHS if Path(p).exists()), None)


def render_dom(html, base_dir, browser, size=(1440, 3000), scheme="light", page_width=None, budget_ms=15000):
    """The page's DOM after scripts ran, each element annotated with its computed style; None on failure.

    scheme: light | dark (prefers-color-scheme, plus the `.dark` class and `data-theme="dark"` on <html>).
    page_width: lay the page out this wide (Chrome's window can't be narrower than 500px).
    """
    base = f'<base href="{Path(base_dir).resolve().as_uri()}/">'
    if scheme == "dark":
        base += ("<script>document.documentElement.classList.add('dark');"
                 "document.documentElement.setAttribute('data-theme','dark');</script>")
    if page_width:
        base += f"<style>html{{width:{page_width}px!important;min-width:0!important}}</style>"
    m = re.search(r"<head(\s[^>]*)?>", html, re.I)
    doc = html[:m.end()] + base + html[m.end():] if m else base + html
    i = doc.lower().rfind("</body>")
    inject = "<script>" + FLATTEN_JS + "</script>"
    doc = doc[:i] + inject + doc[i:] if i >= 0 else doc + inject
    with tempfile.TemporaryDirectory() as tmp:
        page = Path(tmp) / "page.html"
        page.write_text(doc)
        cmd = [browser, "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
               "--hide-scrollbars", "--mute-audio", "--allow-file-access-from-files", f"--user-data-dir={tmp}/profile",
               f"--window-size={size[0]},{size[1]}", f"--virtual-time-budget={budget_ms}",
               f"--blink-settings=preferredColorScheme={0 if scheme == 'dark' else 1}", "--dump-dom", page.as_uri()]
        out = _run_until_dumped(cmd, timeout=120)
    return out if "data-x-flat" in out else None


def _run_until_dumped(cmd, timeout):
    """Read the browser's stdout until the dumped document ends. Some Chrome builds print the DOM but never exit."""
    import select
    import time
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    except OSError:
        return ""
    chunks, deadline = [], time.monotonic() + timeout
    try:
        while time.monotonic() < deadline:
            ready, _, _ = select.select([proc.stdout], [], [], 1.0)
            if ready:
                data = os.read(proc.stdout.fileno(), 1 << 16)
                if not data:
                    break
                chunks.append(data)
                if b"</html>" in b"".join(chunks[-2:])[-4096:]:
                    break
            elif proc.poll() is not None:
                break
    finally:
        proc.kill()
        proc.wait()
    return b"".join(chunks).decode("utf-8", "replace")


def _local_css(html, base_dir):
    """Contents of local <link rel=stylesheet> files, for the static read."""
    out = []
    for tag in re.findall(r"<link\b[^>]*>", html, re.I):
        href = re.search(r'href=["\']([^"\']+)', tag)
        if "stylesheet" in tag.lower() and href and not re.match(r"^(https?:|//|data:)", href.group(1)):
            p = Path(base_dir) / href.group(1).split("?")[0]
            if p.is_file():
                out.append(p.read_text(errors="ignore"))
    return "\n".join(out)


def _static_limits(html, ev):
    notes = []
    if re.search(r"<script\b[^>]*\bsrc=|type=[\"'](?:text/babel|module)|ReactDOM|createRoot|createElement\(|new Vue|x-data",
                 html):
        notes.append("The page runs scripts that may build or restyle the DOM; the static read sees only the HTML as written.")
    if re.search(r"<link\b[^>]*stylesheet[^>]*href=[\"'](?:https?:)?//", html, re.I):
        notes.append("Remote stylesheets aren't fetched by the static read.")
    if re.search(r"cdn\.tailwindcss\.com|tailwind", html, re.I) or \
            len(re.findall(r"\bclass=\"[^\"]*\b(?:bg|text|rounded|px|py|p|m|gap)-", html)) > 20:
        notes.append("Tailwind utility classes are only visible to the render.")
    if ev["skippedSelectors"]:
        notes.append(f"{ev['skippedSelectors']} CSS selectors were too complex for the static read "
                     "(sibling combinators, structural pseudo-classes).")
    return notes


def extract(path, to_hex, render="auto", whole_page=False):
    """Evidence for one HTML file. render: auto (browser if found) | always | never."""
    path = Path(path)
    html, kind = unpack(path.read_text(errors="ignore"))
    warnings, ev, mode = [], None, None
    browser = find_browser() if render != "never" else None
    if render == "always" and not browser:
        raise SystemExit("--render always: no Chrome, Chromium, Edge or Brave found (set CHROME_PATH)")
    if browser:
        width, dom = None, render_dom(html, path.parent, browser)
        if dom:
            ev = collect(dom, to_hex, rendered=True, whole_page=whole_page)
            if not ev["framesFound"] and not whole_page and re.search(r"name=[\"']viewport", html, re.I):
                narrow = render_dom(html, path.parent, browser, page_width=390)
                if narrow:  # a responsive page: read it as one phone screen
                    width, dom = 390, narrow
                    ev = collect(dom, to_hex, rendered=True, whole_page=True)
            mode = (f"rendered in {Path(browser).name}, light, " + (f"{width}px wide" if width else "1440px window")
                    + " (computed styles)")
            if ev["customPropsDark"] or DARK.search(html):
                dark = render_dom(html, path.parent, browser, scheme="dark", page_width=width)
                paired = dark and pair_dark(ev, dom, dark, to_hex, whole_page or bool(width))
                if paired:
                    mode += "; dark mode rendered too, and paired per element"
                elif dark is not None:
                    warnings.append("The dark render's DOM differs from the light one, so dark colours "
                                    "couldn't be paired per element. See the CSS custom properties.")
        else:
            warnings.append("The headless render failed or timed out, so the static read was used.")
    if ev is None:
        ev = collect(html, to_hex, whole_page=whole_page, extra_css=_local_css(html, path.parent))
        mode = "static (inline styles and simple stylesheet rules)"
        limits = _static_limits(html, ev)
        if limits and not browser:
            warnings += limits + ["Install Chrome or Chromium (or set CHROME_PATH) and re-run for a full read."]
        elif limits:
            warnings += limits
    if not ev["framesFound"]:
        warnings.append("No device frames were found, so the whole page was read as one screen. "
                        "If it's a board of several screens, check the samples before trusting the counts.")
    if not ev["colours"]:
        warnings.append("No colours were found. Treat the page as a screenshot (references/inputs/visual-sources.md).")
    ev.update(kind=kind, mode=mode, warnings=warnings)
    return ev


# ------------------------------------------------------------------ report


def usage_summary(entry, top=4):
    by = ", ".join(f"{k} ×{n}" for k, n in entry["by"].most_common(top))
    eg = "; ".join(f"'{x}'" for x in entry["samples"][:3])
    var = f" [= {', '.join('--' + v.lstrip('-') for v in entry.get('vars', []))}]" if entry.get("vars") else ""
    if entry.get("dark"):
        var += f" [dark: {', '.join(d for d, _ in entry['dark'].most_common(2))}]"
    return f"{entry['count']} uses on {len(entry['screens'])} screens{var}: {by}" + (f" (e.g. {eg})" if eg else "")


def evidence_markdown(ev, source_name):
    out = [f"# Design evidence: {source_name}", "",
           "Generated by `draft_spec.py --from html`. Raw usage of every value inside the drawn screens, "
           "with device chrome excluded. Map roles by *usage*, per references/material-mapping.md.", "",
           f"- Read: {ev.get('mode', 'static')}",
           f"- Screens: {len(ev['screens'])}" + ("" if ev["framesFound"] else " (no device frames: whole page)"), ""]
    if ev.get("warnings"):
        out += ["> **Check:**"] + [f"> - {w}" for w in ev["warnings"]] + [""]
    has_dark = any(e.get("dark") for e in ev["colours"].values())
    out += ["## Colours (most used first)", "",
            "| Colour | Uses | Screens | CSS variable |" + (" Dark mode |" if has_dark else "") + " Used as | Sample text |",
            "|---|---|---|---|" + ("---|" if has_dark else "") + "---|---|"]
    for h, e in sorted(ev["colours"].items(), key=lambda kv: (-kv[1]["count"], kv[0])):
        by = "<br>".join(f"{k} ×{n}" for k, n in e["by"].most_common(5))
        var = ", ".join(f"`{v}`" for v in e.get("vars", []))
        dk = (" " + "<br>".join(f"`{d}` ×{n}" for d, n in e["dark"].most_common(3)) + " |") if has_dark else ""
        out.append(f"| `{h}` | {e['count']} | {len(e['screens'])} | {var} |{dk} {by} | {'; '.join(e['samples'][:3])} |")
    if ev["gradients"]:
        out += ["", "## Gradients", ""] + [f"- `{g}` ×{n}" for g, n in ev["gradients"].most_common()]
    out += ["", "## Type scale (size / weight)", "",
            "| Size | Weight | Uses | On | Colours | Line height | Letter spacing | Sample |", "|---|---|---|---|---|---|---|---|"]
    for (size, wt), t in sorted(ev["type"].items(), key=lambda kv: (-kv[0][0], -kv[0][1])):
        kinds = ", ".join(f"{k} ×{n}" for k, n in t["kinds"].most_common(3))
        cols = ", ".join(f"`{c}`" for c, _ in t["colours"].most_common(2))
        lhs = ", ".join(v for v, _ in t["lineHeights"].most_common(3))
        ls = ", ".join(v for v, _ in t["letterSpacing"].most_common(2))
        out.append(f"| {size:g} | {wt} | {t['count']} | {kinds} | {cols} | {lhs} | {ls} | {'; '.join(t['samples'])} |")
    out += ["", "## Radii", ""] + [f"- {r:g}px on {k} ×{n}" for (r, k), n in
                                   sorted(ev["radii"].items(), key=lambda kv: (-kv[1], kv[0]))[:24]]
    out += ["", "## Spacing (padding / gap / margin values)", "",
            ", ".join(f"{v:g}px ×{n}" for v, n in sorted(ev["spacing"].items(), key=lambda kv: (-kv[1], kv[0]))[:16])]
    out += ["", "## Heights", ""] + [f"- {k}: " + ", ".join(f"{h:g}px ×{n}" for h, n in c.most_common(6))
                                     for k, c in sorted(ev["heights"].items())]
    if ev["shadows"]:
        out += ["", "## Shadows", ""] + [f"- `{s}` on {k} ×{n}" for (s, k), n in ev["shadows"].most_common(10)]
    out += ["", "## Fonts", ""] + [f"- {f} ×{n}" for f, n in ev["families"].most_common()]
    if ev["fontFaces"]:
        out += [f"- embedded @font-face: {f} weights {sorted(w)}" for f, w in sorted(ev["fontFaces"].items())]
    if ev["legends"]:
        out += ["", "## Legend cards (the design's own role names)", "",
                "Each card pairs the colours used in its preview with the role names the designer wrote. "
                "Match them by order and usage. Where two cards give one colour different roles, that's a conflict.", ""]
        for lg in ev["legends"]:
            cols = ", ".join(f"{p} `{h}`" for p, h in lg["colors"])
            out += [f"### {lg['title']}", f"- colours in preview: {cols}", f"- legend: {lg['legend'].strip()}", ""]
    if ev["annotations"]:
        out += ["", "## Colours outside the screens (swatches, style guide, annotations)", "",
                "Labels are the nearest text. A swatch labelled with a role name is strong evidence for that role.", ""]
        for h, labels in sorted(ev["annotations"].items(), key=lambda kv: -sum(kv[1].values()))[:40]:
            out.append(f"- `{h}`: " + "; ".join(f"'{t}'" for t, _ in labels.most_common(3)))
    if ev["customProps"] or ev["customPropsDark"]:
        out += ["", "## CSS custom properties", ""] + [f"- `{k}`: `{v.strip()}`" for k, v in ev["customProps"].items()]
        if ev["customPropsDark"]:
            out += ["", "Dark mode:", ""] + [f"- `{k}`: `{v.strip()}`" for k, v in ev["customPropsDark"].items()]
    if ev["states"]:
        out += ["", "## Interaction states (CSS rules)", ""] + [
            f"- `{sel}` ({state}): " + ", ".join(f"{k} `{v}`" for k, v in cols.items())
            for sel, state, cols in ev["states"][:30]]
    out += ["", "## Screens", ""] + [f"- {s}" for s in ev["screens"]]
    return "\n".join(out) + "\n"


def load(path):
    return unpack(Path(path).read_text(errors="ignore"))
