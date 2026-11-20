# ═══════════════════════════════════════════════════════════
# 🌺 RhythmSync 🌺
# GɪᴛHᴜʙ : github.com/SunloMusicOfficial/RhythmSync
# Dᴇᴠʟᴏᴘᴇʀ : @YO_UR_OFFICIAL_CRUSH | Telegram
# ═══════════════════════════════════════════════════════════

import asyncio
import os
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
_URL = "1/chat/completions"

# ── 12 FREE MODELS — auto-fallback ──
FREE_MODELS = [
    "google/gemma-3-12b-it:free",
    "meta-llama/llama-3.2-3b-instruct:free",
    "meta-llama/llama-3.2-1b-instruct:free",
    "google/gemma-2-9b-it:free",
    "mistralai/mistral-7b-instruct:free",
    "huggingfaceh4/zephyr-7b-beta:free",
    "nousresearch/nous-hermes-2-mixtral-8x7b-dpo:free",
    " teknium/openhermes-2.5-mistral-7b-16k:free",
    "pyromind/lmstudio-community/llama-3.2-3b:free",
    "liuhaotian/llava-1.6-34b-hf:free",
    "gryphe/mythomax-l2-13b:free",
    "undi95/toppy-m-7b:free",
]

# ── Paid models for specific commands ──
PAID_MODEL_MAP = {
    "gpt": "openai/gpt-4o",
    "bard": "google/gemini--001",
    "gemini": "google/gemini--001",
    "llama": "meta-llama/llama-3.3-70b-instruct",
    "mistral": "mistralai/mistral-large-2411",
}


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
    async with session.post(OPENROUTER_URL, headers=headers, json=data, timeout=aiohttp.ClientTimeout(total=30)) as resp:
        text = await resp.text()
        if resp.status == 200:
            result = await resp.json()
            return result["choices"][0]["message"]["content"]
        raise Exception(f"{resp.status}: {text[:100]}")


async def get_gpt_response(prompt, model=None):
    if not OPENROUTER_KEY:
        raise Exception("OPENROUTER_KEY missing — set it in Render env vars or edit gpt.py")
    async with aiohttp.ClientSession() as session:
        if model:
            try:
                return await _try_model(session, prompt, model)
            except Exception as e:
                if ":free" not in model:
                    raise Exception(f"❌ Paid model unavailable: {e}")
        last_err = None
        for m in FREE_MODELS:
            try:
                return await _try_model(session, prompt, m)
            except Exception as e:
                last_err = e
                continue
        raise Exception(f"❌ All models failed. Last error: {last_err}")


async def safe_gpt_response(prompt, timeout=30):
    try:
        return await asyncio.wait_for(get_gpt_response(prompt), timeout=timeout)
    except asyncio.TimeoutError:
        raise Exception("⚠️ Request timed out.")
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
    full = (f"{first} {last}".strip()) or (f"@{username}" if username else "")
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
        title = message.sender_chat.title or "there"
        return title, title
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
            return await message.reply_text("⚠️ No response.")

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
                await client.send_voice(
                    chat_id=message.chat.id,
                    voice=audio_file,
                    caption=styled
                )
            except Exception as tts_error:
                await message.reply_text(f"❌ Voice error: {tts_error}")
        else:
            for i in range(0, len(styled), 4096):
                await message.reply_text(styled[i:i+4096])

    except Exception as e:
        await message.reply_text(str(e))
    finally:
        typing_task.cancel()
        if os.path.exists(audio_file):
            try:
                os.remove(audio_file)
            except Exception:
                pass


@app.on_message(filters.command(["ai", "gpt", "bard", "gemini", "llama", "mistral"], prefixes=["/", ".", "-", "+", "?", "$"]))
async def gpt_handler(client, message):
    if not OPENROUTER_KEY:
        return await message.reply_text(
            "❌ AI not configured.\n\n"
            "Set _KEY in Render env vars."
        )
    cmd = message.command[0].lower()
    model = PAID_MODEL_MAP.get(cmd)
    try:
        await asyncio.wait_for(process_query(client, message, model=model), timeout=60)
    except asyncio.TimeoutError:
        await message.reply_text("⏳ Timeout. Try again.")


@app.on_message(filters.command(["assis", "aivoice"], prefixes=["/", ".", "a", "A"]))
async def sakil_tts_handler(client, message):
    try:
        await asyncio.wait_for(process_query(client, message, tts=True), timeout=60)
    except asyncio.TimeoutError:
        await message.reply_text("⏳ Timeout. Try again.")


# ═══════════════════════════════════════════════════════════
# 🌺 RhythmSync 🌺
# github.com.com/SunloMusicOfficial/RhythmSync
# ═══════════════════════════════════════════════════════════
