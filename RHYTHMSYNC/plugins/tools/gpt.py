# ═══════════════════════════════════════════════════════════
# RhythmSync
# GɪᴛHᴜʙ : github.com/SunloMusicOfficial/RhythmSync
# Dᴇᴠʟᴏᴘᴇʀ : @YO_UR_OFFICIAL_CRUSH | Telegram
# ═══════════════════════════════════════════════════════════

import os
import re
import time
import asyncio
import aiohttp
from gtts import gTTS
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ChatAction
from dotenv import load_dotenv

from RHYTHMSYNC import app

load_dotenv()

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
OPENROUTER_KEY = os.getenv("OPENROUTER_KEY")

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODELS_URL     = "https://openrouter.ai/api/v1/models"

TEMP_DIR = "downloads"
os.makedirs(TEMP_DIR, exist_ok=True)

FALLBACK_MODELS = [
    "nvidia/nemotron-3.5-super-vl:free",
    "nvidia/nemotron-3-ultra:free",
    "google/gemma-4-26b-a4b:free",
    "google/gemma-4-31b:free",
    "meta-llama/llama-3.3-70b-instruct:free",
]

_models_cache = {"ids": [], "ts": 0}
_user_models  = {}   # per-user model selection

SYSTEM_PROMPT = (
    "You are RhythmSync AI, a helpful Telegram assistant. "
    "Reply in the same language the user writes in (Hindi, Hinglish, English, etc). "
    "Keep answers clear and concise."
)

# ─────────────────────────────────────────────
# MODEL FETCHING
# ─────────────────────────────────────────────
async def get_free_models() -> list:
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
                        skip = ("rerank", "embed", "transcribe", "whisper",
                                "guard", "span-01", "moderation")
                        if any(x in low for x in skip):
                            continue
                        ids.append(mid)
                    ids.sort(key=lambda x: 0 if ("instruct" in x or "-it" in x) else 1)
                    if ids:
                        _models_cache["ids"] = ids[:20]
                        _models_cache["ts"]  = now
                    return _models_cache["ids"]
    except Exception as e:
        print(f"[GPT] model fetch failed: {e}")

    return _models_cache["ids"] or FALLBACK_MODELS

# ─────────────────────────────────────────────
# OPENROUTER CALL
# ─────────────────────────────────────────────
async def _try_model(session, prompt, model):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENROUTER_KEY}",
        "HTTP-Referer": "https://github.com/SunloMusicOfficial/RhythmSync",
        "X-Title": "RhythmSyncBot",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": prompt},
        ],
        "max_tokens": 1500,
        "temperature": 0.7,
    }
    async with session.post(
        OPENROUTER_URL,
        headers=headers,
        json=payload,
        timeout=aiohttp.ClientTimeout(total=45),
    ) as resp:
        text = await resp.text()
        if resp.status == 200:
            result = await resp.json()
            try:
                return result["choices"][0]["message"]["content"]
            except (KeyError, IndexError):
                raise Exception(f"Malformed response: {text[:120]}")
        raise Exception(f"HTTP {resp.status}: {text[:150]}")


async def get_gpt_response(prompt, model=None):
    if not OPENROUTER_KEY:
        raise Exception(
            "OPENROUTER_KEY not set. Add it in your environment variables."
        )

    async with aiohttp.ClientSession() as session:
        candidates = [model] if model else await get_free_models()
        last_err = None
        for candidate in candidates:
            try:
                return await _try_model(session, prompt, candidate)
            except Exception as e:
                last_err = e
                print(f"[GPT] {candidate} failed: {e}")
                continue
        raise Exception(f"All models failed. Last: {last_err}")

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────
def _clean_text(text: str) -> str:
    """Remove markdown junk + emojis which break gTTS."""
    text = re.sub(r"[*_`#>~\[\]()]", "", text)
    text = re.sub(r"http\S+", "", text)
    text = re.sub(r"[^\w\s.,!?;:\-\u0900-\u097F\u0B80-\u0BFF\u0C00-\u0C7F]", " ", text)
    return text.strip()


def _chunk(text: str, limit: int = 4000):
    """Split long text into Telegram-safe chunks."""
    for i in range(0, len(text), limit):
        yield text[i:i + limit]


async def _send_typing(client, chat_id, stop_event):
    while not stop_event.is_set():
        try:
            await client.send_chat_action(chat_id, ChatAction.TYPING)
        except Exception:
            pass
        await asyncio.sleep(4)

# ─────────────────────────────────────────────
# AI COMMAND  (.ai / .gpt / .ask)
# ─────────────────────────────────────────────
@app.on_message(filters.command(["ai", "gpt", "ask"], prefixes=["/", ".", "!"]))
async def ai_handler(client: Client, message: Message):
    if len(message.command) < 2:
        return await message.reply_text(
            "**🤖 RhythmSync AI**\n\n"
            "**Usage:**\n"
            "• `/ai <question>` — text reply\n"
            "• `/ai voice <question>` — voice reply\n"
            "• `/model <model_id>` — set custom model\n"
            "• `/models` — list free models\n\n"
            "**Example:**\n"
            "`/ai explain black holes in simple words`"
        )

    args = message.command[1:]
    voice_reply = False
    if args[0].lower() == "voice":
        voice_reply = True
        args = args[1:]

    prompt = " ".join(args).strip()
    if not prompt:
        return await message.reply_text("❌ Please provide a question.")

    user_id = message.from_user.id if message.from_user else 0
    model   = _user_models.get(user_id)

    status = await message.reply_text("🤔 **Thinking...**")

    stop_event = asyncio.Event()
    typing_task = asyncio.create_task(_send_typing(client, message.chat.id, stop_event))

    try:
        reply = await get_gpt_response(prompt, model=model)
    except Exception as e:
        stop_event.set()
        typing_task.cancel()
        return await status.edit_text(f"❌ **Error:** `{e}`")
    finally:
        stop_event.set()
        typing_task.cancel()

    try:
        await status.delete()
    except Exception:
        pass

    if not voice_reply:
        for chunk in _chunk(reply):
            await message.reply_text(chunk)
        return

    # ── Voice reply via gTTS ──
    audio_path = os.path.join(TEMP_DIR, f"tts_{message.id}_{int(time.time())}.mp3")
    try:
        clean = _clean_text(reply)
        if len(clean) > 900:
            clean = clean[:900] + "..."

        await client.send_chat_action(message.chat.id, ChatAction.RECORD_AUDIO)
        await asyncio.to_thread(
            gTTS(text=clean, lang="en", slow=False).save, audio_path
        )

        await message.reply_voice(
            voice=audio_path,
            caption=f"🎙 **Voice Reply**\n\n{reply[:300]}"
        )
    except Exception as e:
        await message.reply_text(f"⚠️ Voice failed: `{e}`\n\n**Text reply:**\n\n{reply[:3500]}")
    finally:
        await asyncio.sleep(3)
        try:
            if os.path.exists(audio_path):
                os.remove(audio_path)
        except Exception:
            pass

# ─────────────────────────────────────────────
# REPLY TO BOT HANDLER (Group Chat AI)
# ─────────────────────────────────────────────
@app.on_message(filters.reply & filters.text & ~filters.bot & ~filters.via_bot)
async def reply_ai_handler(client: Client, message: Message):
    # Command ignore karo taaki double trigger na ho
    if message.text.startswith(("/", ".", "!")):
        return

    replied = message.reply_to_message
    if not replied or not replied.from_user:
        return

    me = await client.get_me()
    if replied.from_user.id != me.id:
        return

    prompt = message.text.strip()
    if not prompt:
        return

    if not OPENROUTER_KEY:
        return await message.reply_text(
            "❌ `OPENROUTER_KEY` set nahi hai. Deployment platform ke env vars mein daalein."
        )

    user_id = message.from_user.id if message.from_user else 0
    model   = _user_models.get(user_id)

    stop_event = asyncio.Event()
    typing_task = asyncio.create_task(_send_typing(client, message.chat.id, stop_event))

    try:
        reply = await get_gpt_response(prompt, model=model)
    except Exception as e:
        stop_event.set()
        typing_task.cancel()
        return await message.reply_text(f"❌ **Error:** `{e}`")
    finally:
        stop_event.set()
        typing_task.cancel()

    for chunk in _chunk(reply):
        await message.reply_text(chunk)

# ─────────────────────────────────────────────
# MODEL LIST  (.models)
# ─────────────────────────────────────────────
@app.on_message(filters.command(["models", "aimodels"], prefixes=["/", ".", "!"]))
async def models_handler(client: Client, message: Message):
    models = await get_free_models()
    if not models:
        return await message.reply_text("❌ No free models available right now.")

    lines = ["**🆓 Available Free Models:**\n"]
    for m in models[:15]:
        lines.append(f"• `{m}`")
    lines.append("\n**Set one with:** `/model <model_id>`")

    await message.reply_text("\n".join(lines))

# ─────────────────────────────────────────────
# SET MODEL  (.model)
# ─────────────────────────────────────────────
@app.on_message(filters.command(["model", "aimodel"], prefixes=["/", ".", "!"]))
async def set_model_handler(client: Client, message: Message):
    if len(message.command) < 2:
        return await message.reply_text("**Usage:** `/model <model_id>`\nSee `/models` for list.")

    user_id  = message.from_user.id if message.from_user else 0
    model_id = message.command[1].strip()

    _user_models[user_id] = model_id
    await message.reply_text(f"✅ Model set to: `{model_id}`")

# ─────────────────────────────────────────────
# RESET MODEL  (.resetmodel)
# ─────────────────────────────────────────────
@app.on_message(filters.command(["resetmodel"], prefixes=["/", ".", "!"]))
async def reset_model_handler(client: Client, message: Message):
    user_id = message.from_user.id if message.from_user else 0
    _user_models.pop(user_id, None)
    await message.reply_text("✅ Model reset to auto-select.")

# ─────────────────────────────────────────────
# AI HELP
# ─────────────────────────────────────────────
@app.on_message(filters.command(["aihelp", "gpthelp"], prefixes=["/", ".", "!"]))
async def aihelp_handler(client: Client, message: Message):
    await message.reply_text(
        "**🤖 RhythmSync AI — Help**\n\n"
        "**Commands:**\n"
        "• `/ai <question>` — Ask anything\n"
        "• `/ai voice <question>` — Ask with voice reply\n"
        "• `/models` — List free models\n"
        "• `/model <id>` — Set model\n"
        "• `/resetmodel` — Reset to auto\n\n"
        "**💬 Reply Feature:**\n"
        "Bot ke kisi bhi message ko reply karke direct chat kar sakte hain!\n\n"
        "**Tips:**\n"
        "• Works in 15+ languages (auto-detect)\n"
        "• Free tier, no cost to you\n"
        "• If one model fails, bot auto-switches"
    )

# ─────────────────────────────────────────────
# ERRORS
# ─────────────────────────────────────────────
@app.on_message(filters.command(["aierror"], prefixes=["/", ".", "!"]))
async def error_check(client: Client, message: Message):
    if not OPENROUTER_KEY:
        return await message.reply_text("❌ `OPENROUTER_KEY` missing in env vars.")
    try:
        await get_gpt_response("Say 'OK' in one word.")
        await message.reply_text("✅ API working perfectly.")
    except Exception as e:
        await message.reply_text(f"❌ API error: `{e}`")
