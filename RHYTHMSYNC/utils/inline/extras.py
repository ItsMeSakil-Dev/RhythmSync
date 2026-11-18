# ═══════════════════════════════════════════════════════════
#        🌺 RhythmSync 🌺
#   GɪᴛHᴜʙ : github.com/SunloMusicOfficial/RhythmSync
#   Dᴇᴠʟᴏᴘᴇʀ : @YO_UR_OFFICIAL_CRUSH | Telegram
# ═══════════════════════════════════════════════════════════

from config import SUPPORT_CHAT
from RHYTHMSYNC.utils.colored_buttons import styled_button


def botplaylist_markup(_):
    buttons = [
        [
            styled_button(text=_["S_B_4"], url=SUPPORT_CHAT, style="primary"),
            styled_button(text=_["CLOSE_BUTTON"], callback_data="close", style="danger"),
        ],
    ]
    return buttons


def close_markup(_):
    return [
        [
            styled_button(text=_["CLOSE_BUTTON"], callback_data="close", style="danger"),
        ],
    ]


def supp_markup(_):
    return [
        [
            styled_button(text=_["S_B_4"], url=SUPPORT_CHAT, style="primary"),
        ],
    ]

# ═══════════════════════════════════════════════════════════
#         🌺 RhythmSync 🌺
#   github.com/SunloMusicOfficial/RhythmSync
# ═══════════════════════════════════════════════════════════
