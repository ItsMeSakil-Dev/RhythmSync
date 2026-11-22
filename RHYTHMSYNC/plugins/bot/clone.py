# ═══════════════════════════════════════════════════════════
#        🌺 RhythmSync - Premium Clone System 🌺
#   Path: RHYTHMSYNC/plugins/bot/clone.py
# ═══════════════════════════════════════════════════════════

import os
import re
import sys
import random
import asyncio
import logging
import subprocess
import razorpay
from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import AccessTokenInvalid, AuthKeyUnregistered
from motor.motor_asyncio import AsyncIOMotorClient
from RHYTHMSYNC import app
from config import MONGO_DB_URI, API_ID, API_HASH, OWNER_ID

# --- CONFIGURATION ---
logger = logging.getLogger("RHYTHMSYNC.clone")
RAZORPAY_KEY = os.environ.get("RAZORPAY_KEY_ID", "")
RAZORPAY_SECRET = os.environ.get("RAZORPAY_KEY_SECRET", "")

# Razorpay Client Initialize
if RAZORPAY_KEY and RAZORPAY_SECRET:
    razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY, RAZORPAY_SECRET))
else:
    razorpay_client = None

# --- DATABASE SETUP ---
mongo_client = AsyncIOMotorClient(MONGO_DB_URI)
db = mongo_client["RhythmSync"]
clone_requests = db["clone_requests"]
cloned_bots = db["cloned_bots"]
premium_users = db["premium_users"]

active_processes = {}

# --- LIMITS & PRICING ---
FREE_CLONE_LIMIT = 0   # Free Clone Band
PREMIUM_CLONE_LIMIT = 3
PREMIUM_PRICE_RS = 99  # ₹99 Premium Price

# ═══════════════════════════════════════════════════════════
# 💎 /buypremium COMMAND (Auto-UPI)
# ═══════════════════════════════════════════════════════════
@app.on_message(filters.command(["buypremium", "premium"]) & filters.private)
async def buy_premium(client: Client, message: Message):
    user_id = message.from_user.id
    
    is_premium = await premium_users.find_one({"user_id": user_id})
    if is_premium:
        return await message.reply_text("✅ **Aap pehle se Premium user hain!**\n\nAap `/clone` karke apna bot bana sakte hain.")

    if not razorpay_client:
        return await message.reply_text(
            "⚠️ **Payment Gateway Configure Nahi Hai.**\n"
            "Owner se contact karein."
        )

    status_msg = await message.reply_text("⏳ **Creating Payment Link...**")

    try:
        payment_link = razorpay_client.payment_link.create({
            "amount": PREMIUM_PRICE_RS * 100,  # ₹99 in paise
            "currency": "INR",
            "accept_partial": False,
            "description": "RhythmSync Premium (3 Bots)",
            "customer": {
                "name": message.from_user.first_name,
                "contact": str(user_id)
            },
            "notify": {"sms": False, "email": False},
            "reminder_enable": True,
            "notes": {
                "user_id": str(user_id),
                "plan": "premium"
            }
        })

        pay_url = payment_link['short_url']
        payment_id = payment_link['id']

        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("💳 Pay ₹99 Now", url=pay_url)],
            [InlineKeyboardButton("🔄 Check Payment Status", callback_data=f"check_pay_{payment_id}")]
        ])

        await status_msg.edit_text(
            f"💎 **RhythmSync Premium**\n\n"
            f"**💰 Amount:** ₹{PREMIUM_PRICE_RS}\n"
            f"**🎁 Benefits:**\n"
            f"• {PREMIUM_CLONE_LIMIT} Clone Bots (100% Same as Main Bot)\n"
            f"• Instant Auto-Approval\n\n"
            f"Payment ke liye niche button dabayein.\n"
            f"_(Payment successful hote hi premium auto-activate ho jayega)_",
            reply_markup=buttons
        )
    except Exception as e:
        logger.error(f"Razorpay Error: {e}")
        await status_msg.edit_text(f"❌ **Error:** `{e}`")

@app.on_callback_query(filters.regex(r"^check_pay_"))
async def check_payment_status(client: Client, query: CallbackQuery):
    user_id = query.from_user.id
    is_premium = await premium_users.find_one({"user_id": user_id})
    
    if is_premium:
        await query.message.edit_text("✅ **Payment Successful!**\n\nAap ab Premium hain. `/clone` bhej kar bot banayein.")
        return await query.answer("Premium Active!", show_alert=True)
    
    await query.answer("⚠️ Payment abhi receive nahi hui. Kripya payment complete karein.", show_alert=True)

# ═══════════════════════════════════════════════════════════
# 1. /clone COMMAND
# ═══════════════════════════════════════════════════════════
@app.on_message(filters.command("clone") & filters.private)
async def request_clone(client: Client, message: Message):
    user_id = message.from_user.id

    is_premium = await premium_users.find_one({"user_id": user_id})
    
    # 1. Block Free Users (Since Limit is 0)
    if not is_premium:
        return await message.reply_text(
            "🔒 **Clone Feature is Premium Only!**\n\n"
            "Free clone band kar diya gaya hai.\n"
            f"SIRF ₹{PREMIUM_PRICE_RS} mein Premium kharid kar apna bot banayein.\n\n"
            "👉 Premium kharidne ke liye **/buypremium** bhejein."
        )

    user_bots = await cloned_bots.count_documents({"user_id": user_id})
    if user_bots >= PREMIUM_CLONE_LIMIT:
        return await message.reply_text(
            f"❌ **Limit Reached!**\n\nAapne apni limit ({PREMIUM_CLONE_LIMIT} bots) reach kar li hai.\n"
            f"Kripya purana bot delete karein: `/mybots`"
        )

    pending = await clone_requests.find_one({"user_id": user_id, "status": "pending"})
    if pending:
        return await message.reply_text("⏳ **Aapki ek request pehle se pending hai.**")

    await message.reply_text(
        "🤖 **Premium Cloning Started!**\n\n"
        "**Step 1:** Kripya apna **Bot Token** bhejein (@BotFather se).\n\n"
        "❌ _Cancel karne ke liye `/cancel` bhejein._"
    )

    try:
        token_msg = await client.listen(message.chat.id, timeout=120, filters=filters.text)
        if token_msg.text.startswith("/"):
            return await message.reply_text("❌ Process cancelled.")

        bot_token = token_msg.text.strip()

        if not re.match(r'\d[0-9]{8,10}:[0-9A-Za-z_-]{35}', bot_token):
            return await message.reply_text("❌ **Invalid Token Format!** (Cancelled)")

        status_msg = await message.reply_text("⏳ **Verifying Bot Token...**")

        try:
            temp_client = Client(":memory:", api_id=API_ID, api_hash=API_HASH, bot_token=bot_token, in_memory=True)
            await temp_client.start()
            bot_info = await temp_client.get_me()
            await temp_client.stop()
        except AccessTokenInvalid:
            return await status_msg.edit_text("❌ **Invalid Token!** (Cancelled)")
        except Exception as e:
            return await status_msg.edit_text(f"❌ **Error:** `{e}`. (Cancelled)")

        await status_msg.edit_text(f"✅ **Token Verified!** (Bot: @{bot_info.username})\n\n**Step 2:** Ab apna **String Session** bhejein.\n_(Music ke liye zaroori)_")

    except asyncio.TimeoutError:
        return await message.reply_text("⏳ **Timeout!** Process cancelled.")

    try:
        session_msg = await client.listen(message.chat.id, timeout=120, filters=filters.text)
        if session_msg.text.startswith("/"):
            return await message.reply_text("❌ Process cancelled.")

        string_session = session_msg.text.strip()
        status_msg2 = await message.reply_text("⏳ **Verifying String Session...**")

        try:
            temp_user = Client(":memory:", api_id=API_ID, api_hash=API_HASH, session_string=string_session, in_memory=True)
            await temp_user.start()
            await temp_user.stop()
        except AuthKeyUnregistered:
            return await status_msg2.edit_text("❌ **Invalid Session!** (Cancelled)")
        except Exception as e:
            return await status_msg2.edit_text(f"❌ **Session Error:** `{e}`. (Cancelled)")

        await status_msg2.edit_text("✅ **Session Verified!**\n\n⏳ Starting your bot...")

    except asyncio.TimeoutError:
        return await message.reply_text("⏳ **Timeout!** Process cancelled.")

    # Premium users get instant approval (No owner button needed)
    await process_approval(client, user_id, bot_token, string_session, bot_info.username)

# ═══════════════════════════════════════════════════════════
# 2. CANCEL COMMAND
# ═══════════════════════════════════════════════════════════
@app.on_message(filters.command("cancel") & filters.private)
async def cancel_clone(client: Client, message: Message):
    await message.reply_text("✅ Process cancelled.")

# ═══════════════════════════════════════════════════════════
# 3. PROCESS APPROVAL (Start Subprocess)
# ═══════════════════════════════════════════════════════════
async def process_approval(client, user_id, bot_token, string_session, bot_username):
    try:
        port = random.randint(10000, 20000)
        env = os.environ.copy()
        env["BOT_TOKEN"] = bot_token
        env["STRING_SESSION"] = string_session
        env["PORT"] = str(port)
        env["OWNER_ID"] = str(user_id)
        env["BOT_NAME"] = f"{bot_username} Clone"

        process = subprocess.Popen([sys.executable, "-m", "RHYTHMSYNC"], env=env)
        active_processes[bot_username] = process

        await cloned_bots.update_one(
            {"user_id": user_id, "bot_username": bot_username},
            {"$set": {"token": bot_token, "session": string_session, "bot_username": bot_username, "user_id": user_id, "status": "active", "port": port}},
            upsert=True
        )

        msg = (
            f"🎉 **Badhai Ho!**\n\n"
            f"Aapka bot @{bot_username} live ho gaya hai.\n"
            f"Ab us bot me `/start` karein."
        )
        
        try: await client.send_message(user_id, msg)
        except: pass
        
        logger.info(f"Started {bot_username} on PORT {port}")

    except Exception as e:
        logger.error(f"Error: {e}")
        try: await client.send_message(user_id, f"❌ Error starting bot: `{e}`")
        except: pass

# ═══════════════════════════════════════════════════════════
# 4. USER COMMANDS: /mybots & /delbot
# ═══════════════════════════════════════════════════════════
@app.on_message(filters.command("mybots") & filters.private)
async def my_bots(client: Client, message: Message):
    user_bots = await cloned_bots.find({"user_id": message.from_user.id}).to_list(length=10)
    if not user_bots:
        return await message.reply_text("❌ Aapka koi bot nahi hai.")
    
    text = "**🤖 Your Bots:**\n\n"
    for i, bot in enumerate(user_bots, 1):
        text += f"{i}. @{bot.get('bot_username')}\n"
    text += "\nDelete: `/delbot <bot_username>`"
    await message.reply_text(text)

@app.on_message(filters.command("delbot") & filters.private)
async def delete_bot(client: Client, message: Message):
    if len(message.command) < 2:
        return await message.reply_text("**Usage:** `/delbot <bot_username>`")
    
    bot_username = message.command[1].replace("@", "")
    user_bot = await cloned_bots.find_one({"user_id": message.from_user.id, "bot_username": bot_username})
    
    if not user_bot:
        return await message.reply_text("❌ Bot nahi mila.")
    
    if bot_username in active_processes:
        try: 
            active_processes[bot_username].terminate()
            del active_processes[bot_username]
        except: pass
    
    await cloned_bots.delete_one({"bot_username": bot_username})
    await message.reply_text(f"✅ Bot @{bot_username} deleted.")

# ═══════════════════════════════════════════════════════════
# 5. OWNER COMMANDS
# ═══════════════════════════════════════════════════════════
@app.on_message(filters.command("addpremium") & filters.user(OWNER_ID))
async def add_premium(client: Client, message: Message):
    if len(message.command) < 2: 
        return await message.reply_text("**Usage:** `/addpremium <user_id>`")
    try: target_id = int(message.command[1])
    except: return await message.reply_text("❌ Invalid ID!")
    
    await premium_users.update_one({"user_id": target_id}, {"$set": {"user_id": target_id}}, upsert=True)
    await message.reply_text(f"✅ User `{target_id}` is now Premium.")
    try: await client.send_message(target_id, f"🎉 **Aapko Premium mil gaya!**\n\nAb aap {PREMIUM_CLONE_LIMIT} bots bana sakte hain.")
    except: pass

@app.on_message(filters.command("rempremium") & filters.user(OWNER_ID))
async def remove_premium(client: Client, message: Message):
    if len(message.command) < 2: 
        return await message.reply_text("**Usage:** `/rempremium <user_id>`")
    try: target_id = int(message.command[1])
    except: return await message.reply_text("❌ Invalid ID!")
    
    await premium_users.delete_one({"user_id": target_id})
    await message.reply_text(f"❌ User `{target_id}` premium removed.")

@app.on_message(filters.command("premiumstats") & filters.user(OWNER_ID))
async def premium_stats(client: Client, message: Message):
    total_premium = await premium_users.count_documents({})
    total_bots = await cloned_bots.count_documents({})
    
    await message.reply_text(
        f"📊 **Premium Stats**\n\n"
        f"👑 **Premium Users:** {total_premium}\n"
        f"🤖 **Total Cloned Bots:** {total_bots}"
    )

# ═══════════════════════════════════════════════════════════
# 6. START CLONED BOTS ON RESTART
# ═══════════════════════════════════════════════════════════
async def start_cloned_bots():
    logger.info("[Clone] Checking DB for active bots...")
    async for bot_data in cloned_bots.find({"status": "active"}):
        try:
            port = bot_data.get("port", random.randint(10000, 20000))
            env = os.environ.copy()
            env["BOT_TOKEN"] = bot_data["token"]
            env["STRING_SESSION"] = bot_data["session"]
            env["PORT"] = str(port)
            env["OWNER_ID"] = str(bot_data["user_id"])

            process = subprocess.Popen([sys.executable, "-m", "RHYTHMSYNC"], env=env)
            active_processes[bot_data["bot_username"]] = process
            logger.info(f"[Clone] Restarted {bot_data['bot_username']}")
        except Exception as e:
            logger.error(f"[Clone] Failed: {e}")
