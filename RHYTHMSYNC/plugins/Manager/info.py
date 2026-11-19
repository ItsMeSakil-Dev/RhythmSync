# ═══════════════════════════════════════════════════════════
#        🌺 RhythmSync 🌺
#   GɪᴛHᴜʙ : github.com/SunloMusicOfficial/RhythmSync
#   Dᴇᴠʟᴏᴘᴇʀ : @YO_UR_OFFICIAL_CRUSH | Telegram
# ═══════════════════════════════════════════════════════════
#  /info | /whois | /userinfo — Premium card + rich-coloured buttons
#  Colour rendering delegated 100% to utils/colored_buttons.py
#  (raw Bot API bridge — Kurigram itself can't send the `style` field)
# ═══════════════════════════════════════════════════════════

import html
from datetime import datetime, timezone

from pyrogram import enums, filters
from pyrogram.errors import RPCError
from pyrogram.types import CallbackQuery, Message

from RHYTHMSYNC import app
from RHYTHMSYNC.utils.colored_buttons import (
    styled_button,
    smart_send_photo,
    smart_send_message,
    smart_edit_message_text,
    smart_edit_message_caption,
)

MAX_CAPTION = 1024
MAX_TEXT = 4096
HTML = enums.ParseMode.HTML

STATUS_ICONS = {
    "ONLINE": "🟢 Online",
    "OFFLINE": "⚪️ Offline",
    "RECENTLY": "🟡 Recently",
    "LAST_WEEK": "🟠 Last week",
    "LAST_MONTH": "🔴 Last month",
    "LONG_AGO": "⚫️ Long ago",
}

MEMBER_LABELS = {
    "OWNER": "👑 Owner",
    "ADMINISTRATOR": "🛡 Administrator",
    "MEMBER": "👤 Member",
    "RESTRICTED": "🚫 Restricted",
    "LEFT": "🚪 Left",
    "BANNED": "⛔️ Banned",
}

BADGES = [
    ("is_verified", "✅ Verified"),
    ("is_premium", "⭐️ Premium"),
    ("is_bot", "🤖 Bot"),
    ("is_support", "🛡 Support"),
    ("is_scam", "⚠️ Scam"),
    ("is_fake", "🎭 Fake"),
    ("is_deleted", "🗑 Deleted"),
]


# ─── Helpers ──────────────────────────────────────────────────────────────

def _esc(value) -> str:
    if value is None:
        return "—"
    return html.escape(str(value), quote=False)


def _fmt_dt(dt) -> str:
    if not isinstance(dt, datetime):
        return "—"
    return dt.strftime("%d %b %Y, %H:%M UTC")


def _human_delta(dt) -> str:
    if not isinstance(dt, datetime):
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    seconds = int((datetime.now(timezone.utc) - dt).total_seconds())
    if seconds < 0:
        return "in the future"
    if seconds < 60:
        return "just now"
    units = [(31536000, "yr"), (2592000, "mo"), (604800, "wk"),
             (86400, "d"), (3600, "h"), (60, "m")]
    parts = []
    for size, label in units:
        qty, seconds = divmod(seconds, size)
        if qty:
            parts.append(f"{qty}{label}")
        if len(parts) == 2:
            break
    return " ".join(parts) + " ago"


def _parse_target(raw: str) -> str:
    target = (raw or "").strip()
    for prefix in ("https://", "http://"):
        if target.startswith(prefix):
            target = target[len(prefix):]
    if "t.me/" in target:
        target = target.split("t.me/", 1)[1]
    if "tg://user?id=" in target:
        target = target.split("tg://user?id=", 1)[1]
    return target.split("?", 1)[0].split("/", 1)[0].lstrip("@").strip()


async def _safe(coro, default=None):
    try:
        return await coro
    except Exception:
        return default


async def _fetch_photo(client, user) -> bytes | None:
    photo = getattr(user, "photo", None)
    if not photo:
        return None
    try:
        buf = await client.download_media(photo.big_file_id, in_memory=True)
        return buf.getvalue() if buf else None
    except Exception:
        return None


# ─── Card text builder ─────────────────────────────────────────────────────

async def build_card(client, user, chat) -> str:
    name = _esc(user.first_name) + (
        f" {_esc(user.last_name)}" if user.last_name else ""
    )
    username = f"@{_esc(user.username)}" if user.username else "—"
    badges = " • ".join(l for a, l in BADGES if getattr(user, a, False)) or "—"

    status = getattr(user, "status", None)
    key = getattr(status, "name", None) if status else None
    presence = STATUS_ICONS.get(key, "🔒 Hidden")
    seen = getattr(status, "date", None) if status else None
    if seen:
        presence += f" • {_human_delta(seen)}"

    rows = [
        "<blockquote>👤 <b>ᴜsᴇʀ ɪɴꜰᴏʀᴍᴀᴛɪᴏɴ ᴄᴀʀᴅ</b></blockquote>",
        "",
        f"<b>❖ ɴᴀᴍᴇ</b> : {name}",
        f"<b>❖ ᴜsᴇʀɴᴀᴍᴇ</b> : {username}",
        f"<b>❖ ᴜsᴇʀ ɪᴅ</b> : <code>{user.id}</code>",
        f"<b>❖ ᴍᴇɴᴛɪᴏɴ</b> : {user.mention}",
        f"<b>❖ ᴅᴄ</b> : {getattr(user, 'dc_id', None) or '—'}",
        f"<b>❖ ʟᴀɴɢᴜᴀɢᴇ</b> : {_esc(getattr(user, 'language_code', None))}",
        f"<b>❖ sᴛᴀᴛᴜs</b> : {presence}",
        f"<b>❖ ʙᴀᴅɢᴇs</b> : {badges}",
    ]

    bio = getattr(user, "bio", None)
    if bio:
        rows += ["", "<b>❖ ʙɪᴏ</b>", f"<blockquote>{_esc(bio)}</blockquote>"]

    if chat is not None and getattr(chat, "type", None) in (
        enums.ChatType.GROUP, enums.ChatType.SUPERGROUP,
    ):
        member = await _safe(client.get_chat_member(chat.id, user.id))
        if member:
            m_key = getattr(member.status, "name", None)
            rows += ["", "<blockquote>🏷 <b>ᴄʜᴀᴛ ᴄᴏɴᴛᴇxᴛ</b></blockquote>",
                     f"<b>❖ ʀᴀɴᴋ</b> : {MEMBER_LABELS.get(m_key, _esc(m_key))}"]
            title = getattr(member, "custom_title", None)
            if title:
                rows.append(f"<b>❖ ᴛɪᴛʟᴇ</b> : {_esc(title)}")
            joined = getattr(member, "joined_date", None)
            if joined:
                rows.append(f"<b>❖ ᴊᴏɪɴᴇᴅ</b> : {_fmt_dt(joined)} "
                            f"({_human_delta(joined)})")
            priv = getattr(member, "privileges", None)
            if priv and m_key == "ADMINISTRATOR":
                rights = [k.replace("can_", "").replace("_", " ") for k in (
                    "can_manage_chat", "can_delete_messages",
                    "can_restrict_members", "can_promote_members",
                    "can_pin_messages", "can_invite_users",
                ) if getattr(priv, k, False)]
                if rights:
                    rows.append(f"<b>❖ ᴘᴇʀᴍs</b> : {', '.join(rights)}")

    common = await _safe(client.get_common_chats(user.id))
    if common:
        rows += ["", f"<blockquote>🤝 <b>ᴄᴏᴍᴍᴏɴ ᴄʜᴀᴛs</b> — {len(common)}</blockquote>"]
        for item in common[:5]:
            label = _esc(getattr(item, "title", None) or item.id)
            if getattr(item, "username", None):
                rows.append(f' • <a href="https://t.me/{item.username}">{label}</a>')
            else:
                rows.append(f" • {label}")
        if len(common) > 5:
            rows.append(f" • <i>+{len(common) - 5} more…</i>")

    rows += ["", f"<i>⚡ queried at "
                 f"{_fmt_dt(datetime.now(timezone.utc)).split(',')[1].strip()}</i>"]
    return "\n".join(rows)


# ─── Coloured keyboard (uses project's own helper, NOT raw Pyrogram) ───────

def build_keyboard(user):
    """
    Returns a list-of-rows of `styled_button(...)` objects.
    `style`: "primary" = blue · "success" = green · "danger" = red.
    """
    row1 = [
        styled_button("🔄 ʀᴇꜰʀᴇsʜ", callback_data=f"ui|rf|{user.id}", style="primary"),
        styled_button("📋 ᴄᴏᴘʏ ɪᴅ", callback_data=f"ui|cp|{user.id}", style="primary"),
    ]
    rows = [row1]
    if user.username:
        rows.append([
            styled_button(
                "👤 ᴏᴘᴇɴ ᴘʀᴏꜰɪʟᴇ",
                url=f"https://t.me/{user.username}",
                style="success",
            )
        ])
    rows.append([styled_button("✖️ ᴄʟᴏsᴇ", callback_data="ui|cl", style="danger")])
    return rows


# ─── Sending (delegated to smart_send_*) ───────────────────────────────────

async def send_card(client, message: Message, user, chat):
    text = await build_card(client, user, chat)
    buttons = build_keyboard(user)
    photo = await _fetch_photo(client, user)

    if photo and len(text) <= MAX_CAPTION:
        sent = await smart_send_photo(
            message,
            photo=photo,
            caption=text,
            parse_mode="HTML",
            buttons=buttons,
        )
        if sent:
            return

    if photo:
        await smart_send_photo(
            message,
            photo=photo,
            caption=f"👤 <b>{_esc(user.first_name)}</b> • <code>{user.id}</code>",
            parse_mode="HTML",
        )

    await smart_send_message(
        message,
        text=text[:MAX_TEXT],
        parse_mode="HTML",
        buttons=buttons,
    )


# ─── /info | /whois | /userinfo ───────────────────────────────────────────

@app.on_message(filters.command(["info", "whois", "userinfo"]))
async def info_cmd(client, message: Message):
    await message.reply_chat_action(enums.ChatAction.TYPING)
    try:
        reply = message.reply_to_message

        if reply:
            target = reply.from_user or message.from_user
            if target is None:
                sender = reply.sender_chat
                return await message.reply_text(
                    "<b>❖ sᴇɴᴅᴇʀ</b>\n"
                    f"<b>❖ ᴛʏᴘᴇ</b> : Channel / Anonymous admin\n"
                    f"<b>❖ ɴᴀᴍᴇ</b> : {_esc(getattr(sender, 'title', None))}\n"
                    f"<b>❖ ɪᴅ</b> : <code>{getattr(sender, 'id', '—')}</code>",
                    parse_mode=HTML,
                )

        elif len(message.command) > 1:
            raw = _parse_target(" ".join(message.command[1:]))
            try:
                target = await client.get_users(int(raw) if raw.isdigit() else raw)
            except (RPCError, ValueError):
                return await message.reply_text(
                    "❌ <b>User not found.</b>\n"
                    "<i>Try a numeric ID, a @username, or reply to a message.</i>",
                    parse_mode=HTML,
                )

        else:
            target = message.from_user
            if target is None:
                return await message.reply_text("❌ Couldn't identify the sender.")

        await send_card(client, message, target, message.chat)

    except Exception as e:
        await message.reply_text(
            f"❌ <b>Info failed</b>\n<code>{type(e).__name__}: {_esc(e)}</code>",
            parse_mode=HTML,
        )


# ─── Callbacks ─────────────────────────────────────────────────────────────

@app.on_callback_query(filters.regex(r"^ui\|"))
async def info_callback(client, cb: CallbackQuery):
    try:
        parts = cb.data.split("|")
        action = parts[1]

        if action == "cl":
            await cb.answer("Closed")
            return await cb.message.delete()

        user_id = int(parts[2])

        if action == "cp":
            return await cb.answer(f"🆔 {user_id}", show_alert=True)

        if action == "rf":
            await cb.answer("Refreshing…")
            user = await _safe(client.get_users(user_id))
            if user is None:
                return await cb.answer("User no longer reachable.", show_alert=True)

            text = await build_card(client, user, cb.message.chat)
            buttons = build_keyboard(user)

            if cb.message.caption is not None:
                await smart_edit_message_caption(
                    cb.message, caption=text[:MAX_CAPTION],
                    parse_mode="HTML", buttons=buttons,
                )
            else:
                await smart_edit_message_text(
                    cb.message, text=text[:MAX_TEXT],
                    parse_mode="HTML", buttons=buttons,
                )

    except Exception as e:
        await cb.answer(f"Error: {type(e).__name__}", show_alert=True)


# ═══════════════════════════════════════════════════════════
#         🌺 RhythmSync 🌺
#   github.com/SunloMusicOfficial/RhythmSync
# ═══════════════════════════════════════════════════════════
