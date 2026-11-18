# ═══════════════════════════════════════════════════════════
#        🌺 RhythmSync 🌺
#   GɪᴛHᴜʙ : github.com/SunloMusicOfficial/RhythmSync
#   Dᴇᴠʟᴏᴘᴇʀ : @YO_UR_OFFICIAL_CRUSH | Telegram
# ═══════════════════════════════════════════════════════════

import os
import urllib.parse
import aiohttp
import aiofiles

from PIL import Image, ImageFilter

from RHYTHMSYNC import app
from pyrogram import filters
from pyrogram.types import Message

# ─── Constants ────────────────────────────────────────────────────────────

# Pollinations AI — free, no API key required, supports HD generation
POLLINATIONS_BASE = "https://image.pollinations.ai/prompt"

# Max upscale factor to avoid huge files / memory issues
MAX_UPSCALE_FACTOR = 2


# ─── Helpers ──────────────────────────────────────────────────────────────

async def download_file(url: str, save_path: str) -> str | None:
    """Download a file from a URL and save it locally."""
    os.makedirs(os.path.dirname(save_path) or ".", exist_ok=True)
    async with aiohttp.ClientSession() as session:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=60)) as resp:
            if resp.status == 200:
                async with aiofiles.open(save_path, "wb") as f:
                    await f.write(await resp.read())
                return save_path
    return None


def local_upscale(input_path: str, output_path: str, factor: int = MAX_UPSCALE_FACTOR) -> str:
    """
    Upscale an image locally using high-quality Lanczos resampling
    plus a light sharpening pass to improve perceived detail.
    This runs instantly, has zero external dependencies, and never fails
    due to third-party API downtime or rate limits.
    """
    with Image.open(input_path) as img:
        img = img.convert("RGB")
        new_size = (img.width * factor, img.height * factor)
        upscaled = img.resize(new_size, Image.LANCZOS)
        # Light sharpening pass to compensate for softness introduced by resizing
        upscaled = upscaled.filter(ImageFilter.UnsharpMask(radius=2, percent=120, threshold=3))
        upscaled.save(output_path, quality=95)
    return output_path


def build_pollinations_url(prompt: str) -> str:
    """Build a Pollinations AI image-generation URL for the given prompt."""
    encoded_prompt = urllib.parse.quote(prompt)
    params = "width=1024&height=1024&nologo=true&enhance=true&model=flux"
    return f"{POLLINATIONS_BASE}/{encoded_prompt}?{params}"


# ─── Commands ─────────────────────────────────────────────────────────────

@app.on_message(filters.command("upscale"))
async def upscale_image(_, message: Message):
    reply = message.reply_to_message
    if not reply or not reply.photo:
        return await message.reply_text("📎 Please reply to an image.")

    status = await message.reply_text("🔄 Upscaling image...")

    local_path = None
    output_path = None
    try:
        local_path = await reply.download()
        output_path = f"{local_path}_upscaled.png"

        local_upscale(local_path, output_path)

        await status.delete()
        await message.reply_document(
            output_path,
            caption="✅ Upscaled successfully."
        )

    except Exception as e:
        await status.edit(f"⚠️ Error: `{str(e)}`")

    finally:
        # Clean up temp files
        for path in (local_path, output_path):
            if path and os.path.exists(path):
                os.remove(path)


@app.on_message(filters.command(["getdraw", "image"]))
async def draw_image(_, message: Message):
    reply = message.reply_to_message
    query = None

    if reply and reply.text:
        query = reply.text
    elif len(message.command) > 1:
        query = message.text.split(None, 1)[1]

    if not query:
        return await message.reply_text("💬 Please reply or provide text.")

    status = await message.reply_text("🎨 Generating image...")

    user_id = message.from_user.id
    chat_id = message.chat.id
    temp_path = f"cache/{user_id}_{chat_id}_{message.id}.png"

    try:
        url = build_pollinations_url(query)
        final_path = await download_file(url, temp_path)

        if not final_path:
            return await status.edit("❌ Failed to generate image.")

        await status.delete()
        await message.reply_photo(final_path, caption=f"`{query}`")

    except Exception as e:
        await status.edit(f"⚠️ Error: `{str(e)}`")

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
