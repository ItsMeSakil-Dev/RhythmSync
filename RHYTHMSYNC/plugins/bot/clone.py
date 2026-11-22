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
import qrcode
from io import BytesIO
import razorpay
from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import AccessTokenInvalid, AuthKeyUnregistered
from motor.motor_asyncio import AsyncIOMotorClient
from RHYTHMSYNC import app
from config import MONGO_DB_URI, API_ID, API_HASH, OWNER_ID

logger = logging.getLogger("RHYTHMSYNC.clone")

# --- RAZORPAY & UPI CONFIGURATION ---
RAZORPAY_KEY = os.environ.get("RAZORPAY_KEY_ID", "")
RAZORPAY_SECRET = os.environ.get("RAZORPAY_KEY_SECRET", "")
UPI_ID = os.environ.get("UPI_ID", "yourupi@paytm")

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
FREE_CLONE_LIMIT = 0
PREMIUM_CLONE_LIMIT = 3
PREMIUM_PRICE_RS = 99
user_states = {}

# ═══════════════════════════════════════════════════════════
# 💎 /buypremium COMMAND (Direct QR & UPI in Telegram)
# ═══════════════════════════════════════════════════════════
@app.on_message(filters.command(["buypremium", "premium"]) & filters.private)
async def buy_premium(client: Client, message: Message):
    user_id = message.from_user.id
    
    is_premium = await premium_users.find_one({"user_id": user_id})
    if is_premium:
        return await message.reply_text("✅ **Aap pehle se Premium user hain!**")

    if not razorpay_client:
        return await message.reply_text("⚠️ **Payment Gateway Configure Nahi Hai.**")

    user_states[user_id] = {"step": "WAITING_NAME"}
    await message.reply_text("💎 **RhythmSync Premium**\n\nQR Code aur UPI ID generate karne ke liye apna **Real Name** (English mein) bhejein.")

# ═══════════════════════════════════════════════════════════
# 🧠 STATE HANDLER (Name -> Razorpay QR Generation)
# ═══════════════════════════════════════════════════════════
@app.on_message(filters.private & filters.text & ~filters.regex(r"^/"))
async def handle_user_states(client: Client, message: Message):
    user_id = message.from_user.id
    if user_id not in user_states:
        return
        
    current_step = user_states[user_id].get("step")
    text = message.text.strip()

    if current_step == "WAITING_NAME":
        clean_name = re.sub(r'[^a-zA-Z0-9\s]', '', text).strip()
        if len(clean_name) < 2:
            return await message.reply_text("❌ **Invalid Name!** Kripya sahi naam bhejein.")

        status_msg = await message.reply_text("⏳ **Generating Unique QR & UPI ID...**")

        try:
            # 1. Razorpay Payment Link Create Karein (Isse unique QR/UPI milega)
            payment_link = razorpay_client.payment_link.create({
                "amount": PREMIUM_PRICE_RS * 100,  # ₹99
                "currency": "INR",
                "accept_partial": False,
                "description": f"RhythmSync Premium - {clean_name}",
                "customer": {
                    "name": clean_name,
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

            # 2. QR Code Generate Karein (Razorpay ke payment link ka)
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(pay_url)
            qr.make(fit=True)
            qr_img = qr.make_image(fill_color="black", back_color="white")
            
            bio = BytesIO()
            qr_img.save(bio, format="PNG")
            bio.seek(0)
            bio.name = "razorpay_qr.png"

            # 3. Buttons (UPI ID Copy + Check Status)
            buttons = InlineKeyboardMarkup([
                [InlineKeyboardButton("💳 Pay on Razorpay (UPI/Card)", url=pay_url)],
                [InlineKeyboardButton("🔄 Check Payment Status", callback_data=f"check_pay_{payment_id}")]
            ])

            caption_text = (
                f"💎 **RhythmSync Premium**\n\n"
                f"**👤 Name:** {clean_name}\n"
                f"**💰 Amount:** ₹{PREMIUM_PRICE_RS}\n\n"
                f"**📱 QR Code scan karein** ya **UPI ID** par pay karein:\n"
                f"**UPI ID:** `{UPI_ID}`\n\n"
                f"_(Payment successful hote hi premium auto-activate ho jayega)_"
            )

            await status_msg.delete()
            await message.reply_photo(
                photo=bio,
                caption=caption_text,
                reply_markup=buttons
            )

            user_states[user_id] = {
                "step": "WAITING_PAYMENT",
                "payment_id": payment_id
            }

        except Exception as e:
            logger.error(f"QR Generation Error: {e}")
            await status_msg.edit_text(f"❌ **Error:** `{e}`")

# ═══════════════════════════════════════════════════════════
# 🔄 CHECK PAYMENT STATUS (Manual Check via Webhook)
# ═══════════════════════════════════════════════════════════
@app.on_callback_query(filters.regex(r"^check_pay_"))
async def check_payment_status(client: Client, query: CallbackQuery):
    user_id = query.from_user.id
    is_premium = await premium_users.find_one({"user_id": user_id})
    
    if is_premium:
        await query.message.edit_text("✅ **Payment Successful!**\n\nAap ab Premium hain. `/clone` bhej kar bot banayein.")
        return await query.answer("Premium Active!", show_alert=True)
    
    await query.answer("⚠️ Payment abhi receive nahi hui. Kripya payment complete karein ya 1-2 min wait karein.", show_alert=True)

# ═══════════════════════════════════════════════════════════
# 🤖 /clone COMMAND (Premium Only)
# ═══════════════════════════════════════════════════════════
@app.on_message(filters.command("clone") & filters.private)
async def request_clone(client: Client, message: Message):
    user_id = message.from_user.id

    is_premium = await premium_users.find_one({"user_id": user_id})
    
    if not is_premium:
        return await message.reply_text(
            "🔒 **Clone Feature is Premium Only!**\n\n"
            f"SIRF ₹{PREMIUM_PRICE_RS} mein Premium kharid kar apna bot banayein.\n"
            "👉 Premium kharidne ke liye **/buypremium** bhejein."
        )

    user_bots = await cloned_bots.count_documents({"user_id": user_id})
    if user_bots >= PREMIUM_CLONE_LIMIT:
        return await message.reply_text(f"❌ **Limit Reached!** Aapne {PREMIUM_CLONE_LIMIT} bots bana liye hain.")

    user_states[user_id] = {"step": "WAITING_TOKEN"}
    await message.reply_text("🤖 **Cloning Started!**\n\n**Step 1:** Apna **Bot Token** bhejein (@BotFather se).\n❌ _Cancel: `/cancel`_")

# ... (Baaki clone process, /mybots, /delbot, /addpremium, start_cloned_bots code same rahega) ...
