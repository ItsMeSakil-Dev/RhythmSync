# ═══════════════════════════════════════════════════════════
#        🌺 RhythmSync 🌺
#   GɪᴛHᴜʙ : github.com/SunloMusicOfficial/RhythmSync
#   Dᴇᴠʟᴏᴘᴇʀ : @YO_UR_OFFICIAL_CRUSH | Telegram
# ═══════════════════════════════════════════════════════════

import random
import asyncio
import time
from pathlib import Path
from typing import Optional

import aiohttp


class UnableToFetchCarbon(Exception):
    pass


# Sirf woh names jo carbonara actually support karta hai.
# "dracula-pro" aur "parasio-dark" hata diye — ye HTTP 400 dete the.
themes = [
    "3024-night", "a11y-dark", "blackboard", "base16-dark", "base16-light",
    "cobalt", "duotone-dark", "hopscotch", "lucario", "material", "monokai",
    "night-owl", "nord", "oceanic-next", "one-light", "one-dark", "panda-syntax",
    "paraiso-dark", "seti", "shades-of-purple", "solarized-dark", "solarized-light",
    "synthwave-84", "twilight", "verminal", "vscode", "yeti", "zenburn",
]

# Fallback pool — agar random theme reject ho jaye to inme se pakka chalega.
SAFE_THEMES = ["seti", "blackboard", "cobalt", "monokai", "nord", "twilight"]

colour = [
    "#FF0000", "#FF5733", "#FFFF00", "#008000", "#0000FF", "#800080", "#A52A2A",
    "#FF00FF", "#D2B48C", "#00FFFF", "#808000", "#800000", "#30D5C8", "#00FF00",
    "#008080", "#4B0082", "#EE82EE", "#FFC0CB", "#000000", "#FFFFFF", "#808080",
]

# Primary + mirror endpoint.
ENDPOINTS = [
    "https://carbonara.solopov.dev/api/cook",
    "https://carbonara-42.vercel.app/api/cook",
]

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


class CarbonAPI:
    def __init__(self, cache_dir: str = "cache", timeout_s: int = 25):
        self.language = "auto"
        self.drop_shadow = True
        self.drop_shadow_blur = "68px"
        self.drop_shadow_offset = "20px"
        self.font_family = "JetBrains Mono"
        self.width_adjustment = True
        self.watermark = False

        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self._timeout = aiohttp.ClientTimeout(total=timeout_s)
        self._session: Optional[aiohttp.ClientSession] = None

    async def _session_get(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=self._timeout,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "sakilMusic/CarbonClient",
                },
            )
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    async def generate(self, text: str, user_id) -> str:
        if not text:
            raise UnableToFetchCarbon("Empty text.")
        if len(text) > 10000:
            raise UnableToFetchCarbon("Text too long (max 10k characters).")

        session = await self._session_get()
        errors = []

        # 3 attempts: pehla random theme, baaki pakke SAFE_THEMES se.
        for attempt in range(3):
            pool = themes if attempt == 0 else SAFE_THEMES
            params = {
                "code": text,
                "backgroundColor": random.choice(colour),
                "theme": random.choice(pool),
                "dropShadow": self.drop_shadow,
                "dropShadowOffsetY": self.drop_shadow_offset,
                "dropShadowBlurRadius": self.drop_shadow_blur,
                "fontFamily": self.font_family,
                "language": self.language,
                "watermark": self.watermark,
                "widthAdjustment": self.width_adjustment,
            }
            url = ENDPOINTS[attempt % len(ENDPOINTS)]

            try:
                async with session.post(url, json=params) as resp:
                    data = await resp.read()

                    if resp.status != 200:
                        errors.append(f"{url} -> HTTP {resp.status}: {data[:120]!r}")
                    elif not data.startswith(PNG_MAGIC):
                        # 200 mila par body image nahi hai (rate-limit page etc.)
                        errors.append(f"{url} -> non-PNG body: {data[:120]!r}")
                    else:
                        filename = f"carbon_{user_id}_{int(time.time() * 1000)}.png"
                        out = self.cache_dir / filename
                        out.write_bytes(data)
                        return str(out.resolve())

            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                errors.append(f"{url} -> {e!r}")

            if attempt < 2:
                await asyncio.sleep(1.5 * (attempt + 1))

        raise UnableToFetchCarbon("All attempts failed: " + " | ".join(errors))
