# ═══════════════════════════════════════════════════════════
#        🌺 RhythmSync - Premium Clone System 🌺
#   Path: RHYTHMSYNC/plugins/bot/clone.py
#   Flow: Token -> Verify -> Session -> Verify -> Owner Approval -> Start
# ═══════════════════════════════════════════════════════════

import os
import re
import sys
import random
import asyncio
import logging
import subprocess
from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import AccessTokenInvalid, AuthKeyUnregistered
from motor.motor_asyncio import AsyncIOMotorClient
from RHYTHMSYNC import app
from config import MONGO_DB_URI, API_ID, API_HASH, OWNER_ID

# --- LOGGING SETUP ---
logger = logging.getLogger("RHYTHMSYNC.clone")

# --- DATABASE SETUP ---
mongo_client = AsyncIOMotorClient(MONGO_DB_URI)
db = mongo_client["RhythmSync"]
clone_requests = db["clone_requests"]
cloned_bots = db["cloned_bots"]
premium_users = db["premium_users"]

# Memory mein active subprocesses ko store karne ke liye
active_processes = {} 

# --- FREE & PREMIUM LIMITS ---
FREE_CLONE_LIMIT = 1
PREMIUM_CLONE_LIMIT = 3

# ═══════════════════════════════════════════════════════════
# 1. USER COMMAND: /clone (Step-by-Step Flow)
# ═══════════════════════════════════════════════════════════
@app.on_message(filters.command("clone") & filters.private)
async def request_clone(client: Client, message: Message):
    user_id = message.from_user.id

    # 1. Check Limits
    is_premium = await premium_users.find_one({"user_id": user_id})
    user_bots = await cloned_bots.count_documents({"user_id": user_id})
    
    limit = PREMIUM_CLONE_LIMIT if is_premium else FREE_CLONE_LIMIT
    if user_bots >= limit:
        return await message.reply_text(
            f"❌ **Clone Limit Reached!**\n\n"
            f"Aapne apni limit ({limit} bots) reach kar li hai.\n"
            f"{'Kripya purana bot delete karein.' if is_premium else 'Premium kharidne ke liye owner se contact karein.'}"
        )

    # 2. Check if already pending
    pending = await clone_requests.find_one({"user_id": user_id, "status": "pending"})
    if pending:
        return await message.reply_text("⏳ **Aapki ek request pehle se pending hai.** Owner ke approve karne ka wait karein.")

    # 3. STEP 1: Ask for Bot Token
    await message.reply_text(
        "🤖 **Welcome to RhythmSync Cloning!**\n\n"
        "**Step 1:** Kripya apna **Bot Token** bhejein (jo @BotFather se mila tha).\n\n"
        "❌ _Cancel karne ke liye `/cancel` bhejein._"
    )

    try:
        # Wait for user's token message
        token_msg = await client.listen(message.chat.id, timeout=120, filters=filters.text)
        
        if token_msg.text.startswith("/"):
            return await message.reply_text("❌ Process cancelled.")

        bot_token = token_msg.text.strip()

        # Validate Token Format
        if not re.match(r'\d[0-9]{8,10}:[0-9A-Za-z_-]{35}', bot_token):
            return await message.reply_text("❌ **Invalid Token Format!** Sahi token copy karein. (Process Cancelled)")

        status_msg = await message.reply_text("⏳ **Verifying your Bot Token...**")

        # Verify Bot Token
        try:
            temp_client = Client(":memory:", api_id=API_ID, api_hash=API_HASH, bot_token=bot_token, in_memory=True)
            await temp_client.start()
            bot_info = await temp_client.get_me()
            await temp_client.stop()
        except AccessTokenInvalid:
            return await status_msg.edit_text("❌ **Invalid Token!** Token galat hai ya revoke ho chuka hai. (Cancelled)")
        except Exception as e:
            return await status_msg.edit_text(f"❌ **Error:** `{e}`. (Cancelled)")

        await status_msg.edit_text(f"✅ **Token Verified!** (Bot: @{bot_info.username})\n\n**Step 2:** Ab apna **String Session** bhejein.\n_(Music play karne ke liye zaroori hai. @StringFatherBot se generate karein)_")

    except asyncio.TimeoutError:
        return await message.reply_text("⏳ **Timeout!** Aapne 2 minute tak token nahi bheja. Process cancel ho gaya.")

    # 4. STEP 2: Ask for String Session
    try:
        session_msg = await client.listen(message.chat.id, timeout=120, filters=filters.text)

        if session_msg.text.startswith("/"):
            return await message.reply_text("❌ Process cancelled.")

        string_session = session_msg.text.strip()
        status_msg2 = await message.reply_text("⏳ **Verifying String Session...**")

        # Verify Session
        try:
            temp_user = Client(":memory:", api_id=API_ID, api_hash=API_HASH, session_string=string_session, in_memory=True)
            await temp_user.start()
            await temp_user.stop()
        except AuthKeyUnregistered:
            return await status_msg2.edit_text("❌ **Invalid Session!** Session galat hai ya expire ho chuka hai. (Cancelled)")
        except Exception as e:
            return await status_msg2.edit_text(f"❌ **Session Error:** `{e}`. (Cancelled)")

        await status_msg2.edit_text("✅ **Session Verified!**\n\nAapki request Owner ke paas approval ke liye bhej di gayi hai. Please wait...")

    except asyncio.TimeoutError:
        return await message.reply_text("⏳ **Timeout!** Aapne 2 minute tak session nahi bheja. Process cancel ho gaya.")

    # 5. Save Request to DB
    await clone_requests.update_one(
        {"user_id": user_id},
        {"$set": {
            "user_id": user_id, 
            "token": bot_token, 
            "session": string_session, 
            "status": "pending", 
            "bot_username": bot_info.username
        }},
        upsert=True
    )

    # 6. Premium Instant Approval (Skip Owner Approval)
    if is_premium:
        await message.reply_text("✨ **Premium User Detected!** Instant approval in progress...")
        await process_approval(client, user_id, bot_token, string_session, bot_info.username, instant=True)
        return

    # 7. Send Message to Owner with Buttons
    owner_text = (
        f"🔔 **New Clone Request**\n\n"
        f"**User:** {message.from_user.mention} (`{user_id}`)\n"
        f"**Bot Name:** {bot_info.first_name}\n"
        f"**Username:** @{bot_info.username}\n"
        f"**User Bots:** {user_bots}/{limit}\n\n"
        f"Donon cheezein verify ho chuki hain. Kya aap isko approve karte hain?"
    )
    
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Approve", callback_data=f"approve_{user_id}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"reject_{user_id}")
        ]
    ])

    try:
        await client.send_message(OWNER_ID, owner_text, reply_markup=buttons)
    except Exception:
        await message.reply_text("❌ Owner tak message nahi pahunch paya. (Check OWNER_ID)")

# ═══════════════════════════════════════════════════════════
# 2. CANCEL COMMAND
# ═══════════════════════════════════════════════════════════
@app.on_message(filters.command("cancel") & filters.private)
async def cancel_clone(client: Client, message: Message):
    await message.reply_text("✅ Agar koi process chal raha tha, toh wo cancel ho gaya hai.")

# ═══════════════════════════════════════════════════════════
# 3. APPROVAL HANDLER
# ═══════════════════════════════════════════════════════════
@app.on_callback_query(filters.regex(r"^(approve|reject)_"))
async def handle_approval(client: Client, query: CallbackQuery):
    if query.from_user.id != OWNER_ID:
        return await query.answer("❌ Sirf Owner ke liye!", show_alert=True)

    action, user_id = query.data.split("_")
    user_id = int(user_id)

    request_data = await clone_requests.find_one({"user_id": user_id, "status": "pending"})
    if not request_data:
        return await query.answer("⚠️ Request pehle hi process ho chuki hai.", show_alert=True)

    if action == "reject":
        await clone_requests.update_one({"user_id": user_id}, {"$set": {"status": "rejected"}})
        await query.message.edit_text(f"❌ Request Rejected for User `{user_id}`.")
        try: await client.send_message(user_id, "❌ **Aapki Clone Request Reject kar di gayi hai** Owner dwara.")
        except: pass
        return await query.answer("Rejected!")

    elif action == "approve":
        await query.message.edit_text(f"⏳ Processing approval for `{user_id}`...")
        await process_approval(
            client, user_id, 
            request_data["token"], 
            request_data["session"], 
            request_data["bot_username"]
        )
        await query.answer("Approved!")

async def process_approval(client, user_id, bot_token, string_session, bot_username, instant=False):
    try:
        # Naya process start karein (Subprocess)
        port = random.randint(10000, 20000)
        env = os.environ.copy()
        env["BOT_TOKEN"] = bot_token
        env["STRING_SESSION"] = string_session
        env["PORT"] = str(port)
        env["OWNER_ID"] = str(user_id)
        env["BOT_NAME"] = f"{bot_username} Clone"

        # Main bot background me naya python process run karega
        process = subprocess.Popen([sys.executable, "-m", "RHYTHMSYNC"], env=env)
        active_processes[bot_username] = process

        # DB Update
        await clone_requests.update_one({"user_id": user_id}, {"$set": {"status": "approved"}})
        await cloned_bots.update_one(
            {"user_id": user_id, "bot_username": bot_username},
            {"$set": {"token": bot_token, "session": string_session, "bot_username": bot_username, "user_id": user_id, "status": "active", "port": port}},
            upsert=True
        )

        msg = (
            f"🎉 **Badhai Ho!**\n\n"
            f"Aapka bot @{bot_username} successfully start ho gaya hai.\n"
            f"Ab aap us bot me `/start` karke 100% main bot ki tarah use kar sakte hain."
        )
        
        if instant:
            try: await client.send_message(user_id, f"✨ **Premium Auto-Approve!**\n\n{msg}")
            except: pass
        else:
            try: await client.send_message(user_id, msg)
            except: pass
        
        logger.info(f"Started subprocess for {bot_username} on PORT {port}")

    except Exception as e:
        logger.error(f"Error starting clone: {e}")
        try: await client.send_message(user_id, f"❌ Error starting bot: `{e}`")
        except: pass

# ═══════════════════════════════════════════════════════════
# 4. USER COMMANDS: /mybots & /delbot
# ═══════════════════════════════════════════════════════════
@app.on_message(filters.command("mybots") & filters.private)
async def my_bots(client: Client, message: Message):
    user_bots = await cloned_bots.find({"user_id": message.from_user.id}).to_list(length=10)
    if not user_bots:
        return await message.reply_text("❌ Aapka koi bot nahi hai. `/clone` se banayein.")
    
    text = "**🤖 Your Bots:**\n\n"
    for i, bot in enumerate(user_bots, 1):
        text += f"{i}. @{bot.get('bot_username')}\n"
    text += "\nDelete karne ke liye: `/delbot <bot_username>`"
    await message.reply_text(text)

@app.on_message(filters.command("delbot") & filters.private)
async def delete_bot(client: Client, message: Message):
    if len(message.command) < 2:
        return await message.reply_text("**Usage:** `/delbot <bot_username>`")
    
    bot_username = message.command[1].replace("@", "")
    user_bot = await cloned_bots.find_one({"user_id": message.from_user.id, "bot_username": bot_username})
    
    if not user_bot:
        return await message.reply_text("❌ Bot nahi mila ya aap iske owner nahi hain.")
    
    if bot_username in active_processes:
        try: 
            active_processes[bot_username].terminate()
            del active_processes[bot_username]
        except: pass
    
    await cloned_bots.delete_one({"bot_username": bot_username})
    await message.reply_text(f"✅ Bot @{bot_username} successfully deleted.")

# ═══════════════════════════════════════════════════════════
# 5. OWNER COMMANDS: /addpremium & /rempremium
# ═══════════════════════════════════════════════════════════
@app.on_message(filters.command("addpremium") & filters.user(OWNER_ID))
async def add_premium(client: Client, message: Message):
    if len(message.command) < 2: return await message.reply_text("**Usage:** `/addpremium <user_id>`")
    target_id = int(message.command[1])
    await premium_users.update_one({"user_id": target_id}, {"$set": {"user_id": target_id}}, upsert=True)
    await message.reply_text(f"✅ User `{target_id}` is now Premium (Instant Approve).")

@app.on_message(filters.command("rempremium") & filters.user(OWNER_ID))
async def remove_premium(client: Client, message: Message):
    if len(message.command) < 2: return await message.reply_text("**Usage:** `/rempremium <user_id>`")
    target_id = int(message.command[1])
    await premium_users.delete_one({"user_id": target_id})
    await message.reply_text(f"❌ User `{target_id}` premium removed.")

# ═══════════════════════════════════════════════════════════
# 6. START CLONED BOTS ON SERVER RESTART
# ═══════════════════════════════════════════════════════════
async def start_cloned_bots():
    logger.info("[Clone] Checking Database for active bots...")
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
            logger.info(f"[Clone] Restarted bot: @{bot_data['bot_username']} on port {port}")
        except Exception as e:
            logger.error(f"[Clone] Failed to restart {bot_data.get('bot_username')}: {e}")
