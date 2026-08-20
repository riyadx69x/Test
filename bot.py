import os
import json
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError

# আপনার my.telegram.org থেকে প্রাপ্ত API_ID এবং API_HASH এখানে দিন
API_ID = 3416690
API_HASH = 'f80db9e0f7d2c57ffec3db21b359d339'

# বোট টোকেন (আপনার বোটের টোকেন এখানে বসাবেন)
BOT_TOKEN = '8873131995:AAHBW19oc4_6TjsPBJhusFJCB1g2VJyKFNQ'

# সেভ করা ডেটা রাখার ফাইল
DATA_FILE = 'saved_accounts.json'

# লোকাল মেমোরি বা ফাইল হ্যান্ডলিং
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

# ক্লায়েন্ট হ্যান্ডেল করার জন্য টেম্পোরারি স্টোরেজ
temp_storage = {}

bot = TelegramClient('bot_session', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    buttons = [
        [Button.inline("➕ New Number Add", data="add_number")],
        [Button.inline("📂 Your Numbers", data="list_numbers")]
    ]
    await event.respond("স্বাগতম! আপনার টেলিগ্রাম অ্যাকাউন্ট সেশন ম্যানেজার বোটে। নিচের অপশন থেকে একটি বেছে নিন:", buttons=buttons)

@bot.on(events.CallbackQuery(data=b'add_number'))
async def ask_number(event):
    sender_id = event.sender_id
    temp_storage[sender_id] = {'step': 'waiting_phone'}
    await event.edit("দয়া করে আপনার টেলিগ্রাম ফোন নম্বরটি কান্ট্রি কোড সহ পাঠান (যেমন: `+88017xxxxxxxx`):")

@bot.on(events.CallbackQuery(data=b'list_numbers'))
async def list_numbers(event):
    sender_id = str(event.sender_id)
    data = load_data()
    
    if sender_id not in data or not data[sender_id]:
        await event.edit("আপনার কোনো অ্যাকাউন্ট সেভ করা নেই।", buttons=[[Button.inline("🔙 Back", data="back_home")]])
        return
    
    buttons = []
    for phone, info in data[sender_id].items():
        country = info.get('country', 'Unknown')
        buttons.append([Button.inline(f"{phone} ({country})", data=f"view_{phone}")])
    
    buttons.append([Button.inline("🔙 Back", data="back_home")])
    await event.edit("আপনার সেভ করা অ্যাকাউন্টগুলোর লিস্ট:", buttons=buttons)

@bot.on(events.CallbackQuery(data=b'back_home'))
async def back_home(event):
    buttons = [
        [Button.inline("➕ New Number Add", data="add_number")],
        [Button.inline("📂 Your Numbers", data="list_numbers")]
    ]
    await event.edit("মূল মেনুতে ফিরে এসেছেন:", buttons=buttons)

@bot.on(events.CallbackQuery(pattern=b'view_'))
async def view_account(event):
    sender_id = str(event.sender_id)
    phone = event.data.decode().replace('view_', '')
    data = load_data()
    
    if sender_id in data and phone in data[sender_id]:
        acc = data[sender_id][phone]
        msg = f"📱 **Number:** {phone}\n🌍 **Country:** {acc.get('country')}\n🔑 **Session String:**\n`{acc.get('session')}`"
        await event.edit(msg, buttons=[[Button.inline("🔙 Back to List", data="list_numbers")]])

@bot.on(events.NewMessage())
async def handle_user_input(event):
    sender_id = event.sender_id
    if sender_id not in temp_storage:
        return
    
    state = temp_storage[sender_id].get('step')
    text = event.raw_text.strip()
    
    if state == 'waiting_phone':
        phone = text
        temp_storage[sender_id]['phone'] = phone
        
        # ক্লায়েন্ট ইনিশিয়ালাইজ করে ওটিপি পাঠানো
        client = TelegramClient(StringSession(), API_ID, API_HASH)
        await client.connect()
        
        try:
            sent = await client.send_code_request(phone)
            temp_storage[sender_id]['client'] = client
            temp_storage[sender_id]['phone_code_hash'] = sent.phone_code_hash
            temp_storage[sender_id]['step'] = 'waiting_otp'
            await event.respond("✅ ওটিপি (OTP) পাঠানো হয়েছে। টেলিগ্রাম অ্যাপে কোডটি পেলে সেটি এখানে দিন:")
        except Exception as e:
            await client.disconnect()
            del temp_storage[sender_id]
            await event.respond(f"❌ ভুল নম্বর বা সমস্যা হয়েছে: {str(e)}")
            
    elif state == 'waiting_otp':
        temp_storage[sender_id]['otp'] = text
        temp_storage[sender_id]['step'] = 'waiting_password_or_done'
        
        client = temp_storage[sender_id]['client']
        phone = temp_storage[sender_id]['phone']
        phone_code_hash = temp_storage[sender_id]['phone_code_hash']
        
        try:
            await client.sign_in(phone, text, phone_code_hash=phone_code_hash)
            await finalize_login(event, sender_id, client, phone)
        except SessionPasswordNeededError:
            await event.respond("🔒 আপনার অ্যাকাউন্টে টু-স্টেপ ভেরিফিকেশন (2FA) পাসওয়ার্ড চালু আছে। আপনার পাসওয়ার্ডটি এখানে দিন:")
        except Exception as e:
            await client.disconnect()
            del temp_storage[sender_id]
            await event.respond(f"❌ লগইন ব্যর্থ হয়েছে: {str(e)}\nদয়া করে `/start` দিয়ে আবার শুরু করুন।")

    elif state == 'waiting_password_or_done':
        password = text
        client = temp_storage[sender_id]['client']
        phone = temp_storage[sender_id]['phone']
        
        try:
            await client.sign_in(password=password)
            await finalize_login(event, sender_id, client, phone)
        except Exception as e:
            await client.disconnect()
            del temp_storage[sender_id]
            await event.respond(f"❌ পাসওয়ার্ড ভুল বা সমস্যা হয়েছে: {str(e)}\nদয়া করে `/start` দিয়ে আবার চেষ্টা করুন।")

async def finalize_login(event, sender_id, client, phone):
    session_string = client.session.save()
    
    # কান্ট্রি ডিটেক্ট করার ছোট্ট লজিক (ফোন নম্বর অনুযায়ী)
    country = "Bangladesh" if phone.startswith("+880") else "International"
    
    # ডেটা সেভ করা
    data = load_data()
    str_sender_id = str(sender_id)
    if str_sender_id not in data:
        data[str_sender_id] = {}
        
    data[str_sender_id][phone] = {
        'session': session_string,
        'country': country
    }
    save_data(data)
    
    await client.disconnect()
    del temp_storage[sender_id]
    
    await event.respond(f"🎉 অভিনন্দন! অ্যাকাউন্ট সফলভাবে সেভ হয়ে গেছে।\n📱 নম্বর: {phone}\n🌍 দেশ: {country}\n\nএখন 'Your Numbers' থেকে এটি দেখতে পারবেন।")

print("Bot is running...")
bot.run_until_disconnected()
