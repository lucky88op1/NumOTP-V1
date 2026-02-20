import sqlite3
import os
from telethon import TelegramClient, events, Button

# --- CONFIGURATION ---
API_ID = 33064462  # Apna API ID dalein
API_HASH = '965778fd87a7901719b1fdb09e95cc1e' # Apna API Hash dalein
BOT_TOKEN = '8574246799:AAFCBxIYaiuoJMCrrM8wurYzz4wS--S5RSY' # Apna Bot Token dalein

ADMIN_ID = 7113666466
BACKUP_LINK = "https://t.me/NumOTPGC"
FSUB_CHANNEL = "TeamOFDark1"

client = TelegramClient('otp_pro_final_v24', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# --- DATABASE SETUP ---
conn = sqlite3.connect('otp_store_v24.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('CREATE TABLE IF NOT EXISTS users (uid INTEGER PRIMARY KEY)')
cursor.execute('''CREATE TABLE IF NOT EXISTS countries 
               (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, service TEXT, code TEXT, stock INTEGER DEFAULT 0)''')
cursor.execute('CREATE TABLE IF NOT EXISTS numbers (number TEXT PRIMARY KEY, country_id INTEGER, status TEXT DEFAULT "available", user_id INTEGER)')
conn.commit()


# --- HELPER: FSUB CHECK ---
async def is_subscribed(uid):
    if uid == ADMIN_ID: return True
    try:
        from telethon.tl.functions.channels import GetParticipantRequest
        await client(GetParticipantRequest(channel=FSUB_CHANNEL, participant=uid))
        return True
    except Exception:
        return False

# --- KEYBOARDS (Error Fix: No Mixing) ---
def get_main_btns(uid):
    btns = [
        [Button.text("📲 Get Number", resize=True), Button.text("🌎 Available Country", resize=True)],
        [Button.text("↗️ OTP Group", resize=True)]
    ]
    if uid == ADMIN_ID:
        btns.append([Button.text("🛠 Admin Panel", resize=True)])
    return btns

def admin_dashboard_inline():
    return [
        [Button.inline("🌍 Country Management", b"c_mng")],
        [Button.inline("➕ Add Service", b"add_c"), Button.inline("📦 Update Stock", b"up_s")],
        [Button.inline("🗑 Remove Service", b"rem_c_menu"), Button.inline("📢 Broadcast", b"bcast")],
        [Button.inline("🏠 Back to Home", b"back_to_main")]
    ]

# --- START ---
@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    uid = event.sender_id
    cursor.execute('INSERT OR IGNORE INTO users (uid) VALUES (?)', (uid,))
    conn.commit()
    
    if not await is_subscribed(uid):
        return await event.reply(
            f"⚠️ **ACCESS DENIED**\n\nIs bot ko use karne ke liye hamare channel ko join karein.",
            buttons=[Button.url("📢 Join Channel", f"https://t.me/{FSUB_CHANNEL}")]
        )
    await event.reply("✨ **WELCOME TO PRO OTP STORE** ✨", buttons=get_main_btns(uid))

# --- TEXT HANDLERS ---
@client.on(events.NewMessage())
async def text_handler(event):
    msg, uid = event.text, event.sender_id
    if not await is_subscribed(uid): return

    if msg == "🛠 Admin Panel" and uid == ADMIN_ID:
        await event.reply("⚙️ **ADMIN DASHBOARD**", buttons=admin_dashboard_inline())
    
    elif msg == "🌎 Available Country":
        cursor.execute('SELECT name, service, stock FROM countries WHERE stock > 0')
        rows = cursor.fetchall()
        res = "📊 **LIVE STOCK STATUS**\n━━━━━━━━━━━━━━━━━━━━\n\n"
        if not rows: res = "❌ Stock Empty."
        else:
            for r in rows: res += f"📍 **{r[0]}** | {r[1]} - Stock: `{r[2]}`\n"
        await event.reply(res)

    elif msg == "📲 Get Number":
        cursor.execute('SELECT id, name, service, stock FROM countries WHERE stock > 0')
        rows = cursor.fetchall()
        if not rows: return await event.reply("❌ No numbers available.")
        btns = [[Button.inline(f"💎 {r[1]} | {r[2]} ({r[3]})", f"buy_{r[0]}".encode())] for r in rows]
        await event.reply("🌍 **Select a service:**", buttons=btns)

    elif msg == "↗️ OTP Group":
        await event.reply(f"🔗 **Group Link:** {BACKUP_LINK}")

# --- CALLBACK HANDLERS ---
@client.on(events.CallbackQuery())
async def callback_handler(event):
    data, uid = event.data, event.sender_id
    if not await is_subscribed(uid): return

    if data == b"back_to_main":
        await event.delete()
        await event.respond("🏠 **Main Menu:**", buttons=get_main_btns(uid))

    elif data == b"c_mng" and uid == ADMIN_ID:
        cursor.execute('SELECT name, service, stock FROM countries')
        rows = cursor.fetchall()
        msg = "📊 **MANAGEMENT**\n━━━━━━━━━━━━━━━━━━━━\n"
        if not rows: msg += "❌ No countries found."
        for r in rows: msg += f"🔹 {r[0]} | {r[1]} | Stock: `{r[2]}`\n"
        await event.edit(msg, buttons=admin_dashboard_inline())

    elif data == b"add_c" and uid == ADMIN_ID:
        async with client.conversation(event.chat_id, timeout=60) as conv:
            await conv.send_message("📝 **Format:** `Country | Service | Code` (Ex: `India | WhatsApp | +91`)")
            try:
                res = await conv.get_response()
                if '|' in res.text:
                    n, s, c = [x.strip() for x in res.text.split('|')]
                    cursor.execute('INSERT INTO countries (name, service, code) VALUES (?, ?, ?)', (n, s, c))
                    conn.commit()
                    await conv.send_message(f"✅ Added: {n} {s}", buttons=admin_dashboard_inline())
            except Exception: await event.respond("❌ Timeout! Try Again.")

    elif data == b"bcast" and uid == ADMIN_ID:
        async with client.conversation(event.chat_id, timeout=120) as conv:
            await conv.send_message("📢 **Bhejiye jo message sabko dena hai:**")
            msg = await conv.get_response()
            cursor.execute('SELECT uid FROM users')
            users = cursor.fetchall()
            for u in users:
                try: await client.send_message(u[0], msg)
                except Exception: pass
            await conv.send_message(f"✅ Broadcast complete!")

    elif data.startswith(b"buy_"):
        c_id = data.decode().split('_')[1]
        cursor.execute('SELECT number FROM numbers WHERE country_id=? AND status="available" LIMIT 1', (c_id,))
        res = cursor.fetchone()
        if res:
            num = res[0]
            cursor.execute('UPDATE numbers SET status="active", user_id=? WHERE number=?', (uid, num))
            cursor.execute('UPDATE countries SET stock = stock - 1 WHERE id=?', (c_id,))
            conn.commit()
            user_btns = [
                [Button.inline("🔄 Change Number", f"buy_{c_id}".encode())],
                [Button.inline("🌍 Change Country", b"change_c")],
                [Button.url("↗️ View OTP", BACKUP_LINK)]
            ]
            await event.edit(f"✅ **Assigned:** `{num}`", buttons=user_btns)
        else: await event.answer("❌ Stock Empty!", alert=True)

    elif data == b"change_c":
        cursor.execute('SELECT id, name, service, stock FROM countries WHERE stock > 0')
        rows = cursor.fetchall()
        btns = [[Button.inline(f"💎 {r[1]} | {r[2]} ({r[3]})", f"buy_{r[0]}".encode())] for r in rows]
        await event.edit("🌍 **Select New Service:**", buttons=btns)

    elif data == b"up_s" and uid == ADMIN_ID:
        cursor.execute('SELECT id, name, service FROM countries')
        rows = cursor.fetchall()
        if not rows: return await event.answer("❌ No service added.", alert=True)
        btns = [[Button.inline(f"➕ {r[1]} ({r[2]})", f"addto_{r[0]}".encode())] for r in rows]
        await event.edit("📦 **Update Stock:**", buttons=btns)

    elif data.startswith(b"addto_") and uid == ADMIN_ID:
        c_id = data.decode().split('_')[1]
        async with client.conversation(event.chat_id, timeout=300) as conv:
            await conv.send_message("📂 **Upload `.txt` file.**")
            try:
                file = await conv.get_response()
                path = await client.download_media(file.document)
                added = 0
                with open(path, 'r') as f:
                    for line in f:
                        if line.strip():
                            cursor.execute('INSERT OR IGNORE INTO numbers (number, country_id) VALUES (?, ?)', (line.strip(), c_id))
                            cursor.execute('UPDATE countries SET stock = stock + 1 WHERE id=?', (c_id,))
                            added += 1
                conn.commit()
                os.remove(path)
                await conv.send_message(f"✅ {added} Numbers Added!", buttons=admin_dashboard_inline())
            except Exception: await event.respond("❌ Error processing file.")

    elif data == b"rem_c_menu" and uid == ADMIN_ID:
        cursor.execute('SELECT id, name, service FROM countries')
        rows = cursor.fetchall()
        if not rows: return await event.answer("❌ Empty!", alert=True)
        btns = [[Button.inline(f"❌ Del {r[1]} ({r[2]})", f"del_{r[0]}".encode())] for r in rows]
        await event.edit("⚠️ **Delete Service?**", buttons=btns)

    elif data.startswith(b"del_") and uid == ADMIN_ID:
        c_id = data.decode().split('_')[1]
        cursor.execute('DELETE FROM countries WHERE id=?', (c_id,))
        cursor.execute('DELETE FROM numbers WHERE country_id=?', (c_id,))
        conn.commit()
        await event.answer("✅ Removed!", alert=True)
        await event.edit("⚙️ **ADMIN DASHBOARD**", buttons=admin_dashboard_inline())

print("🚀 Pro Bot is Live!")
client.run_until_disconnected()
