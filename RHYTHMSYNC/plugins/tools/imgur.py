# ═══════════════════════════════════════════════════════════
#        🌺 RhythmSync 🌺
#   Feature: /imgur - Upload replied photo to Imgur
# ═══════════════════════════════════════════════════════════

import os
from typing import Optional, Tuple

import aiohttp
from pyrogram import filters
from pyrogram.types import Message

from RHYTHMSYNC import app
from config import BANNED_USERS

IMGUR_CLIENT_ID = os.environ.get("IMGUR_CLIENT_ID", "")


# ─── /imgur command ─────────────────────────────────────────

@app.on_message(filters.command("imgur") & filters.reply & ~BANNED_USERS)
async def imgur_upload(client, message: Message):
    """Upload replied photo to Imgur and return direct + delete link."""
    if not IMGUR_CLIENT_ID:
        return await message.reply_text(
            "❌ Imgur Client-ID configured nahi hai.\n"
            "`IMGUR_CLIENT_ID` environment variable set karo."
        )

    replied = message.reply_to_message
    if not replied or not replied.photo:
        return await message.reply_text(
            "📷 Ek photo ko reply karke `/imgur` use karo."
        )

    status = await message.reply_text("⬆️ **Uploading to Imgur...**")

    # Step 1: Download photo from Telegram servers
    photo_path = await replied.download(file_name=f"imgur_{replied.id}.jpg")

    try:
        # Step 2: Upload to Imgur
        link, delete_hash = await _upload_to_imgur(photo_path)

        if link:
            delete_url = f"https://imgur.com/delete/{delete_hash}"
            await status.edit_text(
                f"✅ **Upload Successful!**\n\n"
                f"🔗 **Direct URL:**\n`{link}`\n\n"
                f"🗑 **Delete URL:**\n`{delete_url}`\n\n"
                f"📝 **Markdown:**\n`![image]({link})`",
                disable_web_page_preview=False,
            )
        else:
            await status.edit_text("❌ Upload fail ho gaya. Baad mein try karo.")

    except Exception as e:
        await status.edit_text(f"❌ **Error:** `{e}`")

    finally:
        # Cleanup temp downloaded file
        if os.path.exists(photo_path):
            os.remove(photo_path)


async def _upload_to_imgur(file_path: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Upload file to Imgur anonymously.
    Returns (direct_link, delete_hash) or (None, None) on failure.
    """
    headers = {"Authorization": f"Client-ID {IMGUR_CLIENT_ID}"}
    url = "https://api.imgur.com/3/image"

    async with aiohttp.ClientSession() as session:
        with open(file_path, "rb") as f:
            data = aiohttp.FormData()
            data.add_field(
                "image", f, filename="image.jpg", content_type="image/jpeg"
            )

            async with session.post(url, headers=headers, data=data) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    link = result["data"]["link"]
                    delete_hash = result["data"]["deletehash"]
                    return link, delete_hash
                return None, None
