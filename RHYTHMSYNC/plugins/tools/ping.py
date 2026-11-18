# ═══════════════════════════════════════════════════════════
#        🌺 RhythmSync 🌺
#   GɪᴛHᴜʙ : github.com/SunloMusicOfficial/RhythmSync
#   Dᴇᴠʟᴏᴘᴇʀ : @YO_UR_OFFICIAL_CRUSH | Telegram
# ═══════════════════════════════════════════════════════════

from datetime import datetime

from pyrogram import filters
from pyrogram.types import Message
from config import *
from RHYTHMSYNC import app
from RHYTHMSYNC.core.call import SAKIL
from RHYTHMSYNC.utils import bot_sys_stats
from RHYTHMSYNC.utils.decorators.language import language
from RHYTHMSYNC.utils.colored_buttons import buttons_to_inline_markup, smart_edit_message_text as edit_message_text_colored
from RHYTHMSYNC.utils.inline import supp_markup
from config import BANNED_USERS, PING_VID_URL


@app.on_message(filters.command("ping", prefixes=["/"]) & ~BANNED_USERS)
@language
async def ping_com(client, message: Message, _):
    start = datetime.now()
    response = await message.reply_video(
        video=PING_VID_URL,
        caption=_["ping_1"].format(app.mention),
    )
    pytgping = await SAKIL.ping()
    UP, CPU, RAM, DISK = await bot_sys_stats()
    resp = (datetime.now() - start).microseconds / 1000
    await edit_message_text_colored(
        chat_id=response.chat.id,
        message_id=response.id,
        text=_["ping_2"].format(resp, app.mention, UP, RAM, CPU, DISK, pytgping),
        reply_markup=supp_markup(_),
    )

# ═══════════════════════════════════════════════════════════
#         🌺 RhythmSync 🌺
#   github.com/SunloMusicOfficial/RhythmSync
# ═══════════════════════════════════════════════════════════
