# ═══════════════════════════════════════════════════════════
#        🌺 RhythmSync 🌺
#   GɪᴛHᴜʙ : github.com/SunloMusicOfficial/RhythmSync
#   Dᴇᴠʟᴏᴘᴇʀ : @YO_UR_OFFICIAL_CRUSH | Telegram
# ═══════════════════════════════════════════════════════════

import os
import tempfile
import asyncio
import random

import aiohttp

from pyrogram import filters
from pyrogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from RHYTHMSYNC import app

# ─── Constants ────────────────────────────────────────────────────────────

# Two Google mirrors — if one rate-limits (429), try the other before giving up
GOOGLE_MIRRORS = [
    "https://translate.googleapis.com/translate_a/single",
    "https://clients5.google.com/translate_a/t",
]
MYMEMORY_URL = "https://api.mymemory.translated.net/get"
MAX_CHUNK = 1500
MAX_RETRIES = 3

# Throttle: only N translate requests in-flight at once across the whole bot.
# This prevents bursts (e.g. 3 users hitting /tr at the same second) from
# tripping Google's rate limiter in the first place.
_THROTTLE = asyncio.Semaphore(2)

LANGUAGES = {
    "en": "🇬🇧 English",
    "bn": "🇧🇩 Bengali",
    "hi": "🇮🇳 Hindi",
    "ur": "🇵🇰 Urdu",
    "hin": "🔤 Hinglish",
}


# ─── Low-level translation helpers ────────────────────────────────────────

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


async def _google_translate_once(session, mirror: str, text: str, source: str, target: str):
    params = {"client": "gtx", "sl": source, "tl": target, "dt": "t", "q": text}
    async with session.get(mirror, params=params) as resp:
        if resp.status == 429:
            raise ConnectionRefusedError("rate_limited")
        if resp.status != 200:
            raise RuntimeError(f"HTTP {resp.status}")
        data = await resp.json(content_type=None)

    segments = data[0] or []
    translated = "".join(seg[0] for seg in segments if seg and seg[0])
    detected = data[2] if len(data) > 2 and data[2] else source

    if not translated:
        raise RuntimeError("empty translation")
    return translated, detected


async def _google_translate(session, text: str, source: str, target: str):
    """Try all mirrors, with retry + exponential backoff on rate limits."""
    last_error = None
    for attempt in range(MAX_RETRIES):
        for mirror in GOOGLE_MIRRORS:
            try:
                async with _THROTTLE:
                    return await _google_translate_once(session, mirror, text, source, target)
            except ConnectionRefusedError:
                last_error = "rate_limited"
                continue  # try next mirror immediately
            except Exception as e:
                last_error = str(e)
                continue
        # All mirrors failed this round — back off before retrying
        await asyncio.sleep((2 ** attempt) + random.uniform(0, 0.5))
    raise RuntimeError(last_error or "google_translate_failed")


async def _mymemory_translate(session, text: str, source: str, target: str):
    params = {"q": text, "langpair": f"{source}|{target}"}
    async with session.get(MYMEMORY_URL, params=params) as resp:
        if resp.status != 200:
            raise RuntimeError(f"HTTP {resp.status}")
        data = await resp.json(content_type=None)

    translated = (data.get("responseData") or {}).get("translatedText")
    if not translated:
        raise RuntimeError("mymemory empty")
    return translated, source


async def do_translate(text: str, target: str, source: str = "auto"):
    """Translate text (auto-chunked), Google (with retries+mirrors) -> MyMemory fallback."""
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
        parts, detected = [], source
        for chunk in _chunk(text):
            try:
                out, det = await _google_translate(session, chunk, source, target)
            except Exception:
                try:
                    out, det = await _mymemory_translate(
                        session, chunk, "auto" if source == "auto" else source, target
                    )
                except Exception:
                    raise RuntimeError("All translation services are busy. Please try again shortly.")
            parts.append(out)
            if det and det != "auto":
                detected = det
        return "\n".join(parts), detected


def romanize_hindi(text: str) -> str:
    try:
        from indic_transliteration import sanscript
        from indic_transliteration.sanscript import transliterate
        return transliterate(text, sanscript.DEVANAGARI, sanscript.ITRANS)
    except Exception:
        return text


def write_temp(text: str) -> str:
    path = os.path.join(tempfile.gettempdir(), "translation.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path


# ─── Keyboard builder ─────────────────────────────────────────────────────

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

    if "//" in arg_text and reply and (reply.text or reply.caption):
        source_lang, target_lang = [p.strip().lower() for p in arg_text.split("//", 1)]
        source_lang = source_lang or "auto"
        content = reply.text or reply.caption

        status = await message.reply_text("🌐 ᴛʀᴀɴsʟᴀᴛɪɴɢ...")
        try:
            result, detected = await do_translate(content, target_lang, source_lang)
        except Exception as e:
            return await status.edit(f"❌ ᴛʀᴀɴsʟᴀᴛɪᴏɴ ꜰᴀɪʟᴇᴅ: `{e}`")

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


# ─── Callback: button clicks ────────────────────────────────────────────

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
            raise ValueError("Original message was deleted.")

        raw = anchor.text or anchor.caption
        if not raw:
            raise ValueError("No text found in the original message.")

        if flag == "c":
            parts = raw.split(maxsplit=1)
            content = parts[1] if len(parts) > 1 else ""
            if not content:
                raise ValueError("No text found to translate.")
        else:
            content = raw

    except Exception as e:
        return await callback_query.message.edit_text(f"❌ Couldn't fetch original text: `{e}`")

    try:
        if lang == "hin":
            hindi_text, detected = await do_translate(content, "hi")
            display_lang = "🔤 Hinglish"
            result = romanize_hindi(hindi_text)
        else:
            result, detected = await do_translate(content, lang)
            display_lang = LANGUAGES.get(lang, lang)
    except Exception as e:
        return await callback_query.message.edit_text(f"❌ ᴛʀᴀɴsʟᴀᴛɪᴏɴ ꜰᴀɪʟᴇᴅ: `{e}`")

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
