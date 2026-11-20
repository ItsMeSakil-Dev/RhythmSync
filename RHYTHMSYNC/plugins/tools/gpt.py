# ═══════════════════════════════════════════════════════════
# 🌺 RhythmSync 🌺
# GɪᴛHᴜʙ : github.com/SunloMusicOfficial/RhythmSync
# Dᴇᴠʟᴏᴘᴇʀ : @YO_UR_OFFICIAL_CRUSH | Telegram
# ═══════════════════════════════════════════════════════════

import asyncio
import os
import time
import aiohttp
from gtts import gTTS
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ChatAction
from RHYTHMSYNC import app
from dotenv import load_dotenv

load_dotenv()

HARDCODED_OPENROUTER_KEY = "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"
OPENROUTER_KEY = os.getenv("OPENROUTER_KEY") or HARDCODED_OPENROUTER_KEY
OPENROUTER_URL = "1/chat/completions"
MODELS_URL = "https://.ai/api/v1/models"

# ── Static fallback list (sirf agar models API unreachable ho) ──
FALLBACK_MODELS = [
    "nvidia/nemotron-3.5-super-vl:free",
    "nvidia/nemotron-3-ultra:free",
    "google/gemma-4-26b-a4b:free",
    "google/gemma-4-31b:free",
]

_models_cache = {"ids": [], "ts": 0}


async def get_free_models() -> list:
    """Live free-model list from  — 1 ghante ke liye cache hoti hai."""
    now = time.time()
    if _models_cache["ids"] and now - _models_cache["ts"] < 3600:
        return _models_cache["ids"]
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(MODELS_URL, timeout=15) as r:
                if r.status == 200:
                    data = await r.json()
                    ids = []
                    for m in data.get("data", []):
                        p = m.get("pricing", {})
                        if p.get("prompt") != "0" or p.get("completion") != "0":
                            continue
                        mid = m.get("id", "")
                        low = mid.lower()
                        if any(x in low for x in ("rerank", "embed", "transcribe", "whisper", "guard", "span-01")):
                            continue
                        ids.append(mid)
                    ids.sort(key=lambda x: 0 if ("instruct" in x or "-it" in x) else 1)
                    if ids:
                        _models_cache["ids"] = ids[:20]
                        _models_cache["ts"] = now
                        return _models_cache["ids"]
    except Exception:
        pass
    return _models_cache["ids"] or FALLBACK_MODELS


async def _try_model(session, prompt, model):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENROUTER_KEY}",
        "HTTP-Referer": "https://github.com/SunloMusicOfficial/RhythmSync",
        "X-Title": "RhythmSyncBot",
    }
    data = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 1024,
    }
    async with session.post(
        OPENROUTER_URL,
        headers=headers,
        json=data,
        timeout=aiohttp.ClientTimeout(total=30),
    ) as resp:
        text = await resp.text()
        if resp.status == 200:
            result = await resp.json()
            return result["choices"][0]["message"]["content"]
        raise Exception(f"{resp.status}: {text[:120]}")


async def get_gpt_response(prompt, model=None):
    if not OPENROUTER_KEY:
        raise Exception("OPENROUTER_KEY missing — set it in Render env vars or edit gpt.py")

    async with aiohttp.ClientSession() as session:
        candidates = []
        if model:
            candidates.append(model)
        candidates.extend(await get_free_models())

        last_err = None
        for m in candidates:
            if m in candidates[:candidates.index(m)]:
                continue
            try:
                return await _try_model(session, prompt, m)
            except Exception as e:
                last_err = str(e)
                continue
        raise Exception(f"❌ All models failed ({len(candidates)} tried). Last: {last_err}")


async def safe_gpt_response(prompt, timeout=45):
    try:
        return await asyncio.wait_for(get_gpt_response(prompt), timeout=timeout)
    except asyncio.TimeoutError:
        raise Exception("⚠️ GPT request timed out.")
    except Exception as e:
        raise Exception(str(e))


async def send_typing_action(client, chat_id, interval=3):
    try:
        while True:
            await client.send_chat_action(chat_id, ChatAction.TYPING)
            await asyncio.sleep(interval)
    except asyncio.CancelledError:
        pass


def _build_fullname(first_name, last_name, username):
    first = first_name or ""
    last = (last_name or "").strip()
    full = f"{first} {last}".strip() or (f"@{username}" if username else "")
    return full or "there"


def _user_mention_text(user):
    full = _build_fullname(
        getattr(user, "first_name", None),
        getattr(user, "last_name", None),
        getattr(user, "username", None),
    )
    mention_attr = getattr(user, "mention", None)
    if callable(mention_attr):
        try:
            return mention_attr(full)
        except Exception:
            pass
    return f"[{full}](tg://user?id={user.id})"


def get_requester_identity(message):
    if message.from_user:
        u = message.from_user
        full = _build_fullname(u.first_name, getattr(u, "last_name", None), getattr(u, "username", None))
        return full, _user_mention_text(u)
    if message.sender_chat:
        t = message.sender_chat.title or "there"
        return t, t
    return "there", "there"


async def process_query(client, message, tts=False, model=None):
    full, mention = get_requester_identity(message)
    if len(message.command) < 2:
        return await message.reply_text(
            f"✨ ʜᴇʏ {mention},\nɪ'ᴍ ˹ʀʜʏᴛʜᴍ ✘ sʏɴᴄ˼ 💫\nAsk me anything!"
        )

    query = message.text.split(" ", 1)[1].strip()
    if len(query) > 4000:
        return await message.reply_text("❌ Prompt too long (max 4000 chars).")

    audio_file = "response.mp3"
    typing_task = asyncio.create_task(send_typing_action(client, message.chat.id))

    try:
        content = await safe_gpt_response(query)
        if not content:
            return await message.reply_text("⚠️ No response from AI.")

        styled = (
            f"✨ ʜᴇʏ {mention},\n"
            f"ɪ'ᴍ ˹ʀʜʏᴛʜᴍ ✘ sʏɴᴄ˼ 💫\n"
            f"──────────────\n"
            f"🧠 ʀᴇsᴘᴏɴsᴇ:\n{content}"
        )

        if tts:
            try:
                tts_engine = gTTS(text=content[:1000], lang="en")
                tts_engine.save(audio_file)
                await client.send_voice(chat_id=message.chat.id, voice=audio_file, caption=styled)
            except Exception as tts_error:
                await message.reply_text(f"❌ Voice generation error: {tts_error}")
        else:
            for i in range(0, len(styled), 4096):
                await message.reply_text(styled[i:i + 4096])
    except Exception as e:
        await message.reply_text(str(e))
    finally:
        typing_task.cancel()
        if os.path.exists(audio_file):
            try:
                os.remove(audio_file)
            except Exception:
                pass


# ── COMMANDS ──
@app.on_message(filters.command(["ai", "gpt", "bard", "gemini", "llama", "mistral"], prefixes=["/", ".", "-", "+", "?", "$"]))
async def gpt_handler(client, message):
    if not OPENROUTER_KEY:
        return await message.reply_text(
            "❌ AI not configured.\n\nSet OPENROUTER_KEY in Render env vars or edit gpt.py."
        )
    try:
        await asyncio.wait_for(process_query(client, message), timeout=60)
    except asyncio.TimeoutError:
        await message.reply_text("⏳ Timeout. Try again with a shorter prompt.")


# ── SAKIL AI VOICE MODE ──
@app.on_message(filters.command(["assis", "aivoice"], prefixes=["/", ".", "a", "A"]))
async def sakil_tts_handler(client, message):
    try:
        await asyncio.wait_for(process_query(client, message, tts=True), timeout=60)
    except asyncio.TimeoutError:
        await message.reply_text("⏳ Timeout. Try again.")


# ═══════════════════════════════════════════════════════════
# 🌺 RhythmSync 🌺
# github.com/SunloMusicOfficial/RhythmSync
# Dᴇᴠʟᴏᴘᴇʀ : @YO_UR_OFFICIAL_CRUSH | Telegram
# ═══════════════════════════════════════════════════════════
