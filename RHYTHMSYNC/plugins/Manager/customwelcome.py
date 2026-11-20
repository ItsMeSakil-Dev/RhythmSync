# ═══════════════════════════════════════════════════════════
# 🌺 RhythmSync 🌺
# GɪᴛHᴜʙ : github.com/SunloMusicOfficial/RhythmSync
# Dᴇᴠʟᴏᴘᴇʀ : @YO_UR_OFFICIAL_CRUSH | Telegram
# ═══════════════════════════════════════════════════════════
"""
PREMIUM CUSTOM WELCOME SYSTEM
────────────────────────────
/wel          → status check
/setwel <txt>  → custom welcome text set (admin)
/setwelphoto   → welcome photo set (admin, reply to photo)
/welmsg        → preview (admin)
/delwel        → reset to default (admin)

Placeholders: {mention} {uid} {uname} {count} {chat}
"""

import logging

from pyrogram import filters
from pyrogram.types import Message

from RHYTHMSYNC import app
from RHYTHMSYNC.core.mongo import mongodb
from RHYTHMSYNC.utils.admin_filters import admin_filter
from RHYTHMSYNC.utils.colored_buttons import (
    styled_button,
    send_message_colored,
    send_photo_colored,
    buttons_to_inline_markup,
)

logger = logging.getLogger(__name__)

COL = mongodb["custom_welcome"]

# ────────────────── defaults ──────────────────

DEFAULT_BODY = (
    "╔═══════════════════╗\n"
    "║ 👤 Nᴀᴍᴇ : {mention}\n"
    "║ 🆔 Iᴅ : {uid}\n"
    "║ 🔗 Usᴇʀɴᴀᴍᴇ : {uname}\n"
    "║ 🌐 Tᴏᴛᴀʟ Mᴇᴍʙᴇʀs : {count}\n"
    "╚═══════════════════╝"
)

FRAME = ("✨❄─────✧ ᴡᴇʟᴄᴏᴍᴇ ✧─────❄✨\n"
         "💫 {chat} 💫\n\n{body}\n")

USAGE = (
    "**ᴜsᴀɢᴇ:** /setwel <ᴛᴇxᴛ>\n\n"
    "ᴘʟᴀᴄᴇʜᴏʟᴅᴇʀs:\n"
    "{mention} — ᴍᴇᴍʙᴇʀ\n{uid} — ɪᴅ\n"
    "{uname} — ᴜsᴇʀɴᴀᴍᴇ\n{count} — ᴛᴏᴛᴀʟ ᴍᴇᴍʙᴇʀs\n"
    "{chat} — ɢʀᴏᴜᴘ ᴛɪᴛʟᴇ"
)

# ────────────────── db helpers ──────────────────

async def _get(cid: int) -> dict:
    return await COL.find_one({"chat_id": cid}) or {}

async def _save(cid: int, doc: dict) -> None:
    await COL.update_one({"chat_id": cid}, {"$set": doc}, upsert=True)

# ────────────────── formatting ──────────────────

def _fmt(text: str, *, mention: str, uid, uname: str, count, chat: str) -> str:
    return (text
            .replace("{mention}", mention)
            .replace("{uid}", str(uid))
            .replace("{uname}", uname)
            .replace("{count}", str(count))
            .replace("{chat}", chat))

def _buttons(cid: int):
    return [[
        styled_button("💎 ɢʀᴏᴜᴘ sᴛᴀᴛs", callback_data=f"welstats:{cid}", style="primary"),
        styled_button("⚡ ᴏғғɪᴄɪᴀʟ ʙᴏᴛ", callback_data=f"welbot:{cid}", style="success"),
    ]]

async def _send(chat_id: int, text: str, photo, cid: int) -> None:
    buttons = _buttons(cid)
    if photo:
        cap = text[:1020] + "…" if len(text) > 1020 else text
        try:
            ok = await send_photo_colored(chat_id, photo, cap, buttons)
        except Exception:
            ok = None
        if ok:
            return
        try:
            await app.send_photo(chat_id, photo, caption=cap,
                                 reply_markup=buttons_to_inline_markup(buttons))
        except Exception:
            await app.send_message(chat_id, cap)
    else:
        ok = await send_message_colored(chat_id, text, buttons)
        if not ok:
            await app.send_message(chat_id, text,
                                   reply_markup=buttons_to_inline_markup(buttons))

# ────────────────── commands ──────────────────

@app.on_message(filters.command("setwel") & admin_filter & filters.group)
async def set_welcome_text(_, message: Message):
    if len(message.command) < 2:
        return await message.reply_text(USAGE)
    text = message.text.split(None, 1)[1].strip()
    rec = await _get(message.chat.id)
    await _save(message.chat.id, {"text": text,
                                  "photo": rec.get("photo")})
    return await message.reply_text(
        f"**ᴄᴜsᴛᴏᴍ ᴡᴇʟᴄᴏᴍᴇ ᴛᴇxᴛ sᴇᴛ! ✅**\n\n{text}\n\n"
        "**ᴘʀᴇᴠɪᴇᴡ:** /welmsg • **ʀᴇsᴇᴛ:** /delwel")


@app.on_message(filters.command("setwelphoto") & admin_filter & filters.group)
async def set_welcome_photo(_, message: Message):
    if not message.reply_to_message or not message.reply_to_message.photo:
        return await message.reply_text(
            "**ʀᴇᴘʟʏ ᴛᴏ ᴀ ᴘʜᴏᴛᴏ ᴛᴏ sᴇᴛ ɪᴛ ᴀs ᴡᴇʟᴄᴏᴍᴇ ɪᴍᴀɢᴇ.**")
    rec = await _get(message.chat.id)
    await _save(message.chat.id, {"photo": message.reply_to_message.photo.file_id,
                                   "text": rec.get("text") or DEFAULT_BODY})
    return await message.reply_text("**ᴡᴇʟᴄᴏᴍᴇ ɪᴍᴀɢᴇ sᴇᴛ! ✅**\n**ᴘʀᴇᴠɪᴇᴡ:** /welmsg")


@app.on_message(filters.command("welmsg") & admin_filter & filters.group)
async def preview_welcome(_, message: Message):
    rec = await _get(message.chat.id)
    body = _fmt(rec.get("text") or DEFAULT_BODY,
                mention="ᴍᴇᴍʙᴇʀ", uid="123456789", uname="testuser",
                count="247", chat=message.chat.title or "ᴍʏ ɢʀᴏᴜᴘ")
    out = FRAME.format(chat=message.chat.title or "ᴍʏ ɢʀᴏᴜᴘ", body=body)
    await _send(message.chat.id, out, rec.get("photo"), message.chat.id)


@app.on_message(filters.command("delwel") & admin_filter & filters.group)
async def delete_welcome(_, message: Message):
    await COL.delete_one({"chat_id": message.chat.id})
    return await message.reply_text(
        "**ᴄᴜsᴛᴏᴍ ᴡᴇʟᴄᴏᴍᴇ ʀᴇsᴇᴛ! ᴅᴇғᴀᴜʟᴛ ʙᴀᴄᴋ ✅**")


@app.on_message(filters.command("wel") & filters.group)
async def welcome_status(_, message: Message):
    rec = await _get(message.chat.id)
    if rec.get("text"):
        extra = " + ɪᴍᴀɢᴇ" if rec.get("photo") else ""
        return await message.reply_text(
            f"**ᴄᴜsᴛᴏᴍ ᴡᴇʟᴄᴏᴍᴇ ᴀᴄᴛɪᴠᴇ ✅**{extra}\n"
            "**ᴘʀᴇᴠɪᴇᴡ:** /welmsg • **ʀᴇsᴇᴛ:** /delwel")
    return await message.reply_text(
        "**ɴᴏ ᴄᴜsᴛᴏᴍ ᴡᴇʟᴄᴏᴍᴇ — ᴅᴇғᴀᴜʟᴛ ᴀᴜᴛᴏ ᴡᴇʟᴄᴏᴍᴇ ʀᴜɴɴɪɴɢ.**\n"
        "**sᴇᴛ:** /setwel <ᴛᴇxᴛ>")

# ────────────────── auto delivery ──────────────────

@app.on_message(filters.new_chat_members & filters.group, group=10)
async def deliver_custom_welcome(_, message: Message):
    rec = await _get(message.chat.id)
    if not rec.get("text"):
        return
    count = getattr(message.chat, "members_count", None) or "?"
    chat = message.chat.title or "ᴍʏ ɢʀᴏᴜᴘ"
    for member in message.new_chat_members:
        if not member or member.id == app.id:
            continue
        mention = (f"@{member.username}" if getattr(member, "username", None)
                   else (member.first_name or "ᴍᴇᴍʙᴇʀ"))
        uname = f"@{member.username}" if getattr(member, "username", None) else "—"
        body = _fmt(rec["text"], mention=mention, uid=member.id,
                    uname=uname, count=count, chat=chat)
        out = FRAME.format(chat=chat, body=body)
        await _send(message.chat.id, out, rec.get("photo"), message.chat.id)

# ────────────────── callbacks ──────────────────

@app.on_callback_query(filters.regex(r"^welstats:(-?\d+)$"))
async def welcome_stats(_, c):
    cid = int(c.data.split(":", 1)[1])
    try:
        chat = await app.get_chat(cid)
        await c.answer(f"ᴍᴇᴍʙᴇʀs: {getattr(chat, 'members_count', '?')}",
                       show_alert=True)
    except Exception:
        await c.answer("ᴀᴜᴛʜᴏʀɪsᴀᴛɪᴏɴ ғᴀɪʟᴇᴅ", show_alert=True)


@app.on_callback_query(filters.regex(r"^welbot:(-?\d+)$"))
async def welcome_botlink(_, c):
    await c.answer(f"ᴏғғɪᴄɪᴀʟ: @{app.username}", show_alert=True)

# ═══════════════════════════════════════════════════════════
# 🌺 RhythmSync 🌺
# github.com/SunloMusicOfficial/RhythmSync
# ═══════════════════════════════════════════════════════════
