# ═══════════════════════════════════════════════════════════
#        🌺 RhythmSync 🌺
#   GɪᴛHᴜʙ : github.com/SunloMusicOfficial/RhythmSync
#   Dᴇᴠʟᴏᴘᴇʀ : @YO_UR_OFFICIAL_CRUSH | Telegram
# ═══════════════════════════════════════════════════════════

import asyncio
import gc
import importlib
import logging
import os
import time
from threading import Thread

import config
from RHYTHMSYNC import LOGGER, app, userbot
from RHYTHMSYNC.core.call import SAKIL
from RHYTHMSYNC.misc import sudo
from RHYTHMSYNC.plugins import ALL_MODULES
from RHYTHMSYNC.utils.database import get_banned_users, get_gbanned
from RHYTHMSYNC.utils.cookie_handler import fetch_and_store_cookies
from config import BANNED_USERS
from pyrogram import idle
from pytgcalls.exceptions import NoActiveGroupCall

# ----------------------🔹 Render / Web Flask Dashboard 🔹----------------------
def keep_alive():
    try:
        from flask import Flask, jsonify, request
        from pymongo import MongoClient
    except ImportError:
        return

    def run_flask():
        fapp = Flask(__name__)
        logging.getLogger('werkzeug').setLevel(logging.ERROR)

        try:
            _sync_mongo = MongoClient(
                config.MONGO_DB_URI,
                serverSelectionTimeoutMS=2000,
                connectTimeoutMS=2000,
                maxPoolSize=2,
                minPoolSize=0,
                maxIdleTimeMS=20000,
            )
            _sync_db = _sync_mongo.Sakil
        except Exception:
            _sync_db = None

        _start_time = time.time()

        @fapp.route('/')
        def home():
            try:
                uptime_sec = int(time.time() - _start_time)
                hours, remainder = divmod(uptime_sec, 3600)
                minutes, seconds = divmod(remainder, 60)
                uptime_str = f"{hours}h {minutes}m {seconds}s"

                total_users = total_chats = total_banned = total_sudoers = 0
                if _sync_db is not None:
                    try:
                        total_users = _sync_db.tgusersdb.count_documents({})
                        total_chats = _sync_db.chats.count_documents({})
                        total_banned = _sync_db.blockedusers.count_documents({})
                        sudo_data = _sync_db.sudoers.find_one({"sudo": "sudo"})
                        total_sudoers = len(sudo_data.get("sudoers", [])) if sudo_data else 0
                    except Exception as db_error:
                        LOGGER("RHYTHMSYNC").warning(f"DB stats error: {db_error}")

                bot_name = getattr(config, "BOT_NAME", "Sakil Music Bot")
                owner_username = getattr(config, "OWNER_USERNAME", "RhythmSyncBots")
                bot_username = getattr(config, "BOT_USERNAME", "vaishaliTune_bot")

                return f"""<!DOCTYPE html>
<html><head><title>Sakil Music Bot</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="refresh" content="30">
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'Segoe UI',sans-serif;background:linear-gradient(135deg,#0f0c29,#302b63,#24243e);min-height:100vh;color:#fff;padding:20px}}
.c{{max-width:800px;margin:0 auto}}
.h{{text-align:center;padding:30px 0}}
.h h1{{font-size:2.2em;background:linear-gradient(90deg,#7c6cff,#00ff88);-webkit-background-clip:text;-webkit-text-fill-color:transparent}}
.sb{{display:inline-flex;align-items:center;gap:8px;background:rgba(0,255,136,.1);border:1px solid rgba(0,255,136,.3);padding:8px 20px;border-radius:30px;margin-top:15px}}
.dot{{width:10px;height:10px;background:#00ff88;border-radius:50%;animation:p 2s infinite}}
@keyframes p{{0%,100%{{opacity:1}}50%{{opacity:.3}}}}
.sg{{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:15px;margin:30px 0}}
.sc{{background:rgba(255,255,255,.05);backdrop-filter:blur(10px);border:1px solid rgba(255,255,255,.08);border-radius:16px;padding:25px 20px;text-align:center;transition:transform .2s}}
.sc:hover{{transform:translateY(-3px)}}
.sc .i{{font-size:1.8em}}.sc .v{{font-size:1.6em;font-weight:bold;margin:8px 0 4px;color:#00ff88}}.sc .l{{color:#888;font-size:.85em}}
.ib{{background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.06);border-radius:12px;padding:20px;margin-top:20px}}
.ir{{display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px solid rgba(255,255,255,.05)}}
.ir:last-child{{border:none}}.ir .k{{color:#888}}.ir .vl{{color:#ddd;font-weight:500}}
.f{{text-align:center;margin-top:30px;color:#555;font-size:.8em}}.f a{{color:#7c6cff;text-decoration:none}}
</style></head><body><div class="c">
<div class="h"><h1>🎵 Sakil Music Bot</h1><div class="sb"><span class="dot"></span><span style="color:#00ff88;font-size:.9em">Online & Running</span></div></div>
<div class="sg">
<div class="sc"><div class="i">👥</div><div class="v">{total_users}</div><div class="l">Total Users</div></div>
<div class="sc"><div class="i">💬</div><div class="v">{total_chats}</div><div class="l">Total Chats</div></div>
<div class="sc"><div class="i">🚫</div><div class="v">{total_banned}</div><div class="l">Banned Users</div></div>
<div class="sc"><div class="i">👑</div><div class="v">{total_sudoers}</div><div class="l">Sudo Users</div></div>
</div>
<div class="ib">
<div class="ir"><span class="k">⏱️ Uptime</span><span class="vl">{uptime_str}</span></div>
<div class="ir"><span class="k">🤖 Bot Name</span><span class="vl">{bot_name}</span></div>
<div class="ir"><span class="k">👤 Owner</span><span class="vl">@{owner_username}</span></div>
<div class="ir"><span class="k">🌍 Languages</span><span class="vl">15 Supported</span></div>
</div>
<div class="f"><p>Auto-refreshes every 30s</p><p style="margin-top:8px"><a href="https://t.me/{bot_username}">Open Bot</a> • <a href="https://t.me/Vip_Sakil_Bio">Developer</a></p></div>
</div></body></html>"""
            except Exception as e:
                logging.getLogger("RHYTHMSYNC").error(f"Flask home error: {e}")
                return f"Error: {str(e)}", 500

        @fapp.route('/health')
        def health():
            return "OK", 200

        @fapp.route('/api/stats')
        def api_stats():
            if _sync_db is None:
                return jsonify({"error": "DB not connected", "status": "error"}), 200
            try:
                return jsonify({
                    "users": _sync_db.tgusersdb.count_documents({}),
                    "chats": _sync_db.chats.count_documents({}),
                    "banned": _sync_db.blockedusers.count_documents({}),
                    "uptime": int(time.time() - _start_time),
                    "status": "running"
                })
            except Exception as e:
                logging.getLogger("RHYTHMSYNC").error(f"Flask API stats error: {e}")
                return jsonify({"error": str(e), "status": "error"}), 200

        # ═══════════════════════════════════════════════════════
        # 💳 RAZORPAY WEBHOOK (AUTO UPI PAYMENT DETECTION)
        # ═══════════════════════════════════════════════════════
        @fapp.route('/razorpay_webhook', methods=['POST'])
        def razorpay_webhook():
            import hmac
            import hashlib
            
            webhook_secret = os.environ.get("RAZORPAY_WEBHOOK_SECRET", "")
            webhook_signature = request.headers.get('X-Razorpay-Signature')
            webhook_body = request.get_data()
            
            if not webhook_secret:
                return jsonify({"status": "error", "message": "Webhook secret not set"}), 500

            expected_signature = hmac.new(
                webhook_secret.encode('utf-8'),
                webhook_body,
                hashlib.sha256
            ).hexdigest()

            if webhook_signature != expected_signature:
                return jsonify({"status": "invalid signature"}), 400

            data = request.json
            event = data.get('event')

            # Jab payment successful ho jaye (QR Code scan / UPI se)
            if event == 'payment.captured':
                payload = data['payload']['payment']['entity']
                payment_id = payload['id']
                amount = payload['amount'] / 100
                notes = payload.get('notes', {})
                user_id = int(notes.get('user_id', 0))

                if user_id and _sync_db is not None:
                    # MongoDB mein premium add karein
                    _sync_db.premium_users.update_one(
                        {"user_id": user_id},
                        {"$set": {"user_id": user_id, "payment_id": payment_id, "amount": amount}},
                        upsert=True
                    )
                    LOGGER("RHYTHMSYNC").info(f"[AUTO-UPI] Premium granted to {user_id} via Razorpay {payment_id}")

                    # Telegram par user ko success message bhejein
                    from RHYTHMSYNC import app
                    import asyncio
                    
                    async def notify_user():
                        try:
                            await app.send_message(
                                user_id,
                                f"🎉 **Payment Successful!**\n\n"
                                f"Aapka payment (₹{amount}) receive ho gaya hai.\n"
                                f"Aap ab **Premium Member** hain!\n\n"
                                f"**Transaction ID:** `{payment_id}`\n"
                                f"Ab aap `/clone` command bhej kar apna bot bana sakte hain."
                            )
                        except Exception as e:
                            LOGGER("RHYTHMSYNC").error(f"Message send failed: {e}")

                    asyncio.run_coroutine_threadsafe(notify_user(), app.loop)

            return jsonify({"status": "success"}), 200

        port = int(os.environ.get("PORT", 3000))
        fapp.run(host="0.0.0.0", port=port)

    t = Thread(target=run_flask)
    t.daemon = True
    t.start()

# Start Flask Web server immediately for Render port binding
keep_alive()


async def _gc_loop() -> None:
    """Periodic garbage collection loop to keep RAM footprint low and clean memory leaks."""
    while True:
        await asyncio.sleep(600)  # Every 10 mins
        gc.collect()


async def _cookie_refresh_loop() -> None:
    """Periodically re-fetch YouTube cookies."""
    hours = float(os.environ.get("COOKIE_REFRESH_HOURS", "12"))
    while True:
        await asyncio.sleep(hours * 3600)
        try:
            await fetch_and_store_cookies()
            LOGGER("RHYTHMSYNC").info("ʏᴏᴜᴛᴜʙᴇ ᴄᴏᴏᴋɪᴇs ʀᴇꜰʀᴇꜱʜᴇᴅ ✔")
        except Exception as e:
            LOGGER("RHYTHMSYNC").warning(f"⚠️ ᴄᴏᴏᴋɪᴇ ʀᴇꜰʀᴇꜱʜ ꜰᴀɪʟᴇᴅ: {e}")


async def _auto_restart_loop(hours: float) -> None:
    """Optional watchdog: restart the bot process every N hours."""
    import sys

    while True:
        await asyncio.sleep(hours * 3600)
        LOGGER("RHYTHMSYNC").info(f"🔄 ᴀᴜᴛᴏ-ʀᴇꜱᴛᴀʀᴛ ᴀꜰᴛᴇʀ {hours}h ᴏꜰ ᴜᴘᴛɪᴍᴇ...")
        try:
            os.execv(sys.executable, [sys.executable, "-m", "RHYTHMSYNC"])
        except Exception as e:
            LOGGER("RHYTHMSYNC").error(f"❌ ᴀᴜᴛᴏ-ʀᴇꜱᴛᴀʀᴛ ꜰᴀɪʟᴇᴅ: {e}")
            return


async def _keepalive_ping_loop() -> None:
    """Render / Koyeb free-tier keep-alive."""
    url = (os.environ.get("KEEPALIVE_URL") or "").strip().rstrip("/")
    if not url:
        return

    try:
        interval = max(60, int(os.environ.get("KEEPALIVE_INTERVAL", "600")))
    except (TypeError, ValueError):
        interval = 600

    target = f"{url}/health"
    LOGGER("RHYTHMSYNC").info(
        f"🩺 ᴋᴇᴇᴘ-ᴀʟɪᴠᴇ ᴇɴᴀʙʟᴇᴅ: ᴘɪɴɢɪɴɢ {target} ᴇᴠᴇʀʏ {interval}s"
    )

    import aiohttp

    while True:
        await asyncio.sleep(interval)
        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30)
            ) as session:
                async with session.get(target) as resp:
                    if resp.status != 200:
                        LOGGER("RHYTHMSYNC").warning(
                            f"⚠️ ᴋᴇᴇᴘ-ᴀʟɪᴠᴇ ᴘɪɴɢ ʀᴇᴛᴜʀɴᴇᴅ HTTP {resp.status}"
                        )
        except Exception as e:
            LOGGER("RHYTHMSYNC").warning(f"⚠️ ᴋᴇᴇᴘ-ᴀʟɪᴠᴇ ᴘɪɴɢ ꜰᴀɪʟᴇᴅ: {e}")


async def init():
    if (
        not config.STRING1
        and not config.STRING2
        and not config.STRING3
        and not config.STRING4
        and not config.STRING5
    ):
        LOGGER(__name__).error("ᴀssɪsᴛᴀɴᴛ sᴇssɪᴏɴ ɴᴏᴛ ғɪʟʟᴇᴅ, ᴘʟᴇᴀsᴇ ғɪʟʟ ᴀ ᴘʏʀᴏɢʀᴀᴍ sᴇssɪᴏɴ...")
        exit()

    # ✅ Try to fetch cookies at startup
    try:
        await fetch_and_store_cookies()
        LOGGER("RHYTHMSYNC").info("ʏᴏᴜᴛᴜʙᴇ ᴄᴏᴏᴋɪᴇs ʟᴏᴀᴅᴇᴅ sᴜᴄᴄᴇssғᴜʟʟʏ ✅")
    except Exception as e:
        LOGGER("RHYTHMSYNC").warning(f"⚠️ ᴄᴏᴏᴋɪᴇ ᴇʀʀᴏʀ: {e}")

    await sudo()

    try:
        users = await get_gbanned()
        for user_id in users:
            BANNED_USERS.add(user_id)
        users = await get_banned_users()
        for user_id in users:
            BANNED_USERS.add(user_id)
    except:
        pass

    await app.start()
    for all_module in ALL_MODULES:
        try:
            importlib.import_module("RHYTHMSYNC.plugins" + all_module)
        except Exception as e:
            # One broken plugin must never kill the bot.
            LOGGER("RHYTHMSYNC.plugins").error(
                f"❌ Failed to load module {all_module}: {e}\nBot continues without it."
            )

    LOGGER("RHYTHMSYNC.plugins").info("ᴍᴏᴅᴜʟᴇs ʟᴏᴀᴅᴇᴅ...")

    # ═══════════════════════════════════════════════════════════
    # 🌟 CLONE SYSTEM INITIALIZATION
    # ═══════════════════════════════════════════════════════════
    try:
        from RHYTHMSYNC.plugins.bot.clone import start_cloned_bots
        # Background mein cloned bots ko start karein
        asyncio.create_task(start_cloned_bots())
        LOGGER("RHYTHMSYNC").info("🌟 ᴄʟᴏɴᴇ sʏsᴛᴇᴍ ʟᴏᴀᴅᴇᴅ ✔")
    except Exception as e:
        LOGGER("RHYTHMSYNC").error(f"❌ ᴄʟᴏɴᴇ sʏsᴛᴇᴍ ʟᴏᴀᴅ ꜰᴀɪʟᴇᴅ: {e}")
    # ═══════════════════════════════════════════════════════════

    await userbot.start()

    # ▶️ VC Logger: resume VC join/leave notifications
    try:
        from RHYTHMSYNC.plugins.tools.vclogger import load_vc_logger_status
        asyncio.create_task(load_vc_logger_status())
    except Exception as e:
        LOGGER("RHYTHMSYNC").warning(f"⚠️ ᴠᴄ ʟᴏɢɢᴇʀ ɪɴɪᴛ ғᴀɪʟᴇᴅ: {e}")

    await SAKIL.start()

    try:
        await SAKIL.stream_call("https://files.catbox.moe/euj0oc.mp4")
    except NoActiveGroupCall:
        LOGGER("RHYTHMSYNC").error(
            "ᴘʟᴇᴀsᴇ ᴛᴜʀɴ ᴏɴ ᴛʜᴇ ᴠᴏɪᴄᴇ ᴄʜᴀᴛ ᴏғ ʏᴏᴜʀ ʟᴏɢ ɢʀᴏᴜᴘ/ᴄʜᴀɴɴᴇʟ.\n\nʙᴏᴛ sᴛᴏᴘᴘᴇᴅ..."
        )
        exit()
    except:
        pass

    await SAKIL.decorators()

    # Long-uptime health: periodic GC, refresh YouTube cookies periodically
    asyncio.create_task(_gc_loop())
    asyncio.create_task(_cookie_refresh_loop())
    
    # Render/Koyeb free tier: keep the service from spinning down on idle.
    asyncio.create_task(_keepalive_ping_loop())
    
    auto_restart_hours = float(os.environ.get("AUTO_RESTART_HOURS", "0"))
    if auto_restart_hours > 0:
        asyncio.create_task(_auto_restart_loop(auto_restart_hours))
        LOGGER("RHYTHMSYNC").info(f"🔄 ᴀᴜᴛᴏ-ʀᴇꜱᴛᴀʀᴛ ᴇɴᴀʙʟᴇᴅ: ᴇᴠᴇʀʏ {auto_restart_hours}h")

    LOGGER("RHYTHMSYNC").info("✅ Sakil music Bot Started Successfully!")
    await idle()
    await app.stop()
    await userbot.stop()
    LOGGER("RHYTHMSYNC").info("sᴛᴏᴘᴘɪɴɢ ᴍᴜsɪᴄ ʙᴏᴛ ...")


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(init())

# ═══════════════════════════════════════════════════════════
#         🌺 RhythmSync 🌺
#   github.com/SunloMusicOfficial/RhythmSync
# ═══════════════════════════════════════════════════════════
