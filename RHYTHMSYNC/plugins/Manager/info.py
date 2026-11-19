# ═══════════════════════════════════════════════════════════
#        🌺 RhythmSync 🌺
#   GɪᴛHᴜʙ : github.com/SunloMusicOfficial/RhythmSync
#   Dᴇᴠʟᴏᴘᴇʀ : @YO_UR_OFFICIAL_CRUSH | Telegram
# ═══════════════════════════════════════════════════════════

from pyrogram import filters
from pyrogram.errors import RPCError
from RHYTHMSYNC import app


@app.on_message(filters.command(["info", "userinfo", "whois"]))
async def info_cmd(client, message):
    try:
        # ── Determine which user we're looking up ──────────────────────
        if message.reply_to_message:
            user = message.reply_to_message.from_user

            # Channel posts / anonymous group admins have no from_user
            if user is None:
                sender = message.reply_to_message.sender_chat
                name = sender.title if sender else "Unknown"
                sender_id = sender.id if sender else "N/A"
                return await message.reply_text(
                    f"**Sender Info:**\n"
                    f" Type: Channel post / Anonymous admin\n"
                    f" Name: {name}\n"
                    f" ID: `{sender_id}`"
                )

        elif len(message.command) > 1:
            query = message.command[1]
            try:
                user = await client.get_users(query)
            except (RPCError, ValueError, IndexError):
                return await message.reply_text("❌ User not found.")

        else:
            user = message.from_user
            if user is None:
                return await message.reply_text("❌ Couldn't identify the sender.")

        # ── Build info text ─────────────────────────────────────────────
        uname = f"@{user.username}" if user.username else "None"

        try:
            dc = user.dc_id if user.dc_id else "N/A"
        except Exception:
            dc = "N/A"

        txt = (
            f"**User Info:**\n"
            f" ID: `{user.id}`\n"
            f" Name: {user.mention}\n"
            f" Username: {uname}\n"
            f" DC: {dc}"
        )

        # ── Try sending with profile photo, fall back to text-only ──────
        pp = user.photo.big_file_id if getattr(user, "photo", None) else None
        if pp:
            try:
                return await message.reply_photo(pp, caption=txt)
            except Exception:
                pass  # fall through to text reply

        await message.reply_text(txt)

    except Exception as e:
        # Never fail silently — show the real error so it's debuggable
        await message.reply_text(f"❌ **Info failed:**\n`{type(e).__name__}: {e}`")

# ═══════════════════════════════════════════════════════════
#         🌺 RhythmSync 🌺
#   github.com/SunloMusicOfficial/RhythmSync
# ═══════════════════════════════════════════════════════════
