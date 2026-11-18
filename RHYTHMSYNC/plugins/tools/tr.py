# ═══════════════════════════════════════════════════════════
#        🌺 RhythmSync 🌺
#   GɪᴛHᴜʙ : github.com/SunloMusicOfficial/RhythmSync
#   Dᴇᴠʟᴏᴘᴇʀ : @YO_UR_OFFICIAL_CRUSH | Telegram
# ═══════════════════════════════════════════════════════════

from pyrogram import filters
from pyrogram.types import Message
from RHYTHMSYNC import app
from gpytranslate import Translator

translator = Translator()


@app.on_message(filters.command("tr"))
async def translate(_, message: Message):
    reply = message.reply_to_message

    if not reply or not (reply.text or reply.caption):
        return await message.reply_text("📌 ʀᴇᴘʟʏ ᴛᴏ ᴀ ᴛᴇxᴛ ᴏʀ ᴄᴀᴘᴛɪᴏɴ ᴛᴏ ᴛʀᴀɴsʟᴀᴛᴇ.")

    content = reply.text or reply.caption

    try:
        arg = message.text.split(maxsplit=1)[1].lower()
        if "//" in arg:
            source_lang, target_lang = arg.split("//")
        else:
            detected = await translator.detect(content)
            source_lang = detected.lang  # ✅ extract the actual language code
            target_lang = arg
    except IndexError:
        detected = await translator.detect(content)
        source_lang = detected.lang  # ✅ extract the actual language code
        target_lang = "en"

    try:
        result = await translator(content, sourcelang=source_lang, targetlang=target_lang)
        await message.reply_text(
            f"🌐 **ᴛʀᴀɴsʟᴀᴛᴇᴅ:** `{source_lang}` ➜ `{target_lang}`\n\n"
            f"`{result.text}`"
        )
    except Exception as e:
        await message.reply_text(f"❌ **ᴛʀᴀɴsʟᴀᴛɪᴏɴ ꜰᴀɪʟᴇᴅ:** `{str(e)}`")

# ═══════════════════════════════════════════════════════════
#         🌺 RhythmSync 🌺
#   github.com/SunloMusicOfficial/RhythmSync
# ═══════════════════════════════════════════════════════════
