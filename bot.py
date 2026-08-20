import os
import json
from telethon import TelegramClient, events
from telethon.tl.custom import Button
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError

# সঠিক API_ID এবং API_HASH
API_ID = 34166690
API_HASH = 'f80db9e0f7d2c57ffec3db21b359d339'

# আপনার টেলিগ্রাম বট টোকেন
BOT_TOKEN = '8873131995:AAHBW19oc4_6TjsPBJhusFJCB1g2VJyKFNQ'

# সেভ করা ডেটা রাখার ফাইল
DATA_FILE = 'saved_accounts.json'

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

temp_storage = {}

bot = TelegramClient('bot_session', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# কান্ট্রি কোড থেকে সুন্দর নাম ও ফ্ল্যাগ বের করার ফাংশন
def get_country_name(phone):
    if phone.startswith("+880"):
        return "Bangladesh 🇧🇩"
    elif phone.startswith("+91"):
        return "India 🇮🇳"
    elif phone.startswith("+92"):
        return "Pakistan 🇵🇰"
    elif phone.startswith("+60"):
        return "Malaysia 🇲🇾"
    elif phone.startswith("+62"):
        return "Indonesia 🇮🇩"
    elif phone.startswith("+1"):
        return "USA/Canada 🇺🇸"
    elif phone.startswith("+44"):
        return "UK 🇬🇧"
    else:
        return "International 🌍"

# পার্মানেন্ট নিচের কিবোর্ড বাটন (Reply Keyboard)
def main_menu_keyboard():
    return [
        [Button.text("➕ New Number Add", resize=True)],
        [Button.text("📂 Your Numbers", resize=True)]
    ]

@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    await event.respond(
        "স্বাগতম! আপনার টেলিগ্রাম অ্যাকাউন্ট সেশন ম্যানেজার বোটে। নিচের মেনু থেকে অপশন বেছে নিন:",
        buttons=main_menu_keyboard()
    )

@bot.on(events.NewMessage(pattern='➕ New Number Add'))
async def ask_number(event):
    sender_id = event.sender_id
    temp_storage[sender_id] = {'step': 'waiting_phone'}
    await event.respond("দয়া করে আপনার টেলিগ্রাম ফোন নম্বরটি কান্ট্রি কোড সহ পাঠান (যেমন: `+88017xxxxxxxx`):")

@bot.on(events.NewMessage(pattern='📂 Your Numbers'))
async def list_numbers(event):
    sender_id = str(event.sender_id)
    data = load_data()
    
    if sender_id not in data or not data[sender_id]:
        await event.respond("আপনার কোনো অ্যাকাউন্ট সেভ করা নেই।", buttons=main_menu_keyboard())
        return
    
    buttons = []
    for phone, info in data[sender_id].items():
        country = info.get('country', 'Unknown')
        # বাটনে শুধু কান্ট্রি নেম দেখাবে
        buttons.append([Button.inline(f"{country}", data=f"getnum_{phone}")])
    
    await event.respond("আপনার সেভ করা দেশগুলোর লিস্ট নিচে দেওয়া হলো (ক্লিক করলে নম্বর দেখতে পাবেন):", buttons=buttons)

@bot.on(events.CallbackQuery(pattern=b'getnum_'))
async def send_phone_number(event):
    sender_id = str(event.sender_id)
    phone = event.data.decode().replace('getnum_', '')
    data = load_data()
    
    if sender_id in data and phone in data[sender_id]:
        # ইউজার যেন সহজে ১ ক্লিকে কপি করতে পারে, তাই কোড ব্লক (```) আকারে নম্বরটি পাঠানো হচ্ছে
        await event.respond(f"📱 আপনার সেভ করা নম্বর:\n`{phone}`")
    else:
        await event.answer("নম্বর পাওয়া যায়নি!", alert=True)

@bot.on(events.NewMessage())
async def handle_user_input(event):
    text = event.raw_text.strip()
    if text in ['➕ New Number Add', '📂 Your Numbers', '/start']:
        return

    sender_id = event.sender_id
    if sender_id not in temp_storage:
        return
    
    state = temp_storage[sender_id].get('step')
    
    if state == 'waiting_phone':
        phone = text
        temp_storage[sender_id]['phone'] = phone
        
        waiting_msg = await event.respond("⏳ **Waiting for otp...**")
        
        client = TelegramClient(StringSession(), API_ID, API_HASH)
        await client.connect()
        
        try:
            sent = await client.send_code_request(phone)
            temp_storage[sender_id]['client'] = client
            temp_storage[sender_id]['phone_code_hash'] = sent.phone_code_hash
            temp_storage[sender_id]['step'] = 'waiting_otp'
            await waiting_msg.edit("✅ ওটিপি (OTP) পাঠানো হয়েছে। টেলিগ্রাম অ্যাপে কোডটি পেলে সেটি এখানে দিন:")
        except Exception as e:
            await client.disconnect()
            del temp_storage[sender_id]
            await waiting_msg.edit(f"❌ ভুল নম্বর বা সমস্যা হয়েছে: {str(e)}")
            
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
            await event.respond(f"❌ লগইন ব্যর্থ হয়েছে: {str(e)}\nদয়া করে আবার চেষ্টা করুন।", buttons=main_menu_keyboard())

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
            await event.respond(f"❌ পাসওয়ার্ড ভুল বা সমস্যা হয়েছে: {str(e)}\nদয়া করে আবার চেষ্টা করুন।", buttons=main_menu_keyboard())

async def finalize_login(event, sender_id, client, phone):
    session_string = client.session.save()
    
    country = get_country_name(phone)
    
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
    
    await event.respond(
        f"🎉 অভিনন্দন! অ্যাকাউন্ট সফলভাবে সেভ হয়ে গেছে।\n🌍 দেশ: {country}\n📱 নম্বর: `{phone}`",
        buttons=main_menu_keyboard()
    )

print("Bot is running...")
bot.run_until_disconnected()
