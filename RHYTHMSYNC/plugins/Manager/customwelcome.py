# ═══════════════════════════════════════════════════════════
# 🌺 RhythmSync 🌺
# PREMIUM CUSTOM WELCOME SYSTEM
# Manually set welcome messages per group
# ═══════════════════════════════════════════════════════════

from pyrogram import filters
from pyrogram.enums import ChatType
from pyrogram.types import Message

from RHYTHMSYNC import app
from RHYTHMSYNC.utils.admin_filters import admin_filter
from RHYTHMSYNC.utils.colored_buttons import (
    styled_button,
    send_message_colored,
    send_photo_colored,
)
from RHYTHMSYNC.mongo import db          # ← import error aaye to apne DB wali line laga do

COL = db.custom_welcome

# ────────────────── helpers ──────────────────

async def _get(cid: int) -> dict:
    return await COL.find_one({"chat_id": cid}) or {}

async def _save(cid: int, doc: dict) -> None:
    await COL.update_one({"chat_id": cid}, {"$set": doc}, upsert=True)

async def _clear(cid: int) -> None:
    await COL.delete_one({"chat_id": cid})

def _is_group(m: Message) -> bool:
    return m.chat.type not in (ChatType.PRIVATE, ChatType.BOT)

DEFAULT_BODY = (
    "╔═══════════════════╗\n"
    "║ 👤 Nᴀᴍᴇ : {mention}\n"
    "║ 🆔 Iᴅ : {uid}\n"
    "║ 🔗 Usᴇʀɴᴀᴍᴇ : @{{uname}}\n"
    "║ 🌐 Tᴏᴛᴀʟ Mᴇᴍʙᴇʀs : {count}\n"
    "╚═══════════════════╝"
)

FRAME = "✨❄─────✧ ᴡᴇʟᴄᴏᴍᴇ ✧─────❄✨\n💫 {chat} 💫\n\n{body}"

def _fmt(text: str, *, mention, uid, uname, count) -> str:
    return (text
            .replace("{mention}", mention)
            .replace("{uid}", str(uid))
            .replace("{uname}", uname)
            .replace("{count}", count))

# ────────────────── commands ──────────────────

@app.on_message(filters.command("setwel") & admin_filter & filters.group)
async def set_welcome_text(_, message: Message):
    if len(message.command) < 2:
        return await message.reply_text(
            "**ᴜsᴀɢᴇ:** /setwel <ᴛᴇxᴛ>\n\n"
            "Pʟᴀᴄᴇʜᴏʟᴅᴇʀs:\n"
            "{mention} • {uid} • {uname} • {count}"
        )
    text = message.text.split(None, 1)[1]
    await _save(message.chat.id, {"text": text, "photo": None})
    return await message.reply_text(f"**ᴄᴜsᴛᴏᴍ ᴡᴇʟᴄᴏᴍᴇ sᴇᴛ! ✅**\n\n{text}")


@app.on_message(filters.command("setwelphoto") & admin_filter & filters.group)
async def set_welcome_photo(_, message: Message):
    if not message.reply_to_message or not message.reply_to_message.photo:
        return await message.reply_text("**ʀᴇᴘʟʏ ᴛᴏ ᴀ ᴘʜᴏᴛᴏ ᴛᴏ sᴇᴛ ɪᴛ ᴀs ᴡᴇʟᴄᴏᴍᴇ ɪᴍᴀɢᴇ.**")
    rec = await _get(message.chat.id)
    text = rec.get("text") or DEFAULT_BODY
    await _save(message.chat.id, {"text": text, "photo": message.reply_to_message.photo.file_id})
    return await message.reply_text("**ᴡᴇʟᴄᴏᴍᴇ ɪᴍᴀɢᴇ sᴇᴛ! ✅**")


@app.on_message(filters.command("welmsg") & admin_filter & filters.group)
async def preview_welcome(_, message: Message):
    rec = await _get(message.chat.id)
    if not rec.get("text"):
        return await message.reply_text("**ɴᴏ ᴄᴜsᴛᴏᴍ ᴡᴇʟᴄᴏᴍᴇ sᴇᴛ — ᴅᴇғᴀᴜʟᴛ ɪs ᴀᴄᴛɪᴠᴇ.**")
    body = _fmt(rec["text"], mention="ᴍᴇᴍʙᴇʀ", uid="12345678",
                uname="user", count="120")
    out = FRAME.format(chat=message.chat.title, body=body)
    btns = [[styled_button("💎 ɢʀᴏᴜᴘ sᴛᴀᴛs", callback_data=f"welstats:{message.chat.id}", style="primary")]]
    res = await send_message_colored(message.chat.id, out, btns)
    if not res and rec.get("photo"):
        await send_photo_colored(message.chat.id, rec["photo"], out, btns)


@app.on_message(filters.command("delwel") & admin_filter & filters.group)
async def delete_welcome(_, message: Message):
    await _clear(message.chat.id)
    return await message.reply_text("**ᴄᴜsᴛᴏᴍ ᴡᴇʟᴄᴏᴍᴇ ʀᴇsᴇᴛ! ᴅᴇғᴀᴜʟᴛ ʙᴀᴄᴋ ✅**")


@app.on_message(filters.command("wel") & filters.group)
async def welcome_status(_, message: Message):
    rec = await _get(message.chat.id)
    status = "**ᴄᴜsᴛᴏᴍ ᴡᴇʟᴄᴏᴍᴇ ᴀᴄᴛɪᴠᴇ ✅**" if rec.get("text") else "**ᴅᴇғᴀᴜʟᴛ ᴀᴜᴛᴏ ᴡᴇʟᴄᴏᴍᴇ ᴀᴄᴛɪᴠᴇ**"
    return await message.reply_text(f"**ʟᴛ ʟɪɴᴋ** {status}")

# ────────────────── auto delivery ──────────────────

@app.on_message(filters.new_chat_members & filters.group, group=10)
async def deliver_custom_welcome(_, message: Message):
    rec = await _get(message.chat.id)
    if not rec.get("text"):
        return
    for member in message.new_chat_members:
        if not member or member.id == app.id:
            continue
        count = str(getattr(message.chat, "members_count", "") or "—")
        mention = getattr(member, "mention", member.first_name or "ᴍᴇᴍʙᴇʀ")
        uname = f"@{member.username}" if getattr(member, "username", None) else "—"
        body = _fmt(rec["text"], mention=mention, uid=member.id, uname=uname, count=count)
        out = FRAME.format(chat=message.chat.title, body=body)
        btns = [[
            styled_button("💎 ɢʀᴏᴜᴘ sᴛᴀᴛs", callback_data=f"welstats:{message.chat.id}", style="primary"),
            styled_button("⚡ ᴏғғɪᴄɪᴀʟ ʙᴏᴛ", url=f"https://t.me/{app.username}", style="success"),
        ]]
        res = await send_message_colored(message.chat.id, out, btns)
        if not res:
            if rec.get("photo"):
                await send_photo_colored(message.chat.id, rec["photo"], out, btns)
            else:
                await message.chat.send_text(out)


@app.on_callback_query(filters.regex(r"^welstats:(-?\d+)$"))
async def welcome_stats(_, c):
    cid = int(c.data.split(":")[1])
    try:
        chat = await app.get_chat(cid)
        n = getattr(chat, "members_count", "?")
        await c.answer(f"ᴍᴇᴍʙᴇʀs: {n} • ᴄʜᴀᴛ ɪᴅ: {cid}", show_alert=True)
    except Exception:
        await c.answer("ᴀᴜᴛʜᴏʀɪsᴀᴛɪᴏɴ ғᴀɪʟᴇᴅ", show_alert=True)

# ═══════════════════════════════════════════════════════════
