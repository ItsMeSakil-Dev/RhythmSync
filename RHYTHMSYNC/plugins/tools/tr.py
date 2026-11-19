# ═══════════════════════════════════════════════════════════
#        🌺 RhythmSync 🌺
#   GɪᴛHᴜʙ : github.com/SunloMusicOfficial/RhythmSync
#   Dᴇᴠʟᴏᴘᴇʀ : @YO_UR_OFFICIAL_CRUSH | Telegram
# ═══════════════════════════════════════════════════════════

import os
import time
import random
import asyncio
import tempfile
import urllib.parse

import aiohttp

from pyrogram import filters
from pyrogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from RHYTHMSYNC import app

# ─── Provider endpoints ───────────────────────────────────────────────────

GOOGLE_URL = "https://translate.googleapis.com/translate_a/single"

# Public Lingva instances (free Google frontends built for programmatic use,
# much more tolerant than hitting googleapis directly from a shared IP)
LINGVA_INSTANCES = [
    "https://lingva.ml",
    "https://lingva.garudalinux.org",
    "https://translate.plausibility.cloud",
]

MYMEMORY_URL = "https://api.mymemory.translated.net/get"

# Last-resort free LLM endpoint (same provider already used for /image)
POLLINATIONS_TEXT = "https://text.pollinations.ai"

MAX_CHUNK = 1500

# Only N translation requests in flight bot-wide
_THROTTLE = asyncio.Semaphore(3)

# Simple in-memory cache: (text, source, target) -> (result, detected)
_CACHE: dict[tuple[str, str, str], tuple[str, str]] = {}
_CACHE_MAX = 500

LANGUAGES = {
    "en": "🇬🇧 English",
    "bn": "🇧🇩 Bengali",
    "hi": "🇮🇳 Hindi",
    "ur": "🇵🇰 Urdu",
    "hin": "🔤 Hinglish",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json,text/plain,*/*",
}


# ─── Utilities ────────────────────────────────────────────────────────────

def _chunk(text: str, size: int = MAX_CHUNK) -> list[str]:
    if len(text) <= size:
        return [text]
    chunks, current = [], ""
    for line in text.splitlines(keepends=True):
        if len(current) + len(line) > size:
            if current:
                chunks.append(current)
            while len(line) > size:
                chunks.append(line[:size])
                line = line[size:]
            current = line
        else:
            current += line
    if current:
        chunks.append(current)
    return chunks or [text[:size]]


def _cache_get(key):
    return _CACHE.get(key)


def _cache_put(key, value):
    if len(_CACHE) >= _CACHE_MAX:
        _CACHE.pop(next(iter(_CACHE)))
    _CACHE[key] = value


def write_temp(text: str) -> str:
    path = os.path.join(tempfile.gettempdir(), "translation.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path


# ─── Provider 1: Google gtx (dj=1 → clean JSON) ───────────────────────────

async def _google(session, text, source, target):
    params = {
        "client": "gtx",
        "sl": source,
        "tl": target,
        "dt": "t",
        "dj": "1",          # JSON response with "sentences" + "src"
        "q": text,
    }
    async with session.get(GOOGLE_URL, params=params, headers=HEADERS) as resp:
        if resp.status != 200:
            raise RuntimeError(f"google HTTP {resp.status}")
        data = await resp.json(content_type=None)

    translated = "".join(s.get("trans", "") for s in data.get("sentences", []))
    if not translated:
        raise RuntimeError("google empty")
    return translated, data.get("src") or source


# ─── Provider 2: Lingva instances ─────────────────────────────────────────

async def _lingva(session, text, source, target):
    src = "auto" if source == "auto" else source
    path = urllib.parse.quote(text, safe="")
    last = None
    for base in LINGVA_INSTANCES:
        try:
            url = f"{base}/api/v1/{src}/{target}/{path}"
            async with session.get(url, headers=HEADERS) as resp:
                if resp.status != 200:
                    last = f"lingva HTTP {resp.status}"
                    continue
                data = await resp.json(content_type=None)
            translated = data.get("translation")
            if not translated:
                last = "lingva empty"
                continue
            return translated, data.get("info", {}).get("detectedSource") or source
        except Exception as e:
            last = str(e)
            continue
    raise RuntimeError(last or "lingva failed")


# ─── Provider 3: MyMemory (needs a REAL source code, not "auto") ──────────

async def _mymemory(session, text, source, target):
    if source == "auto":
        raise RuntimeError("mymemory needs explicit source")
    params = {"q": text, "langpair": f"{source}|{target}"}
    async with session.get(MYMEMORY_URL, params=params, headers=HEADERS) as resp:
        if resp.status != 200:
            raise RuntimeError(f"mymemory HTTP {resp.status}")
        data = await resp.json(content_type=None)

    # MyMemory returns 200 + error text inside translatedText on bad langpairs
    if data.get("responseStatus") != 200:
        raise RuntimeError(data.get("responseDetails") or "mymemory rejected")
    translated = (data.get("responseData") or {}).get("translatedText")
    if not translated:
        raise RuntimeError("mymemory empty")
    return translated, source


# ─── Provider 4: Pollinations text LLM (last resort, never blocks) ────────

LANG_NAMES = {
    "en": "English", "bn": "Bengali", "hi": "Hindi",
    "ur": "Urdu", "hin": "Hinglish (Hindi written in Roman/Latin letters)",
}

async def _pollinations(session, text, source, target):
    lang_name = LANG_NAMES.get(target, target)
    prompt = (
        f"Translate the text below into {lang_name}. "
        f"Output ONLY the {lang_name} translation, no explanations, no quotes, "
        f"no notes, no romanization unless the target is Hinglish.\n\n"
        f"TEXT:\n{text}"
    )
    url = f"{POLLINATIONS_TEXT}/{urllib.parse.quote(prompt, safe='')}"
    async with session.get(url, params={"model": "openai"}, headers=HEADERS) as resp:
        if resp.status != 200:
            raise RuntimeError(f"pollinations HTTP {resp.status}")
        out = (await resp.text()).strip()
    if not out:
        raise RuntimeError("pollinations empty")
    return out, source


# ─── Provider chain ───────────────────────────────────────────────────────

PROVIDERS_AUTO = [_google, _lingva, _pollinations]           # support "auto"
PROVIDERS_FIXED = [_google, _lingva, _mymemory, _pollinations]


async def _translate_chunk(session, text, source, target):
    providers = PROVIDERS_AUTO if source == "auto" else PROVIDERS_FIXED
    errors = []
    for provider in providers:
        try:
            async with _THROTTLE:
                return await provider(session, text, source, target)
        except Exception as e:
            errors.append(f"{provider.__name__}: {e}")
            continue
    raise RuntimeError(" | ".join(errors[-2:]) or "all providers failed")


async def do_translate(text: str, target: str, source: str = "auto"):
    key = (text, source, target)
    cached = _cache_get(key)
    if cached:
        return cached

    async with aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(total=45)
    ) as session:
        parts, detected = [], source
        for chunk in _chunk(text):
            out, det = await _translate_chunk(session, chunk, source, target)
            parts.append(out)
            if det and det != "auto":
                detected = det

    result = "\n".join(parts)
    _cache_put(key, (result, detected))
    return result, detected


def romanize_hindi(text: str) -> str:
    try:
        from indic_transliteration import sanscript
        from indic_transliteration.sanscript import transliterate
        return transliterate(text, sanscript.DEVANAGARI, sanscript.ITRANS)
    except Exception:
        return text


# ─── Keyboard ─────────────────────────────────────────────────────────────

def build_keyboard(anchor_id: int, flag: str) -> InlineKeyboardMarkup:
    buttons, row = [], []
    for code, label in LANGUAGES.items():
        row.append(InlineKeyboardButton(label, callback_data=f"tr|{code}|{anchor_id}|{flag}"))
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return InlineKeyboardMarkup(buttons)


# ─── Command: /tr ─────────────────────────────────────────────────────────

@app.on_message(filters.command("tr"))
async def translate_cmd(_, message: Message):
    reply = message.reply_to_message
    args = message.text.split(maxsplit=1)
    arg_text = args[1].strip() if len(args) > 1 else ""

    # Power-user: /tr en//hi (reply required, no buttons)
    if "//" in arg_text and reply and (reply.text or reply.caption):
        source_lang, target_lang = [p.strip().lower() for p in arg_text.split("//", 1)]
        source_lang = source_lang or "auto"
        content = reply.text or reply.caption

        status = await message.reply_text("🌐 ᴛʀᴀɴsʟᴀᴛɪɴɢ...")
        try:
            result, detected = await do_translate(content, target_lang, source_lang)
        except Exception as e:
            return await status.edit(f"❌ ᴛʀᴀɴsʟᴀᴛɪᴏɴ ꜰᴀɪʟᴇᴅ:\n`{e}`")

        text = f"🌐 **ᴛʀᴀɴsʟᴀᴛᴇᴅ:** `{detected}` ➜ `{target_lang}`\n\n{result}"
        if len(text) <= 4096:
            return await status.edit(text)
        await status.delete()
        path = write_temp(text)
        await message.reply_document(path, caption=f"🌐 `{detected}` ➜ `{target_lang}`")
        return os.remove(path)

    if reply and (reply.text or reply.caption):
        anchor_id, flag = reply.id, "r"
    elif arg_text:
        anchor_id, flag = message.id, "c"
    else:
        return await message.reply_text(
            "📌 ʀᴇᴘʟʏ ᴛᴏ ᴀ ᴛᴇxᴛ, ᴏʀ ᴛʏᴘᴇ `/tr <text>`."
        )

    await message.reply_text(
        "🌍 **Choose a language to translate into:**",
        reply_markup=build_keyboard(anchor_id, flag),
    )


# ─── Callback ─────────────────────────────────────────────────────────────

@app.on_callback_query(filters.regex(r"^tr\|"))
async def translate_callback(client, callback_query: CallbackQuery):
    try:
        _, lang, anchor_id, flag = callback_query.data.split("|")
        anchor_id = int(anchor_id)
    except Exception:
        return await callback_query.answer("⚠️ Invalid request.", show_alert=True)

    await callback_query.answer("Translating...")

    try:
        anchor = await client.get_messages(callback_query.message.chat.id, anchor_id)
        if not anchor:
            raise ValueError("original message deleted")
        raw = anchor.text or anchor.caption
        if not raw:
            raise ValueError("no text in original message")

        if flag == "c":
            parts = raw.split(maxsplit=1)
            content = parts[1] if len(parts) > 1 else ""
            if not content:
                raise ValueError("no text to translate")
        else:
            content = raw
    except Exception as e:
        return await callback_query.message.edit_text(f"❌ {e}")

    try:
        if lang == "hin":
            hindi_text, detected = await do_translate(content, "hi")
            display_lang = LANGUAGES["hin"]
            result = romanize_hindi(hindi_text)
        else:
            result, detected = await do_translate(content, lang)
            display_lang = LANGUAGES.get(lang, lang)
    except Exception as e:
        return await callback_query.message.edit_text(f"❌ ᴛʀᴀɴsʟᴀᴛɪᴏɴ ꜰᴀɪʟᴇᴅ:\n`{e}`")

    text = f"🌐 **{display_lang}** (from `{detected}`):\n\n{result}"

    if len(text) > 4096:
        await callback_query.message.delete()
        path = write_temp(text)
        await callback_query.message.reply_document(path, caption=f"🌐 {display_lang}")
        os.remove(path)
    else:
        await callback_query.message.edit_text(
            text, reply_markup=callback_query.message.reply_markup
        )

# ═══════════════════════════════════════════════════════════
#         🌺 RhythmSync 🌺
#   github.com/SunloMusicOfficial/RhythmSync
# ═══════════════════════════════════════════════════════════
