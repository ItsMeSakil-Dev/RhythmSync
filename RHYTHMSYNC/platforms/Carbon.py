# ═══════════════════════════════════════════════════════════
#        🌺 RhythmSync 🌺
#   GɪᴛHᴜʙ : github.com/SunloMusicOfficial/RhythmSync
#   Dᴇᴠʟᴏᴘᴇʀ : @YO_UR_OFFICIAL_CRUSH | Telegram
# ═══════════════════════════════════════════════════════════

import asyncio
import random
import time
import urllib.request
from pathlib import Path
from typing import List, Tuple

from PIL import Image, ImageDraw, ImageFilter, ImageFont
from pygments.lexers import get_lexer_by_name, guess_lexer
from pygments.styles import get_style_by_name
from pygments.token import Token
from pygments.util import ClassNotFound


class UnableToFetchCarbon(Exception):
    pass


# Pygments style names — inhi ko theme maan lo.
themes = [
    "monokai", "dracula", "nord", "one-dark", "material", "paraiso-dark",
    "solarized-dark", "solarized-light", "zenburn", "gruvbox-dark", "native",
    "vim", "friendly", "xcode", "rainbow_dash", "inkpot", "tango", "fruity",
]

FALLBACK_STYLE = "monokai"

# Font dhundhne ke liye common paths (Render/Ubuntu/Debian)
FONT_CANDIDATES = [
    Path("fonts/JetBrainsMono-Regular.ttf"),
    Path("RHYTHMSYNC/assets/fonts/JetBrainsMono-Regular.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"),
    Path("/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf"),
    Path("/usr/share/fonts/truetype/ubuntu/UbuntuMono-R.ttf"),
]

FONT_URL = (
    "https://github.com/JetBrains/JetBrainsMono/raw/master/fonts/ttf/"
    "JetBrainsMono-Regular.ttf"
)

_probe = ImageDraw.Draw(Image.new("RGB", (1, 1)))


# ─────────────────────────── helpers ───────────────────────────

def _hex(value: str, default: str = "#ffffff") -> str:
    if not value:
        return default
    return value if value.startswith("#") else "#" + value


def _get_style(name: str):
    try:
        return get_style_by_name(name)
    except ClassNotFound:
        return get_style_by_name(FALLBACK_STYLE)


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    for path in FONT_CANDIDATES:
        if path.exists():
            try:
                return ImageFont.truetype(str(path), size)
            except OSError:
                continue
    # Aakhri koshish: default bitmap font (chhota par kaam chalau)
    return ImageFont.load_default()


def _ensure_font(cache_dir: Path) -> None:
    """Agar koi TTF nahi mila to ek baar JetBrains Mono download karo."""
    if any(p.exists() for p in FONT_CANDIDATES):
        return
    target = cache_dir / "JetBrainsMono-Regular.ttf"
    if target.exists():
        FONT_CANDIDATES.insert(0, target)
        return
    try:
        with urllib.request.urlopen(FONT_URL, timeout=10) as resp:
            target.write_bytes(resp.read())
        FONT_CANDIDATES.insert(0, target)
    except Exception:
        pass  # offline — default font se kaam chal jayega


def _tokenize(code: str, language: str):
    try:
        lexer = (
            get_lexer_by_name(language)
            if language and language != "auto"
            else guess_lexer(code)
        )
    except ClassNotFound:
        lexer = get_lexer_by_name("text")
    return list(lexer.get_tokens(code))


def _to_lines(tokens, style) -> List[List[Tuple[str, str]]]:
    """Tokens ko [(text, color)] ki lines me todo — newlines preserve karte hue."""
    lines: List[List[Tuple[str, str]]] = [[]]
    for ttype, value in tokens:
        color = _hex(style.style_for_token(ttype).get("color"))
        for i, part in enumerate(value.split("\n")):
            if i > 0:
                lines.append([])
            if part:
                lines[-1].append((part, color))

    while lines and not lines[-1]:  # trailing blank lines hatao
        lines.pop()
    return lines or [[("", "#ffffff")]]


def _render(
    code: str,
    out_path: Path,
    theme_name: str,
    language: str,
    font_size: int,
    line_numbers: bool,
    title: str,
) -> None:
    style = _get_style(theme_name)
    bg_color = _hex(style.background_color, "#1e1e1e")
    fg_color = _hex(style.style_for_token(Token.Text).get("color"))

    font = _load_font(font_size)
    lines = _to_lines(_tokenize(code, language), style)

    # ── metrics ──
    char_w = _probe.textlength("M", font=font)
    ascent, descent = font.getmetrics()
    line_h = ascent + descent + 4

    pad_x, pad_y = 34, 26
    bar_h = 40

    gutter_w = 0
    if line_numbers:
        gutter_w = int(_probe.textlength(str(len(lines)), font=font)) + 18

    max_w = max(
        (sum(_probe.textlength(seg, font=font) for seg, _ in ln) for ln in lines),
        default=char_w * 10,
    )

    content_w = int(max_w) + gutter_w
    width = max(520, min(1800, content_w + pad_x * 2))
    height = bar_h + pad_y * 2 + line_h * len(lines)

    # ── base card ──
    card = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(card)
    draw.rounded_rectangle([0, 0, width - 1, height - 1], radius=14, fill=bg_color)

    # title bar + window controls
    draw.rounded_rectangle([0, 0, width - 1, bar_h], radius=14, fill=bg_color)
    draw.rectangle([0, bar_h - 14, width - 1, bar_h], fill=bg_color)
    for i, dot in enumerate(("#ff5f56", "#ffbd2e", "#27c93f")):
        cx = 22 + i * 22
        draw.ellipse([cx - 6, bar_h // 2 - 6, cx + 6, bar_h // 2 + 6], fill=dot)

    if title:
        tw = _probe.textlength(title, font=_load_font(13))
        draw.text(
            ((width - tw) / 2, bar_h / 2 - 8),
            title,
            font=_load_font(13),
            fill="#9a9a9a",
        )

    # ── code ──
    y = bar_h + pad_y
    for idx, segments in enumerate(lines, start=1):
        if line_numbers:
            num = str(idx)
            nw = _probe.textlength(num, font=font)
            draw.text(
                (pad_x + gutter_w - nw - 12, y),
                num,
                font=font,
                fill="#5c5c5c",
            )

        x = pad_x + gutter_w
        for text, color in segments:
            draw.text((x, y), text, font=font, fill=color or fg_color)
            x += _probe.textlength(text, font=font)
        y += line_h

    # ── drop shadow + flatten ──
    shadow_pad, blur = 26, 14
    canvas = Image.new(
        "RGBA", (width + shadow_pad * 2, height + shadow_pad * 2), (255, 255, 255, 255)
    )
    mask = Image.new("L", canvas.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [shadow_pad, shadow_pad + 6, shadow_pad + width, shadow_pad + height + 6],
        radius=14,
        fill=120,
    )
    shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    shadow.paste((0, 0, 0, 255), (0, 0), mask.filter(ImageFilter.GaussianBlur(blur)))

    canvas = Image.alpha_composite(canvas, shadow)
    canvas.paste(card, (shadow_pad, shadow_pad), card)
    canvas.convert("RGB").save(out_path, "PNG", optimize=True)


# ─────────────────────────── API ───────────────────────────

class CarbonAPI:
    def __init__(self, cache_dir: str = "cache", timeout_s: int = 25):
        self.language = "auto"
        self.font_family = "JetBrains Mono"
        self.watermark = False

        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        _ensure_font(self.cache_dir)

    async def close(self):
        """Purane network client ka compatibility stub."""
        return None

    async def generate(self, text: str, user_id) -> str:
        if not text or not text.strip():
            raise UnableToFetchCarbon("Empty text.")
        if len(text) > 10000:
            raise UnableToFetchCarbon("Text too long (max 10k characters).")

        font_size = 15 if len(text) < 1500 else 12
        out = self.cache_dir / f"carbon_{user_id}_{int(time.time() * 1000)}.png"

        try:
            await asyncio.to_thread(
                _render,
                text,
                out,
                random.choice(themes),
                self.language,
                font_size,
                True,
                "RhythmSync",
            )
        except Exception as e:
            raise UnableToFetchCarbon(f"Render failed: {type(e).__name__}: {e}") from e

        if not out.exists() or out.stat().st_size == 0:
            raise UnableToFetchCarbon("Render produced empty file.")

        return str(out.resolve())

# ═══════════════════════════════════════════════════════════
#         🌺 RhythmSync 🌺
#   github.com/SunloMusicOfficial/RhythmSync
# ═══════════════════════════════════════════════════════════
