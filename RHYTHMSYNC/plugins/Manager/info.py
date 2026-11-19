# ═══════════════════════════════════════════════════════════
#        🌺 RhythmSync 🌺
#   GɪᴛHᴜʙ : github.com/SunloMusicOfficial/RhythmSync
#   Dᴇᴠʟᴏᴘᴇʀ : @YO_UR_OFFICIAL_CRUSH | Telegram
# ═══════════════════════════════════════════════════════════
#  /info | /whois | /userinfo  —  Premium user intelligence card
# ═══════════════════════════════════════════════════════════

import html
from datetime import datetime, timezone

from pyrogram import enums, filters
from pyrogram.errors import RPCError
from pyrogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from RHYTHMSYNC import app

MAX_CAPTION = 1024
MAX_TEXT = 4096
HTML = enums.ParseMode.HTML

# ─── Status / member lookup tables ────────────────────────────────────────

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


# ─── Small helpers ────────────────────────────────────────────────────────

def _esc(value) -> str:
    """HTML-escape anything that may contain < > & (names, bios, titles)."""
    if value is None:
        return "—"
    return html.escape(str(value), quote=False)


def _fmt_dt(dt) -> str:
    if not isinstance(dt, datetime):
        return "—"
    return dt.strftime("%d %b %Y, %H:%M UTC")


def _human_delta(dt) -> str:
    """Turn a past datetime into '2 yrs 3 mo ago' style text."""
    if not isinstance(dt, datetime):
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    seconds = int((datetime.now(timezone.utc) - dt).total_seconds())
    if seconds < 0:
        return "in the future"
    if seconds < 60:
        return "just now"

    units = [
        (31536000, "yr"), (2592000, "mo"), (604800, "wk"),
        (86400, "d"), (3600, "h"), (60, "m"),
    ]
    parts = []
    for size, label in units:
        qty, seconds = divmod(seconds, size)
        if qty:
            parts.append(f"{qty}{label}")
        if len(parts) == 2:
            break
    return " ".join(parts) + " ago"


def _parse_target(raw: str) -> str:
    """Accept @name, name, t.me/name, tg://user?id=123, or a plain ID."""
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
    """Await something that is allowed to fail (privacy, flood, perms)."""
    try:
        return await coro
    except Exception:
        return default


# ─── Profile photo ────────────────────────────────────────────────────────

async def _fetch_photo(client, user):
    photo = getattr(user, "photo", None)
    if not photo:
        return None
    try:
        data = await client.download_media(photo.big_file_id, in_memory=True)
        if data is None:
            return None
        return data.getvalue() if hasattr(data, "getvalue") else data
    except Exception:
        return None


# ─── The card builder ─────────────────────────────────────────────────────

async def build_card(client, user, chat) -> str:
    name = _esc(user.first_name) + (
        f" {_esc(user.last_name)}" if user.last_name else ""
    )
    username = f"@{_esc(user.username)}" if user.username else "—"

    # ── badges ───────────────────────────────────────────────────────────
    active = [label for attr, label in BADGES if getattr(user, attr, False)]
    badges = " • ".join(active) if active else "—"

    # ── presence ─────────────────────────────────────────────────────────
    status = getattr(user, "status", None)
    status_key = getattr(status, "name", None) if status else None
    presence = STATUS_ICONS.get(status_key, "🔒 Hidden")
    seen_dt = getattr(status, "date", None) if status else None
    if seen_dt:
        presence += f" • {_human_delta(seen_dt)}"

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

    # ── bio (only exposed for some accounts) ─────────────────────────────
    bio = getattr(user, "bio", None)
    if bio:
        rows += ["", "<b>❖ ʙɪᴏ</b>", f"<blockquote>{_esc(bio)}</blockquote>"]

    # ── membership in the current chat ───────────────────────────────────
    if chat is not None and getattr(chat, "type", None) in (
        enums.ChatType.GROUP,
        enums.ChatType.SUPERGROUP,
    ):
        member = await _safe(
            client.get_chat_member(chat.id, user.id), default=None
        )
        if member:
            m_key = getattr(member.status, "name", None)
            rows += [
                "",
                "<blockquote>🏷 <b>ᴄʜᴀᴛ ᴄᴏɴᴛᴇxᴛ</b></blockquote>",
                f"<b>❖ ʀᴀɴᴋ</b> : {MEMBER_LABELS.get(m_key, _esc(m_key))}",
            ]
            title = getattr(member, "custom_title", None)
            if title:
                rows.append(f"<b>❖ ᴛɪᴛʟᴇ</b> : {_esc(title)}")
            joined = getattr(member, "joined_date", None)
            if joined:
                rows.append(
                    f"<b>❖ ᴊᴏɪɴᴇᴅ</b> : {_fmt_dt(joined)} "
                    f"({_human_delta(joined)})"
                )
            priv = getattr(member, "privileges", None)
            if priv and m_key == "ADMINISTRATOR":
                rights = [
                    key.replace("can_", "").replace("_", " ")
                    for key in (
                        "can_manage_chat", "can_delete_messages",
                        "can_restrict_members", "can_promote_members",
                        "can_pin_messages", "can_invite_users",
                    )
                    if getattr(priv, key, False)
                ]
                if rights:
                    rows.append(f"<b>❖ ᴘᴇʀᴍs</b> : {', '.join(rights)}")

    # ── common chats ─────────────────────────────────────────────────────
    common = await _safe(client.get_common_chats(user.id), default=None)
    if common:
        rows += [
            "",
            f"<blockquote>🤝 <b>ᴄᴏᴍᴍᴏɴ ᴄʜᴀᴛs</b> — {len(common)}</blockquote>",
        ]
        for item in common[:5]:
            label = _esc(getattr(item, "title", None) or item.id)
            if getattr(item, "username", None):
                rows.append(
                    f' • <a href="https://t.me/{item.username}">{label}</a>'
                )
            else:
                rows.append(f" • {label}")
        if len(common) > 5:
            rows.append(f" • <i>+{len(common) - 5} more…</i>")

    # ── footer ───────────────────────────────────────────────────────────
    rows += [
        "",
        f"<i>⚡ queried at {_fmt_dt(datetime.now(timezone.utc)).split(',')[1].strip()}</i>",
    ]
    return "\n".join(rows)


def build_keyboard(user) -> InlineKeyboardMarkup:
    row1 = [
        InlineKeyboardButton("🔄 ʀᴇꜰʀᴇsʜ", callback_data=f"ui|rf|{user.id}"),
        InlineKeyboardButton("📋 ᴄᴏᴘʏ ɪᴅ", callback_data=f"ui|cp|{user.id}"),
    ]
    rows = [row1]
    if user.username:
        rows.append([
            InlineKeyboardButton(
                "👤 ᴏᴘᴇɴ ᴘʀᴏꜰɪʟᴇ", url=f"https://t.me/{user.username}"
            )
        ])
    rows.append([InlineKeyboardButton("✖️ ᴄʟᴏsᴇ", callback_data="ui|cl")])
    return InlineKeyboardMarkup(rows)


# ─── Sending (photo + caption limit aware) ────────────────────────────────

async def send_card(client, message: Message, user, chat, as_reply=True):
    text = await build_card(client, user, chat)
    keyboard = build_keyboard(user)
    photo = await _fetch_photo(client, user)
    reply = message.reply_photo if as_reply else message.reply_photo

    if photo:
        if len(text) <= MAX_CAPTION:
            return await reply(
                photo, caption=text, parse_mode=HTML, reply_markup=keyboard
            )
        # Caption limit exceeded → photo first, details second
        await reply(
            photo,
            caption=f"👤 <b>{_esc(user.first_name)}</b> • "
                    f"<code>{user.id}</code>",
            parse_mode=HTML,
        )
        return await message.reply_text(
            text[:MAX_TEXT], parse_mode=HTML, reply_markup=keyboard,
            disable_web_page_preview=True,
        )

    return await message.reply_text(
        text[:MAX_TEXT], parse_mode=HTML, reply_markup=keyboard,
        disable_web_page_preview=True,
    )


# ─── /info | /whois | /userinfo ───────────────────────────────────────────

@app.on_message(filters.command(["info", "whois", "userinfo"]))
async def info_cmd(client, message: Message):
    await message.reply_chat_action(enums.ChatAction.TYPING)

    try:
        reply = message.reply_to_message

        # 1) reply → use that message's author
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

        # 2) argument → resolve @user / id / link
        elif len(message.command) > 1:
            raw = _parse_target(" ".join(message.command[1:]))
            try:
                target = await client.get_users(
                    int(raw) if raw.isdigit() else raw
                )
            except (RPCError, ValueError):
                return await message.reply_text(
                    "❌ <b>User not found.</b>\n"
                    "<i>Try a numeric ID, a @username, or reply to a message.</i>",
                    parse_mode=HTML,
                )

        # 3) nothing → yourself
        else:
            target = message.from_user
            if target is None:
                return await message.reply_text(
                    "❌ Couldn't identify the sender.", parse_mode=HTML
                )

        await send_card(client, message, target, message.chat)

    except Exception as e:
        # Surface the real reason instead of dying silently
        await message.reply_text(
            f"❌ <b>Info failed</b>\n<code>{type(e).__name__}: {_esc(e)}</code>",
            parse_mode=HTML,
        )


# ─── Callback buttons ─────────────────────────────────────────────────────

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
            user = await _safe(client.get_users(user_id), default=None)
            if user is None:
                return await cb.answer("User no longer reachable.", show_alert=True)

            text = await build_card(client, user, cb.message.chat)
            keyboard = build_keyboard(user)

            try:
                if cb.message.caption is not None:
                    await cb.message.edit_caption(
                        text[:MAX_CAPTION], parse_mode=HTML, reply_markup=keyboard
                    )
                else:
                    await cb.message.edit_text(
                        text[:MAX_TEXT], parse_mode=HTML,
                        reply_markup=keyboard,
                        disable_web_page_preview=True,
                    )
            except Exception:
                await cb.answer("Nothing changed.", show_alert=False)

    except Exception as e:
        await cb.answer(f"Error: {type(e).__name__}", show_alert=True)


# ═══════════════════════════════════════════════════════════
#         🌺 RhythmSync 🌺
#   github.com/SunloMusicOfficial/RhythmSync
# ═══════════════════════════════════════════════════════════
