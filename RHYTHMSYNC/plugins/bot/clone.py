# ═══════════════════════════════════════════════════════════
#        🌺 RhythmSync - Premium Clone System 🌺
#   Path: RHYTHMSYNC/plugins/bot/clone.py
# ═══════════════════════════════════════════════════════════

import os
import re
import asyncio
import logging
from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import AccessTokenInvalid, ApiIdInvalid
from motor.motor_asyncio import AsyncIOMotorClient
from RHYTHMSYNC import app

# --- LOGGING SETUP ---
logger = logging.getLogger("RHYTHMSYNC.clone")

# --- CONFIGURATION ---
from config import MONGO_DB_URI, API_ID, API_HASH, OWNER_ID

# Apne plugins folder ka naam yahan dein
PLUGINS_DIR = "RHYTHMSYNC.plugins" 

# --- DATABASE SETUP ---
mongo_client = AsyncIOMotorClient(MONGO_DB_URI)
db = mongo_client["RhythmSync"]
clone_requests = db["clone_requests"]
cloned_bots = db["cloned_bots"]
premium_users = db["premium_users"]

# Memory mein active bots ko store karne ke liye
active_clones = {}

# --- FREE & PREMIUM LIMITS ---
FREE_CLONE_LIMIT = 1
PREMIUM_CLONE_LIMIT = 3

# ═══════════════════════════════════════════════════════════
# 1. USER COMMAND: /clone <token>
# ═══════════════════════════════════════════════════════════
@app.on_message(filters.command("clone") & filters.private)
async def request_clone(client: Client, message: Message):
    if len(message.command) < 2:
        return await message.reply_text(
            "**🤖 Premium Bot Cloning**\n\n"
            "Apna khud ka music bot banane ke liye:\n"
            "`/clone <your_bot_token>`\n\n"
            "**Note:** Aapki request Owner ke paas approval ke liye jayegi.\n"
            "**Premium Users:** Instant Approval (No Wait)."
        )

    bot_token = message.command[1].strip()
    user_id = message.from_user.id

    # 1. Token Format Check
    if not re.match(r'\d[0-9]{8,10}:[0-9A-Za-z_-]{35}', bot_token):
        return await message.reply_text("❌ **Invalid Token Format!** @BotFather se sahi token copy karein.")

    # 2. Check if already pending
    pending = await clone_requests.find_one({"user_id": user_id, "status": "pending"})
    if pending:
        return await message.reply_text("⏳ **Aapki ek request pehle se pending hai.** Owner ke approve karne ka wait karein.")

    # 3. Check Clone Limits
    is_premium = await premium_users.find_one({"user_id": user_id})
    user_bots = await cloned_bots.count_documents({"user_id": user_id})
    
    limit = PREMIUM_CLONE_LIMIT if is_premium else FREE_CLONE_LIMIT
    if user_bots >= limit:
        return await message.reply_text(
            f"❌ **Clone Limit Reached!**\n\n"
            f"Aapne apni limit ({limit} bots) reach kar li hai.\n"
            f"{'Aap premium user hain, kripya purana bot delete karein.' if is_premium else 'Premium kharidne ke liye owner se contact karein.'}"
        )

    status_msg = await message.reply_text("⏳ **Verifying your bot token...**")

    # 4. Verify Token
    try:
        temp_client = Client(":memory:", api_id=API_ID, api_hash=API_HASH, bot_token=bot_token, in_memory=True)
        bot_info = await temp_client.get_me()
        await temp_client.stop()
    except AccessTokenInvalid:
        return await status_msg.edit_text("❌ **Invalid Token!** Token galat hai ya revoke ho chuka hai.")
    except Exception as e:
        return await status_msg.edit_text(f"❌ **Error:** `{e}`")

    # 5. Save Request to DB
    await clone_requests.update_one(
        {"user_id": user_id},
        {"$set": {"user_id": user_id, "token": bot_token, "status": "pending", "bot_username": bot_info.username}},
        upsert=True
    )

    # 6. Premium Instant Approval Logic
    if is_premium:
        await status_msg.edit_text("✨ **Premium User Detected!** Instant approval in progress...")
        await process_approval(client, user_id, bot_token, bot_info.username, instant=True)
        return

    await status_msg.edit_text("✅ **Token Verified!**\n\nAapki request Owner ko bhej di gayi hai. Approval ka wait karein.")

    # 7. Send Message to Owner with Buttons
    owner_text = (
        f"🔔 **New Clone Request**\n\n"
        f"**User:** {message.from_user.mention} (`{user_id}`)\n"
        f"**Bot Name:** {bot_info.first_name}\n"
        f"**Username:** @{bot_info.username}\n"
        f"**User Bots:** {user_bots}/{limit}\n\n"
        f"Kya aap is user ko bot clone karne ki permission dete hain?"
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
        await status_msg.edit_text("❌ Owner tak message nahi pahunch paya. (Check OWNER_ID)")

# ═══════════════════════════════════════════════════════════
# 2. APPROVAL HANDLER (Owner Inline Buttons)
# ═══════════════════════════════════════════════════════════
@app.on_callback_query(filters.regex(r"^(approve|reject)_"))
async def handle_approval(client: Client, query: CallbackQuery):
    if query.from_user.id != OWNER_ID:
        return await query.answer("❌ Ye button sirf Owner ke liye hai!", show_alert=True)

    action, user_id = query.data.split("_")
    user_id = int(user_id)

    request_data = await clone_requests.find_one({"user_id": user_id, "status": "pending"})
    if not request_data:
        return await query.answer("⚠️ Request pehle hi process ho chuki hai.", show_alert=True)

    if action == "reject":
        await clone_requests.update_one({"user_id": user_id}, {"$set": {"status": "rejected"}})
        await query.message.edit_text(f"❌ Request Rejected for User `{user_id}`.")
        
        try:
            await client.send_message(user_id, "❌ **Aapki Clone Request Reject kar di gayi hai** Owner dwara.")
        except: pass
        return await query.answer("Rejected!")

    elif action == "approve":
        await query.message.edit_text(f"⏳ Processing approval for `{user_id}`...")
        bot_token = request_data["token"]
        await process_approval(client, user_id, bot_token, request_data.get("bot_username", "Bot"))
        await query.answer("Approved!")

async def process_approval(client, user_id, bot_token, bot_username, instant=False):
    try:
        new_client = Client(
            name=f"clone_{bot_token[:10]}",
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=bot_token,
            plugins={"root": PLUGINS_DIR}
        )
        await new_client.start()
        bot_info = await new_client.get_me()

        await clone_requests.update_one({"user_id": user_id}, {"$set": {"status": "approved"}})
        await cloned_bots.update_one(
            {"user_id": user_id, "bot_id": bot_info.id},
            {"$set": {"token": bot_token, "bot_username": bot_info.username, "user_id": user_id, "status": "active"}},
            upsert=True
        )
        active_clones[bot_info.id] = new_client

        msg = f"✅ **Bot Successfully Cloned!**\n\nUsername: @{bot_info.username}"
        if instant:
            try: await client.send_message(user_id, f"✨ **Premium Auto-Approve!**\n\n{msg}")
            except: pass
        else:
            try: await client.send_message(user_id, f"🎉 **Badhai Ho!**\n\nAapka bot @{bot_info.username} approve ho gaya hai aur ab live hai.")
            except: pass
        
        logger.info(f"Cloned bot {bot_info.username} for user {user_id}")

    except Exception as e:
        logger.error(f"Error cloning bot: {e}")
        if not instant:
            try: await client.send_message(user_id, f"❌ Error cloning bot: `{e}`")
            except: pass

# ═══════════════════════════════════════════════════════════
# 3. USER COMMANDS: /mybots & /delbot
# ═══════════════════════════════════════════════════════════
@app.on_message(filters.command("mybots") & filters.private)
async def my_bots(client: Client, message: Message):
    user_bots = await cloned_bots.find({"user_id": message.from_user.id}).to_list(length=10)
    if not user_bots:
        return await message.reply_text("❌ Aapka koi clone bot nahi hai. `/clone <token>` se banayein.")
    
    text = "**🤖 Your Bots:**\n\n"
    for i, bot in enumerate(user_bots, 1):
        text += f"{i}. @{bot.get('bot_username', 'Unknown')} (ID: `{bot.get('bot_id')}`)\n"
    text += "\nDelete karne ke liye: `/delbot <bot_id>`"
    await message.reply_text(text)

@app.on_message(filters.command("delbot") & filters.private)
async def delete_bot(client: Client, message: Message):
    if len(message.command) < 2:
        return await message.reply_text("**Usage:** `/delbot <bot_id>`\n\nBot ID `/mybots` se lein.")
    
    try:
        bot_id = int(message.command[1])
    except ValueError:
        return await message.reply_text("❌ **Invalid Bot ID!** Sirf numbers daalein.")
    
    user_bot = await cloned_bots.find_one({"user_id": message.from_user.id, "bot_id": bot_id})
    
    if not user_bot:
        return await message.reply_text("❌ Bot nahi mila ya aap iske owner nahi hain.")
    
    # Stop the bot if running
    if bot_id in active_clones:
        try: await active_clones[bot_id].stop()
        except: pass
        del active_clones[bot_id]
    
    await cloned_bots.delete_one({"bot_id": bot_id})
    await message.reply_text(f"✅ Bot @{user_bot.get('bot_username')} successfully deleted.")

# ═══════════════════════════════════════════════════════════
# 4. OWNER COMMANDS: /addpremium & /rempremium
# ═══════════════════════════════════════════════════════════
@app.on_message(filters.command("addpremium") & filters.user(OWNER_ID))
async def add_premium(client: Client, message: Message):
    if len(message.command) < 2:
        return await message.reply_text("**Usage:** `/addpremium <user_id>`")
    
    try:
        target_id = int(message.command[1])
    except ValueError:
        return await message.reply_text("❌ **Invalid User ID!**")
        
    await premium_users.update_one({"user_id": target_id}, {"$set": {"user_id": target_id}}, upsert=True)
    await message.reply_text(f"✅ User `{target_id}` is now Premium (Limit: {PREMIUM_CLONE_LIMIT} bots).")

@app.on_message(filters.command("rempremium") & filters.user(OWNER_ID))
async def remove_premium(client: Client, message: Message):
    if len(message.command) < 2:
        return await message.reply_text("**Usage:** `/rempremium <user_id>`")
    
    try:
        target_id = int(message.command[1])
    except ValueError:
        return await message.reply_text("❌ **Invalid User ID!**")
        
    await premium_users.delete_one({"user_id": target_id})
    await message.reply_text(f"❌ User `{target_id}` premium removed (Limit: {FREE_CLONE_LIMIT} bot).")

# ═══════════════════════════════════════════════════════════
# 5. START CLONED BOTS ON RESTART (Called from main.py)
# ═══════════════════════════════════════════════════════════
async def start_cloned_bots():
    logger.info("[Clone] Checking Database for cloned bots...")
    async for bot_data in cloned_bots.find({"status": "active"}):
        try:
            client = Client(
                name=f"clone_{bot_data['token'][:10]}",
                api_id=API_ID,
                api_hash=API_HASH,
                bot_token=bot_data["token"],
                plugins={"root": PLUGINS_DIR}
            )
            await client.start()
            active_clones[bot_data["bot_id"]] = client
            logger.info(f"[Clone] Started Bot: @{bot_data.get('bot_username')} (ID: {bot_data['bot_id']})")
        except Exception as e:
            logger.error(f"[Clone] Failed to start bot {bot_data['bot_id']}: {e}")
            # Agar token invalid ho gaya, toh DB se remove kar dein
            if "AccessTokenInvalid" in str(e) or "ApiIdInvalid" in str(e):
                await cloned_bots.delete_one({"bot_id": bot_data["bot_id"]})
                logger.warning(f"[Clone] Removed invalid bot {bot_data['bot_id']} from DB.")
