# ═══════════════════════════════════════════════════════════
#        🌺 RhythmSync 🌺
#   GɪᴛHᴜʙ : github.com/SunloMusicOfficial/RhythmSync
#   Dᴇᴠʟᴏᴘᴇʀ : @YO_UR_OFFICIAL_CRUSH | Telegram
# ═══════════════════════════════════════════════════════════

# ── Pyrogram / PyTgCalls Compatibility Layer ────────────────
import pyrogram.errors

if not hasattr(pyrogram.errors, "GroupcallForbidden"):
    _found = False
    for _sub in ("bad_request_400", "forbidden_403"):
        try:
            import importlib
            _mod = importlib.import_module(f"pyrogram.errors.exceptions.{_sub}")
            if hasattr(_mod, "GroupcallForbidden"):
                setattr(pyrogram.errors, "GroupcallForbidden", getattr(_mod, "GroupcallForbidden"))
                _found = True
                break
        except Exception:
            pass
    if not _found:
        class GroupcallForbidden(pyrogram.errors.RPCError):
            """The group call is forbidden."""
            ID = "GROUPCALL_FORBIDDEN"
        setattr(pyrogram.errors, "GroupcallForbidden", GroupcallForbidden)

from RHYTHMSYNC.core.bot import SAKIL
from RHYTHMSYNC.core.dir import dirr
from RHYTHMSYNC.core.git import git
from RHYTHMSYNC.core.userbot import Userbot
from RHYTHMSYNC.misc import dbb, heroku

from .logging import LOGGER

dirr()
git()
dbb()
heroku()

app = SAKIL()
userbot = Userbot()

# ── Kurigram mention fix ──────────────────────────────────────
# Kurigram ka User.mention bina quotes ka anchor banata hai:
#     <a href=tg://user?id=123>Name</a>
# Telegram Bot API usse parse nahi kar pata ("Unexpected end of name
# token") → Bot API path fail → buttons colorless fallback me jaate
# hain. Isliye mention ko QUOTED anchor ke saath override karte hain.
try:
    from pyrogram.types import User as _KurigramUser

    def _quoted_mention(self):
        name = self.first_name or "Deleted Account"
        return f'<a href="tg://user?id={self.id}">{name}</a>'

    _KurigramUser.mention = property(_quoted_mention)
    LOGGER("RHYTHMSYNC").info("✔ mention HTML quote fix applied")
except Exception as _e:
    LOGGER("RHYTHMSYNC").warning(f"mention fix failed: {_e}")


from .platforms import *

Apple = AppleAPI()
Carbon = CarbonAPI()
SoundCloud = SoundAPI()
Spotify = SpotifyAPI()
Resso = RessoAPI()
Telegram = TeleAPI()
YouTube = YouTubeAPI()

# ═══════════════════════════════════════════════════════════
#         🌺 RhythmSync 🌺
#   github.com/SunloMusicOfficial/RhythmSync
# ═══════════════════════════════════════════════════════════
