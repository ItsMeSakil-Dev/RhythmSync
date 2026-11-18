# ═══════════════════════════════════════════════════════════
#        🌺 RhythmSync 🌺
#   GɪᴛHᴜʙ : github.com/SunloMusicOfficial/RhythmSync
#   Dᴇᴠʟᴏᴘᴇʀ : @YO_UR_OFFICIAL_CRUSH | Telegram
# ═══════════════════════════════════════════════════════════

import time
import asyncio
import random
import logging

from pyrogram import enums, filters
from pyrogram.enums import ChatType
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from py_yt import VideosSearch

import config
from RHYTHMSYNC import app
from RHYTHMSYNC.misc import _boot_
from RHYTHMSYNC.plugins.sudo.sudoers import sudoers_list
from RHYTHMSYNC.utils.database import (
    add_served_chat,
    add_served_user,
    blacklisted_chats,
    get_lang,
    is_banned_user,
    is_on_off,
)
from RHYTHMSYNC.utils.decorators.language import LanguageStart
from RHYTHMSYNC.utils.formatters import get_readable_time
from RHYTHMSYNC.utils.inline.help import first_page
from RHYTHMSYNC.utils.inline.start import private_panel, start_panel
from RHYTHMSYNC.utils.colored_buttons import (
    buttons_to_inline_markup,
    smart_send_photo as send_photo_colored,
    styled_button,
)
from config import BANNED_USERS
from strings import get_string

LOGGER = logging.getLogger(__name__)

# 🔥 Love, Kiss, Cute stickers - alag alag type ke (all working)
STICKERS = [
    "CAACAgUAAxkBAAEQI1RlTLnRAy4h9lOS6jgS5FYsQoruOAAC1gMAAg6ryVcldUr_lhPexzME",
    "CAACAgQAAxkBAAMraaaBHm27-Wy2uQoptU3WZAAB6j3PAALEFQACIPCZUR1h3KoW6nItHgQ",
    "CAACAgQAAxkBAAMtaaaBKyjqLW8aBukB-vtOy-pUCxwAAoIOAAIF9AFSd_QCdbkZVqAeBA",
    "CAACAgQAAxkBAAMvaaaBNyAKbOtk05em_J8gQTmqotsAAhELAAIbGgABUuUNZ1V7LfMMHgQ",
    "CAACAgQAAxkBAAMxaaaBTZjH9A31Qdrb_xgKnrd4700AArgaAAJLO-hR8MN1DY1xe2ceBA",
    "CAACAgQAAxkBAAM5aaaB7A7JfXbtkO7b8ubX6_IjDdIAAhoVAAKRIKFRpathP0j9IIYeBA",
    "CAACAgUAAxkBAAEQI2FlTLpR8P8P8P8P8P8P8P8P8P8P8QACDwADyvhHAAHLh_6L3bL3bA",
    "CAACAgUAAxkBAAEQI2hlTLqJ8P8P8P8P8P8P8P8P8P8P8QACFgADyvhHAAHLh_6L3bL3bA",
    "CAACAgQAAxkBAAMzaaaBUYNDr2RENDvdHTkz5tg-lVcAAmkaAAIIeUlRllAUMDa5YOoeBA",
    "CAACAgQAAxkBAAM7aaaB-elXM9UEYY4OIo4eTCIbgigAAuUVAALryRlQRN37BBGYPgYeBA",
    "CAACAgQAAxkBAAM_aaaCCjmuL6EkqSBKpYbYzK3xKCcAAqYTAAK9jHlQ6vzt6mbH8-ceBA",
    "CAACAgUAAxkBAAEQI2BlTLpJ8P8P8P8P8P8P8P8P8P8P8QACDgADyvhHAAHLh_6L3bL3bA",
    "CAACAgUAAxkBAAEQI2VlTLpx8P8P8P8P8P8P8P8P8P8P8QACEwADyvhHAAHLh_6L3bL3bA",
]

REACTIONS = [
    "❤️", "🔥", "🥰", "😍", "😘", "👍", "👏", "🎉", "✨", "⭐️",
    "🌈", "🎵", "🎶", "💝", "💖", "💗", "💓", "💞", "💕", "💋",
]


# ───────────────────────────────────────────────────────────
#  ✅ FIX: single safe sender used EVERYWHERE.
#
#  Pehle har jagah `if not result: reply_photo(same_url)` tha —
#  yaani wahi broken URL dobara, bina try/except ke. Wahi crash
#  ki jad thi. Ab: photo fail ho to TEXT + same buttons.
#  Media pe depend nahi karta, isliye kabhi crash nahi hoga.
# ───────────────────────────────────────────────────────────
async def safe_send_photo(
    chat_id: int,
    photo,
    caption: str,
    markup=None,
    reply_to_message_id: int | None = None,
):
    """Photo bhejne ki koshish karo; fail ho to text+buttons pe fallback."""

    # ---- Attempt 1: colored photo sender ----
    if photo:
        try:
            result = await send_photo_colored(
                chat_id=chat_id,
                photo=photo,
                caption=caption,
                reply_markup=markup,
            )
            if result:
                return result
        except Exception as exc:
            # send_photo_colored apna error khud log karta hai, par agar
            # wo bhi raise kare to handler na mare
            LOGGER.warning("safe_send_photo: photo send failed: %s", exc)

    # ---- Attempt 2: text fallback (same buttons, no media) ----
    # Styled-button list ho to real InlineKeyboardMarkup mein convert karo.
    plain_markup = markup
    if markup is not None:
        try:
            plain_markup = buttons_to_inline_markup(markup)
        except Exception:
            plain_markup = markup  # already a markup? use as-is

    try:
        return await app.send_message(
            chat_id=chat_id,
            text=caption,
            parse_mode=enums.ParseMode.HTML,
            disable_web_page_preview=True,
            reply_markup=plain_markup,
            reply_to_message_id=reply_to_message_id,
        )
    except Exception as exc:
        # Aakhri safety net — handler kabhi na mare
        LOGGER.error("safe_send_photo: text fallback ALSO failed: %s", exc)
        return None


async def delete_message_after_delay(message: Message, delay: int):
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except Exception:
        pass


@app.on_message(filters.command(["start"]) & filters.private & ~BANNED_USERS)
@LanguageStart
async def start_pm(client, message: Message, _):
    try:
        await add_served_user(message.from_user.id)
    except Exception:
        pass

    # 🔥 PEHLE REACTION BHEJO - PRIVATE MEIN HAR BAAR
    try:
        await message.react(random.choice(REACTIONS))
    except Exception:
        try:
            await message.react("❤️")
        except Exception:
            pass

    # Make sure _ is a dictionary
    if isinstance(_, int):
        language = await get_lang(message.chat.id)
        _ = get_string(language)

    if len(message.text.split()) > 1:
        name = message.text.split(None, 1)[1]

        if name[0:4] == "help":
            keyboard = first_page(_)
            try:
                await message.reply_sticker(random.choice(STICKERS))
            except Exception:
                pass

            start_photo = random.choice(config.START_IMGS)
            # ✅ FIX: helper khud fallback karta hai, alag reply_photo nahi chahiye
            await safe_send_photo(
                chat_id=message.chat.id,
                photo=start_photo,
                caption=_["help_1"].format(config.SUPPORT_CHAT),
                markup=keyboard,
            )
            return

        if name[0:3] == "sud":
            await sudoers_list(client=client, message=message, _=_)
            if await is_on_off(2):
                username = (
                    f"@{message.from_user.username}"
                    if message.from_user.username
                    else "None"
                )
                return await app.send_message(
                    chat_id=config.LOGGER_ID,
                    text=f"{message.from_user.mention} ᴊᴜsᴛ sᴛᴀʀᴛᴇᴅ ᴛʜᴇ ʙᴏᴛ ᴛᴏ ᴄʜᴇᴄᴋ <b>sᴜᴅᴏʟɪsᴛ</b>.\n\n<b>ᴜsᴇʀ ɪᴅ :</b> <code>{message.from_user.id}</code>\n<b>ᴜsᴇʀɴᴀᴍᴇ :</b> {username}",
                )
            return

        if name[0:3] == "inf":
            m = await message.reply_text("🔎")
            query = (str(name)).replace("info_", "", 1)
            query = f"https://www.youtube.com/watch?v={query}"
            results = VideosSearch(query, limit=1)
            for result in (await results.next())["result"]:
                title = result["title"]
                duration = result["duration"]
                views = result["viewCount"]["short"]
                thumbnail = result["thumbnails"][0]["url"].split("?")[0]
                channellink = result["channel"]["link"]
                channel = result["channel"]["name"]
                link = result["link"]
                published = result["publishedTime"]

            bot_mention = f'<a href="tg://user?id={app.id}">{app.name}</a>'
            searched_text = _["start_6"].format(
                title, duration, views, published, channellink, channel, bot_mention
            )

            key = [
                [
                    styled_button(text=_["S_B_6"], url=link, style="primary"),
                    styled_button(text=_["S_B_4"], url=config.SUPPORT_CHAT, style="primary"),
                ],
            ]

            await m.delete()
            await safe_send_photo(
                chat_id=message.chat.id,
                photo=thumbnail,
                caption=searched_text,
                markup=key,
            )

            if await is_on_off(2):
                username = (
                    f"@{message.from_user.username}"
                    if message.from_user.username
                    else "None"
                )
                return await app.send_message(
                    chat_id=config.LOGGER_ID,
                    text=f"{message.from_user.mention} ᴊᴜsᴛ sᴛᴀʀᴛᴇᴅ ᴛʜᴇ ʙᴏᴛ ᴛᴏ ᴄʜᴇᴄᴋ <b>ᴛʀᴀᴄᴋ ɪɴғᴏʀᴍᴀᴛɪᴏɴ</b>.\n\n<b>ᴜsᴇʀ ɪᴅ :</b> <code>{message.from_user.id}</code>\n<b>ᴜsᴇʀɴᴀᴍᴇ :</b> {username}",
                )

    else:
        # Welcome animation
        try:
            user_mention = (
                f'<a href="tg://user?id={message.from_user.id}">'
                f"{message.from_user.first_name}</a>"
            )

            welcome_msgs = [
                "𝐖𝐞𝐥𝐜𝐨𝐦𝐞 𝐁𝐚𝐛𝐲 ꨄ︎ {}.. ❣️",
                "𝐖𝐞𝐥𝐜𝐨𝐦𝐞 𝐁𝐚𝐛𝐲 ꨄ {}..... 🥳",
                "𝐖𝐞𝐥𝐜𝐨𝐦𝐞 𝐁𝐚𝐛𝐲 ꨄ {}........ 💥",
                "𝐖𝐞𝐥𝐜𝐨𝐦𝐞 𝐁𝐚𝐛𝐲 ꨄ {}.......... 🤩",
                "𝐖𝐞𝐥𝐜𝐨𝐦𝐞 𝐁𝐚𝐛𝐲 ꨄ {}........... 💌",
                "𝐖𝐞𝐥𝐜𝐨𝐦𝐞 𝐁𝐚𝐛𝐲 ꨄ {}............. 💞",
            ]

            lol = await message.reply_text(
                welcome_msgs[0].format(user_mention),
                parse_mode=enums.ParseMode.HTML,
            )
            for msg in welcome_msgs[1:]:
                await asyncio.sleep(0.3)
                await lol.edit_text(
                    msg.format(user_mention),
                    parse_mode=enums.ParseMode.HTML,
                )
            await lol.delete()
        except Exception:
            pass

        # Profile photo try karo, warna random START_IMGS
        start_photo = None
        try:
            if message.from_user.photo:
                start_photo = await app.download_media(
                    message.from_user.photo.big_file_id
                )
        except Exception:
            pass

        if not start_photo:
            start_photo = random.choice(config.START_IMGS)

        out = await private_panel(_)

        user_mention = (
            f'<a href="tg://user?id={message.from_user.id}">'
            f"{message.from_user.first_name}</a>"
        )
        bot_mention = f'<a href="tg://user?id={app.id}">{app.name}</a>'
        caption = _["start_2"].format(user_mention, bot_mention)

        # ✅ FIX: purana `if not result: reply_photo(...)` hata diya —
        # helper already text fallback kar deta hai.
        await safe_send_photo(
            chat_id=message.chat.id,
            photo=start_photo,
            caption=caption,
            markup=out,
        )

        if await is_on_off(2):
            username = (
                f"@{message.from_user.username}"
                if message.from_user.username
                else "None"
            )
            await app.send_message(
                chat_id=config.LOGGER_ID,
                text=f"{message.from_user.mention} ᴊᴜsᴛ sᴛᴀʀᴛᴇᴅ ᴛʜᴇ ʙᴏᴛ.\n\n<b>ᴜsᴇʀ ɪᴅ :</b> <code>{message.from_user.id}</code>\n<b>ᴜsᴇʀɴᴀᴍᴇ :</b> {username}",
            )


@app.on_message(filters.command(["start"]) & filters.group & ~BANNED_USERS)
@LanguageStart
async def start_gp(client, message: Message, _):
    try:
        await message.react(random.choice(REACTIONS))
    except Exception:
        try:
            await message.react("❤️")
        except Exception:
            pass

    if isinstance(_, int):
        language = await get_lang(message.chat.id)
        _ = get_string(language)

    try:
        sticker_msg = await message.reply_sticker(random.choice(STICKERS))
        asyncio.create_task(delete_message_after_delay(sticker_msg, 3))
    except Exception:
        pass

    out = start_panel(_)
    uptime = int(time.time() - _boot_)

    start_photo = None
    try:
        if message.from_user and message.from_user.photo:
            start_photo = await app.download_media(
                message.from_user.photo.big_file_id
            )
    except Exception:
        pass

    if not start_photo:
        start_photo = random.choice(config.START_IMGS)

    bot_mention = f'<a href="tg://user?id={app.id}">{app.name}</a>'
    caption = _["start_1"].format(bot_mention, get_readable_time(uptime))

    # ✅ FIX: group mein bhi same safe helper (pehle bare await tha)
    await safe_send_photo(
        chat_id=message.chat.id,
        photo=start_photo,
        caption=caption,
        markup=out,
    )

    return await add_served_chat(message.chat.id)


@app.on_message(filters.new_chat_members, group=-1)
async def welcome(client, message: Message):
    for member in message.new_chat_members:
        try:
            language = await get_lang(message.chat.id)
            _ = get_string(language)

            if await is_banned_user(member.id):
                try:
                    await message.chat.ban_member(member.id)
                except Exception:
                    pass

            if member.id == app.id:
                if message.chat.type != ChatType.SUPERGROUP:
                    await message.reply_text(_["start_4"])
                    return await app.leave_chat(message.chat.id)

                if message.chat.id in await blacklisted_chats():
                    await message.reply_text(
                        _["start_5"].format(
                            app.mention,
                            f"https://t.me/{app.username}?start=sudolist",
                            config.SUPPORT_CHAT,
                        ),
                        disable_web_page_preview=True,
                    )
                    return await app.leave_chat(message.chat.id)

                try:
                    await message.reply_sticker(random.choice(STICKERS))
                except Exception:
                    pass

                out = start_panel(_)

                welcome_photo = None
                try:
                    if member and member.photo:
                        welcome_photo = await app.download_media(
                            member.photo.big_file_id
                        )
                except Exception:
                    pass

                if not welcome_photo:
                    welcome_photo = random.choice(config.START_IMGS)

                # ✅ FIX: same safe helper
                await safe_send_photo(
                    chat_id=message.chat.id,
                    photo=welcome_photo,
                    caption=_["start_3"].format(
                        member.first_name,
                        app.mention,
                        message.chat.title,
                        app.mention,
                    ),
                    markup=out,
                )

                await add_served_chat(message.chat.id)
                await message.stop_propagation()

        except Exception:
            pass
