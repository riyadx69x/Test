import os
import json
import re
from datetime import datetime, timezone, timedelta
from telethon import TelegramClient, events
from telethon.tl.custom import Button
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError

API_ID = 34166690
API_HASH = 'f80db9e0f7d2c57ffec3db21b359d339'
BOT_TOKEN = '8873131995:AAHBW19oc4_6TjsPBJhusFJCB1g2VJyKFNQ'

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

def get_country_name(phone):
    if phone.startswith("+880") or phone.startswith("880"):
        return "Bangladesh 🇧🇩"
    elif phone.startswith("+91") or phone.startswith("91"):
        return "India 🇮🇳"
    elif phone.startswith("+92") or phone.startswith("92"):
        return "Pakistan 🇵🇰"
    elif phone.startswith("+60") or phone.startswith("60"):
        return "Malaysia 🇲🇾"
    elif phone.startswith("+62") or phone.startswith("62"):
        return "Indonesia 🇮🇳"
    elif phone.startswith("+1") or phone.startswith("1"):
        return "USA/Canada 🇺🇸"
    elif phone.startswith("+44") or phone.startswith("44"):
        return "UK 🇬🇧"
    else:
        return "International 🌍"

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
async def list_countries(event):
    sender_id = str(event.sender_id)
    data = load_data()
    
    if sender_id not in data or not data[sender_id]:
        await event.respond("আপনার কোনো অ্যাকাউন্ট সেভ করা নেই।", buttons=main_menu_keyboard())
        return
    
    user_accounts = data[sender_id]
    valid_accounts = {}
    
    for phone, info in user_accounts.items():
        session_str = info.get('session')
        try:
            temp_client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
            await temp_client.connect()
            if await temp_client.is_user_authorized():
                valid_accounts[phone] = info
            await temp_client.disconnect()
        except:
            pass
            
    if len(valid_accounts) != len(user_accounts):
        data[sender_id] = valid_accounts
        save_data(data)
        
    if not valid_accounts:
        await event.respond("আপনার সেভ করা সব অ্যাকাউন্ট টেলিগ্রাম থেকে লগআউট হয়ে গেছে, তাই লিস্ট খালি।", buttons=main_menu_keyboard())
        return

    countries = {}
    for phone, info in valid_accounts.items():
        country = info.get('country', 'International 🌍')
        if country not in countries:
            countries[country] = []
        countries[country].append(phone)
    
    buttons = []
    for country in countries.keys():
        count = len(countries[country])
        buttons.append([Button.inline(f"{country} ({count} Numbers)", data=f"country_{country}")])
    
    await event.respond("আপনার সেভ করা দেশগুলোর লিস্ট নিচে দেওয়া হলো:", buttons=buttons)

@bot.on(events.CallbackQuery(pattern=b'country_'))
async def list_numbers_by_country(event):
    sender_id = str(event.sender_id)
    selected_country = event.data.decode().replace('country_', '')
    data = load_data()
    
    if sender_id in data:
        buttons = []
        for phone, info in data[sender_id].items():
            if info.get('country') == selected_country:
                buttons.append([Button.inline(f"📱 {phone}", data=f"getnum_{phone}")])
        
        buttons.append([Button.inline("🔙 Back to Countries", data="back_countries")])
        await event.edit(f"📂 **{selected_country}** এর আন্ডারে থাকা নম্বরগুলো:", buttons=buttons)

@bot.on(events.CallbackQuery(pattern=b'back_countries'))
async def back_to_countries(event):
    sender_id = str(event.sender_id)
    data = load_data()
    if sender_id not in data:
        return
    
    countries = {}
    for phone, info in data[sender_id].items():
        country = info.get('country', 'International 🌍')
        if country not in countries:
            countries[country] = []
        countries[country].append(phone)
    
    buttons = []
    for country in countries.keys():
        count = len(countries[country])
        buttons.append([Button.inline(f"{country} ({count} Numbers)", data=f"country_{country}")])
    
    await event.edit("আপনার সেভ করা দেশগুলোর লিস্ট নিচে দেওয়া হলো:", buttons=buttons)

@bot.on(events.CallbackQuery(pattern=b'getnum_'))
async def send_phone_number(event):
    sender_id = str(event.sender_id)
    phone = event.data.decode().replace('getnum_', '')
    data = load_data()
    
    if sender_id in data and phone in data[sender_id]:
        session_str = data[sender_id][phone]['session']
        
        otp_code = None
        try:
            client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
            await client.connect()
            
            async for message in client.iter_messages(777000, limit=1):
                if message.date:
                    now = datetime.now(timezone.utc)
                    message_time = message.date
                    
                    # ৫ মিনিটের ভেতরের মেসেজ কিনা চেক করা
                    if (now - message_time) <= timedelta(minutes=5):
                        text = message.text
                        match = re.search(r'\b\d{5,6}\b', text)
                        if match:
                            otp_code = match.group(0)
                        else:
                            numbers = re.findall(r'\d+', text)
                            if numbers:
                                otp_code = numbers[0]
            
            await client.disconnect()
        except Exception as e:
            pass

        if otp_code:
            await event.respond(f"📱 নম্বর: `{phone}`\n\n🔑 **নতুন ওটিপি কোড:** `{otp_code}`")
        else:
            await event.respond(f"📱 নম্বর: `{phone}`\n\n⏳ গত ৫ মিনিটের মধ্যে এই নাম্বারে কোনো নতুন ওটিপি আসেনি।")
    else:
        await event.answer("নম্বর পাওয়া যায়নি বা লগআউট হয়ে গেছে!", alert=True)

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
        phone = text if text.startswith("+") else "+" + text
        temp_storage[sender_id]['phone'] = phone
        
        waiting_msg = await event.respond("⏳ **Waiting for otp...**")
        
        client = TelegramClient(StringSession(), API_ID, API_HASH)
        await client.connect()
        
        try:
            sent = await client.send_code_request(phone)
            temp_storage[sender_id]['client'] = client
            temp_storage[sender_id]['phone_code_hash'] = sent.phone_code_hash
            temp_storage[sender_id]['step'] = 'waiting_otp'
            await waiting_msg.edit("✅ ওটিপি পাঠানো হয়েছে। আপনার টেলিগ্রাম অ্যাপে কোডটি আসলে সেটি এখানে দিন:")
        except Exception as e:
            await client.disconnect()
            del temp_storage[sender_id]
            await waiting_msg.edit(f"❌ সমস্যা হয়েছে: {str(e)}")
            
    elif state == 'waiting_otp':
        client = temp_storage[sender_id]['client']
        phone = temp_storage[sender_id]['phone']
        phone_code_hash = temp_storage[sender_id]['phone_code_hash']
        
        try:
            await client.sign_in(phone, text, phone_code_hash=phone_code_hash)
            await finalize_login(event, sender_id, client, phone)
        except SessionPasswordNeededError:
            temp_storage[sender_id]['step'] = 'waiting_password'
            await event.respond("🔒 টু-স্টেপ ভেরিফিকেশন পাসওয়ার্ড দিন:")
        except Exception as e:
            await event.respond(f"❌ ওটিপি ভুল হয়েছে ({str(e)})। আবার সঠিক কোড দিন:")

    elif state == 'waiting_password':
        client = temp_storage[sender_id]['client']
        phone = temp_storage[sender_id]['phone']
        
        try:
            await client.sign_in(password=text)
            await finalize_login(event, sender_id, client, phone)
        except Exception as e:
            await event.respond(f"❌ পাসওয়ার্ড ভুল: {str(e)}\nআবার সঠিক পাসওয়ার্ড দিন:")

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
    if sender_id in temp_storage:
        del temp_storage[sender_id]
    
    await event.respond(
        f"🎉 অভিনন্দন! অ্যাকাউন্ট সফলভাবে সেভ হয়ে গেছে।\n🌍 দেশ: {country}\n📱 নম্বর: `{phone}`",
        buttons=main_menu_keyboard()
    )

print("Bot is running...")
bot.run_until_disconnected()
