import telebot
from telebot.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ChatPermissions, ReplyKeyboardMarkup, KeyboardButton,
    ReplyKeyboardRemove
)
import os
import requests
import json
import time
import re
import sqlite3
from datetime import datetime, timedelta
from threading import Thread
from flask import Flask

# ═══════════════════════════════════════════
#         🌐 Flask برای Render
# ═══════════════════════════════════════════
app = Flask(__name__)

@app.route('/')
def home():
    return '🔥 SFOR Bot is running!'

def run_flask():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

Thread(target=run_flask, daemon=True).start()

# ═══════════════════════════════════════════
#              ⚙️ تنظیمات اصلی
# ═══════════════════════════════════════════
TOKEN = os.environ.get('BOT_TOKEN', '')
ADMIN_ID = 7533340777
SITE_URL = 'https://sfor.onrender.com'
GROK_API_KEY = os.environ.get('GROK_API_KEY', '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')
GROK_URL = 'https://api.groq.com/openai/v1/chat/completions'
BOT_VERSION = '2.0.0'

bot = telebot.TeleBot(TOKEN)

# ═══════════════════════════════════════════
#              🗄️ پایگاه داده
# ═══════════════════════════════════════════
def init_db():
    conn = sqlite3.connect('sfor_bot.db')
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        joined_at TEXT,
        is_banned INTEGER DEFAULT 0,
        message_count INTEGER DEFAULT 0
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS groups (
        id INTEGER PRIMARY KEY,
        title TEXT,
        joined_at TEXT,
        anti_link INTEGER DEFAULT 1,
        anti_spam INTEGER DEFAULT 1,
        welcome INTEGER DEFAULT 1,
        ai_reply INTEGER DEFAULT 0,
        warn_limit INTEGER DEFAULT 3
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS warns (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        group_id INTEGER,
        reason TEXT,
        warned_at TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS auto_replies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        keyword TEXT,
        response TEXT,
        match_type TEXT DEFAULT 'contains'
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_type TEXT,
        user_id INTEGER,
        group_id INTEGER,
        detail TEXT,
        created_at TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS spam_track (
        user_id INTEGER,
        group_id INTEGER,
        message_count INTEGER DEFAULT 0,
        last_message TEXT,
        PRIMARY KEY (user_id, group_id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS user_configs (
        user_id INTEGER PRIMARY KEY,
        given_at TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS user_vpns (
        user_id INTEGER PRIMARY KEY,
        given_at TEXT
    )''')

    conn.commit()
    conn.close()

init_db()

# ═══════════════════════════════════════════
#         🗄️ توابع پایگاه داده
# ═══════════════════════════════════════════
def db():
    return sqlite3.connect('sfor_bot.db')

def add_user(user):
    conn = db()
    c = conn.cursor()
    c.execute('''INSERT OR IGNORE INTO users (id, username, first_name, joined_at)
                 VALUES (?, ?, ?, ?)''',
              (user.id, user.username, user.first_name, datetime.now().isoformat()))
    c.execute('''UPDATE users SET username=?, first_name=?, message_count=message_count+1
                 WHERE id=?''', (user.username, user.first_name, user.id))
    conn.commit()
    conn.close()

def add_group(chat):
    conn = db()
    c = conn.cursor()
    c.execute('''INSERT OR IGNORE INTO groups (id, title, joined_at)
                 VALUES (?, ?, ?)''',
              (chat.id, chat.title, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_group(group_id):
    conn = db()
    c = conn.cursor()
    c.execute('SELECT * FROM groups WHERE id=?', (group_id,))
    row = c.fetchone()
    conn.close()
    return row

def update_group_setting(group_id, setting, value):
    conn = db()
    c = conn.cursor()
    c.execute(f'UPDATE groups SET {setting}=? WHERE id=?', (value, group_id))
    conn.commit()
    conn.close()

def get_stats():
    conn = db()
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM users')
    users = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM groups')
    groups = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM users WHERE is_banned=1')
    banned = c.fetchone()[0]
    c.execute('SELECT SUM(message_count) FROM users')
    msgs = c.fetchone()[0] or 0
    c.execute('SELECT COUNT(*) FROM warns')
    warns = c.fetchone()[0]
    conn.close()
    return users, groups, banned, msgs, warns

def add_warn(user_id, group_id, reason):
    conn = db()
    c = conn.cursor()
    c.execute('INSERT INTO warns (user_id, group_id, reason, warned_at) VALUES (?,?,?,?)',
              (user_id, group_id, reason, datetime.now().isoformat()))
    c.execute('SELECT COUNT(*) FROM warns WHERE user_id=? AND group_id=?', (user_id, group_id))
    count = c.fetchone()[0]
    conn.commit()
    conn.close()
    return count

def get_warns(user_id, group_id):
    conn = db()
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM warns WHERE user_id=? AND group_id=?', (user_id, group_id))
    count = c.fetchone()[0]
    conn.close()
    return count

def clear_warns(user_id, group_id):
    conn = db()
    c = conn.cursor()
    c.execute('DELETE FROM warns WHERE user_id=? AND group_id=?', (user_id, group_id))
    conn.commit()
    conn.close()

def log_event(event_type, user_id=None, group_id=None, detail=None):
    conn = db()
    c = conn.cursor()
    c.execute('INSERT INTO logs (event_type, user_id, group_id, detail, created_at) VALUES (?,?,?,?,?)',
              (event_type, user_id, group_id, detail, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def check_spam(user_id, group_id, msg_text):
    conn = db()
    c = conn.cursor()
    c.execute('SELECT message_count, last_message FROM spam_track WHERE user_id=? AND group_id=?',
              (user_id, group_id))
    row = c.fetchone()
    if row:
        count, last = row
        if last == msg_text:
            count += 1
        else:
            count = 1
        c.execute('UPDATE spam_track SET message_count=?, last_message=? WHERE user_id=? AND group_id=?',
                  (count, msg_text, user_id, group_id))
    else:
        count = 1
        c.execute('INSERT INTO spam_track VALUES (?,?,?,?)', (user_id, group_id, 1, msg_text))
    conn.commit()
    conn.close()
    return count

def ban_user(user_id):
    conn = db()
    c = conn.cursor()
    c.execute('UPDATE users SET is_banned=1 WHERE id=?', (user_id,))
    conn.commit()
    conn.close()

def unban_user(user_id):
    conn = db()
    c = conn.cursor()
    c.execute('UPDATE users SET is_banned=0 WHERE id=?', (user_id,))
    conn.commit()
    conn.close()

def get_auto_replies():
    conn = db()
    c = conn.cursor()
    c.execute('SELECT keyword, response, match_type FROM auto_replies')
    rows = c.fetchall()
    conn.close()
    return rows

def add_auto_reply(keyword, response, match_type='contains'):
    conn = db()
    c = conn.cursor()
    c.execute('INSERT INTO auto_replies (keyword, response, match_type) VALUES (?,?,?)',
              (keyword, response, match_type))
    conn.commit()
    conn.close()

def delete_auto_reply(keyword):
    conn = db()
    c = conn.cursor()
    c.execute('DELETE FROM auto_replies WHERE keyword=?', (keyword,))
    conn.commit()
    conn.close()

def get_all_users():
    conn = db()
    c = conn.cursor()
    c.execute('SELECT id FROM users WHERE is_banned=0')
    rows = c.fetchall()
    conn.close()
    return [r[0] for r in rows]

# ═══════════════════════════════════════════
#         🔒 کانفیگ‌های V2Ray
# ═══════════════════════════════════════════
V2RAY_CONFIGS = """vless://d0cfc134-447c-4c84-965a-ff5f827c9016@116.203.60.171:8080?security=none&type=tcp#SFOR-1
trojan://humanity@188.114.97.6:443?path=%2Fassignment&security=tls&host=www.calmloud.com&type=ws&sni=www.calmloud.com#SFOR-2
trojan://humanity@212.183.88.136:443?path=%2Fassignment&security=tls&host=www.calmlunch.com&type=ws&sni=www.calmlunch.com#SFOR-3
vless://e65c9135-5c62-4e63-9bec-bca0cdf94f52@167.172.108.83:443?security=reality&encryption=none&pbk=YIwwnfgqZKzbdxD0Mq-PiOmIDPYCvkaptHyN_HzDgFA&headerType=none&fp=firefox&spx=%2FwkBfIEIhNxYDFMj&type=tcp&flow=xtls-rprx-vision&sni=icloud.com&sid=844282e475538c#SFOR-4
trojan://Masir_Sefid@188.213.130.212:443?security=reality&pbk=w0XepGv1Hk0gBh1Apiw-nvn8SfzjWcDuxdxN1mpaF3g&headerType=none&fp=chrome&type=tcp&sni=store.steampowered.com&sid=6ced01fc4aa417#SFOR-5
vless://6ca8ea5b-e47f-4c19-adee-365456e1e87c@31.56.188.78:7443?security=reality&encryption=none&pbk=5QAO98ot2U7TcGs_f6EEaQjCzNOJLNHqPf6smYsdFVI&headerType=none&fp=firefox&type=tcp&flow=xtls-rprx-vision&sni=mi.com&sid=be0ce047#SFOR-6
vless://ad6d51ab-2d06-4d41-85b7-da9d703ea4fd@dnn4.avaaaal.ir:2087?path=%2F720f09dba195549b424f771551162528%2Fworkers%2Fservices6%2Fview6%2FAvaal6%2Fproduction6%2Fsettings&security=tls&alpn=http%2F1.1&encryption=none&host=sv333.avaaal.ir&fp=random&type=ws&sni=sv333.avaaal.ir#SFOR-7
vless://8dc7722c-2767-4eea-a28b-2f8daacc07e3@sca17.myfymain.com:8880?mode=gun&security=&encryption=none&type=grpc#SFOR-8
vless://8dc7722c-2767-4eea-a28b-2f8daacc07e3@sca22.myfymain.com:8880?security=&encryption=none&type=grpc#SFOR-9
vless://931729a8-3c20-4841-89a1-f18dc9ce0a6f@46.229.243.137:8443?security=tls&encryption=none&type=tcp&sni=cdn7-09.vk-cdnvideo.com#SFOR-10
vless://da48859d-edf9-4a8c-a026-80910591f284@nytimes.com:80?mode=auto&path=%2FTignal&security=&encryption=none&host=tignaltofansv8.global.ssl.fastly.net&type=xhttp#SFOR-11
vless://0058c215-ab1e-400c-a403-b5b2fda7e846@199.232.197.131:80?path=%2F&security=&encryption=none&host=max-gb1.global.ssl.fastly.net&type=ws#SFOR-12
vless://8dc7722c-2767-4eea-a28b-2f8daacc07e3@sca21.myfymain.com:8880?mode=gun&security=&encryption=none&type=grpc#SFOR-13"""

# نام فایل‌های VPN (باید در همان دایرکتوری ربات باشن)
VPN_FILES = [
    'SFOR-Free-1.npvt',
    'SFOR-Free-2.npvt',
    'SFOR-Saman.npvt',
    'SFOR-IR98.npvt',
    'SFOR-Storm.npvt',
]

def has_received_config(user_id):
    conn = db()
    c = conn.cursor()
    c.execute('SELECT 1 FROM user_configs WHERE user_id=?', (user_id,))
    result = c.fetchone()
    conn.close()
    return result is not None

def mark_config_given(user_id):
    conn = db()
    c = conn.cursor()
    c.execute('INSERT OR IGNORE INTO user_configs (user_id, given_at) VALUES (?,?)',
              (user_id, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def has_received_vpn(user_id):
    conn = db()
    c = conn.cursor()
    c.execute('SELECT 1 FROM user_vpns WHERE user_id=?', (user_id,))
    result = c.fetchone()
    conn.close()
    return result is not None

def mark_vpn_given(user_id):
    conn = db()
    c = conn.cursor()
    c.execute('INSERT OR IGNORE INTO user_vpns (user_id, given_at) VALUES (?,?)',
              (user_id, datetime.now().isoformat()))
    conn.commit()
    conn.close()

# ═══════════════════════════════════════════
#         🤖 هوش مصنوعی Grok
# ═══════════════════════════════════════════
user_ai_history = {}

SYSTEM_PROMPT = """تو یه دستیار هوشمند فارسی‌زبان برای ربات SFOR هستی.
SFOR یه پلتفرم ابزارهای هک، امنیت دیجیتال و فناوری‌ه.
با لحن دوستانه، حرفه‌ای و مختصر جواب بده.
اگه سوال فنی بود، دقیق و با مثال توضیح بده.
از ایموجی مناسب استفاده کن."""

def ask_ai(user_id, message, use_history=True):
    if user_id not in user_ai_history:
        user_ai_history[user_id] = []

    user_ai_history[user_id].append({"role": "user", "content": message})

    if len(user_ai_history[user_id]) > 10:
        user_ai_history[user_id] = user_ai_history[user_id][-10:]

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if use_history:
        messages += user_ai_history[user_id]
    else:
        messages.append({"role": "user", "content": message})

    try:
        response = requests.post(
            GROK_URL,
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {GROK_API_KEY}'
            },
            json={
                'model': 'llama-3.3-70b-versatile',
                'messages': messages,
                'max_tokens': 1000,
                'temperature': 0.7
            },
            timeout=30
        )
        data = response.json()
        if 'choices' in data:
            reply = data['choices'][0]['message']['content']
            user_ai_history[user_id].append({"role": "assistant", "content": reply})
            return reply
        else:
            return f'❌ خطا: {data.get("error", {}).get("message", str(data))}'
    except Exception as e:
        return f'❌ خطا در اتصال به AI: {str(e)}'

def clear_ai_history(user_id):
    user_ai_history.pop(user_id, None)

# ═══════════════════════════════════════════
#       🎨 منوهای شیشه‌ای پیشرفته
# ═══════════════════════════════════════════

def main_menu(user_id=None):
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton('🌐 ورود به سایت', url=SITE_URL),
        InlineKeyboardButton('🤖 هوش مصنوعی', callback_data='ai_chat'),
    )
    markup.add(
        InlineKeyboardButton('🛡️ ابزارها', callback_data='tools'),
        InlineKeyboardButton('📚 آموزش', callback_data='tutorials'),
    )
    markup.add(
        InlineKeyboardButton('🔒 کانفیگ V2Ray', callback_data='get_config'),
        InlineKeyboardButton('📁 فایل VPN', callback_data='get_vpn'),
    )
    markup.add(
        InlineKeyboardButton('👤 پیام ناشناس', callback_data='anon'),
        InlineKeyboardButton('📞 پشتیبانی', callback_data='support'),
    )
    markup.add(
        InlineKeyboardButton('📣 معرفی به دیگران', callback_data='share'),
        InlineKeyboardButton('ℹ️ درباره ما', callback_data='about'),
    )
    markup.add(
        InlineKeyboardButton('👤 پروفایل من', callback_data='my_profile'),
    )
    return markup

def admin_menu():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton('📊 آمار کامل', callback_data='admin_stats'),
        InlineKeyboardButton('📢 پیام همگانی', callback_data='admin_broadcast'),
    )
    markup.add(
        InlineKeyboardButton('👥 مدیریت کاربران', callback_data='admin_users'),
        InlineKeyboardButton('🏘️ مدیریت گروه‌ها', callback_data='admin_groups'),
    )
    markup.add(
        InlineKeyboardButton('💬 پاسخ خودکار', callback_data='admin_autoreplies'),
        InlineKeyboardButton('📋 لاگ رویدادها', callback_data='admin_logs'),
    )
    markup.add(
        InlineKeyboardButton('⚙️ تنظیمات ربات', callback_data='admin_settings'),
        InlineKeyboardButton('🌐 ورود به سایت', url=SITE_URL),
    )
    return markup

def group_settings_menu(group_id):
    group = get_group(group_id)
    if not group:
        return InlineKeyboardMarkup()

    _, title, _, anti_link, anti_spam, welcome, ai_reply, warn_limit = group

    def status(val):
        return '✅' if val else '❌'

    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton(f'🔗 ضد لینک: {status(anti_link)}',
                             callback_data=f'grp_toggle_anti_link_{group_id}'),
        InlineKeyboardButton(f'🚫 ضد اسپم: {status(anti_spam)}',
                             callback_data=f'grp_toggle_anti_spam_{group_id}'),
        InlineKeyboardButton(f'👋 خوش‌آمدگویی: {status(welcome)}',
                             callback_data=f'grp_toggle_welcome_{group_id}'),
        InlineKeyboardButton(f'🤖 AI در گروه: {status(ai_reply)}',
                             callback_data=f'grp_toggle_ai_reply_{group_id}'),
        InlineKeyboardButton(f'⚠️ حد اخطار: {warn_limit}',
                             callback_data=f'grp_warn_limit_{group_id}'),
        InlineKeyboardButton('🔙 برگشت', callback_data='admin_groups'),
    )
    return markup

def ai_menu():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton('🗑️ پاک کردن تاریخچه', callback_data='ai_clear'),
        InlineKeyboardButton('💡 راهنما', callback_data='ai_help'),
    )
    markup.add(
        InlineKeyboardButton('🔙 برگشت به منو', callback_data='back'),
    )
    return markup

def back_btn(callback='back'):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton('🔙 برگشت', callback_data=callback))
    return markup

# ═══════════════════════════════════════════
#       🔍 ابزارهای کمکی
# ═══════════════════════════════════════════

def contains_link(text):
    patterns = [
        r'http[s]?://\S+',
        r'www\.\S+',
        r't\.me/\S+',
        r'telegram\.me/\S+',
        r'@\w+',
    ]
    for p in patterns:
        if re.search(p, text, re.IGNORECASE):
            return True
    return False

def is_admin_in_group(chat_id, user_id):
    try:
        member = bot.get_chat_member(chat_id, user_id)
        return member.status in ['administrator', 'creator']
    except:
        return False

def is_bot_admin(chat_id):
    try:
        me = bot.get_me()
        member = bot.get_chat_member(chat_id, me.id)
        return member.status in ['administrator', 'creator']
    except:
        return False

def mute_user(chat_id, user_id, seconds=300):
    try:
        until = int(time.time()) + seconds
        bot.restrict_chat_member(
            chat_id, user_id,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=until
        )
        return True
    except:
        return False

def kick_user(chat_id, user_id):
    try:
        bot.kick_chat_member(chat_id, user_id)
        return True
    except:
        return False

def format_datetime(iso_str):
    try:
        dt = datetime.fromisoformat(iso_str)
        return dt.strftime('%Y/%m/%d %H:%M')
    except:
        return iso_str

# ═══════════════════════════════════════════
#            📨 هندلرهای اصلی
# ═══════════════════════════════════════════

user_states = {}

@bot.message_handler(commands=['start'])
def start(message):
    user = message.from_user
    add_user(user)
    log_event('start', user.id, detail=f'{user.first_name} started bot')

    name = user.first_name or 'کاربر'

    if user.id != ADMIN_ID:
        try:
            bot.send_message(ADMIN_ID,
                f'🔔 *کاربر جدید وارد شد*\n\n'
                f'👤 نام: {name}\n'
                f'🔗 یوزر: @{user.username or "ندارد"}\n'
                f'🆔 ID: `{user.id}`\n'
                f'🕐 زمان: {datetime.now().strftime("%H:%M:%S")}',
                parse_mode='Markdown')
        except:
            pass

    welcome = (
        f'سلام *{name}* عزیز! 👋\n\n'
        f'🔥 به ربات *SFOR* خوش اومدی\n'
        f'مرکز ابزارهای هک و امنیت دیجیتال\n\n'
        f'━━━━━━━━━━━━━━━\n'
        f'🤖 AI هوشمند • 🛡️ ابزارها • 📚 آموزش\n'
        f'━━━━━━━━━━━━━━━\n\n'
        f'از منو زیر انتخاب کن 👇'
    )

    if user.id == ADMIN_ID:
        bot.send_message(message.chat.id,
            '⚡ *پنل ادمین SFOR*\nخوش اومدی باس! 😎',
            parse_mode='Markdown', reply_markup=admin_menu())

    bot.send_message(message.chat.id, welcome,
                     parse_mode='Markdown', reply_markup=main_menu())


@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, '❌ دسترسی ندارید!')
        return
    bot.send_message(message.chat.id, '⚡ *پنل ادمین SFOR*',
                     parse_mode='Markdown', reply_markup=admin_menu())


@bot.message_handler(commands=['warn'])
def warn_cmd(message):
    if message.chat.type not in ['group', 'supergroup']:
        return
    if not is_admin_in_group(message.chat.id, message.from_user.id):
        bot.reply_to(message, '❌ فقط ادمین‌ها می‌تونن اخطار بدن!')
        return
    if not message.reply_to_message:
        bot.reply_to(message, '⚠️ روی پیام کاربر reply کن!')
        return

    target = message.reply_to_message.from_user
    reason = message.text.split(None, 1)[1] if len(message.text.split()) > 1 else 'بدون دلیل'

    group = get_group(message.chat.id)
    warn_limit = group[7] if group else 3

    count = add_warn(target.id, message.chat.id, reason)
    log_event('warn', target.id, message.chat.id, reason)

    if count >= warn_limit:
        kick_user(message.chat.id, target.id)
        clear_warns(target.id, message.chat.id)
        bot.reply_to(message,
            f'🚫 *{target.first_name}* به دلیل {count} اخطار از گروه اخراج شد!',
            parse_mode='Markdown')
    else:
        bot.reply_to(message,
            f'⚠️ *اخطار {count}/{warn_limit}*\n\n'
            f'👤 کاربر: {target.first_name}\n'
            f'📝 دلیل: {reason}',
            parse_mode='Markdown')


@bot.message_handler(commands=['kick'])
def kick_cmd(message):
    if message.chat.type not in ['group', 'supergroup']:
        return
    if not is_admin_in_group(message.chat.id, message.from_user.id):
        bot.reply_to(message, '❌ فقط ادمین‌ها می‌تونن کیک کنن!')
        return
    if not message.reply_to_message:
        bot.reply_to(message, '⚠️ روی پیام کاربر reply کن!')
        return

    target = message.reply_to_message.from_user
    if kick_user(message.chat.id, target.id):
        log_event('kick', target.id, message.chat.id)
        bot.reply_to(message, f'✅ *{target.first_name}* از گروه اخراج شد!', parse_mode='Markdown')
    else:
        bot.reply_to(message, '❌ خطا در اخراج کاربر!')


@bot.message_handler(commands=['mute'])
def mute_cmd(message):
    if message.chat.type not in ['group', 'supergroup']:
        return
    if not is_admin_in_group(message.chat.id, message.from_user.id):
        bot.reply_to(message, '❌ فقط ادمین‌ها می‌تونن میوت کنن!')
        return
    if not message.reply_to_message:
        bot.reply_to(message, '⚠️ روی پیام کاربر reply کن!')
        return

    parts = message.text.split()
    minutes = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 5

    target = message.reply_to_message.from_user
    if mute_user(message.chat.id, target.id, minutes * 60):
        log_event('mute', target.id, message.chat.id, f'{minutes} دقیقه')
        bot.reply_to(message,
            f'🔇 *{target.first_name}* برای {minutes} دقیقه میوت شد!',
            parse_mode='Markdown')
    else:
        bot.reply_to(message, '❌ خطا در میوت کردن!')


@bot.message_handler(commands=['ban'])
def ban_cmd(message):
    if message.chat.type not in ['group', 'supergroup']:
        return
    if not is_admin_in_group(message.chat.id, message.from_user.id):
        bot.reply_to(message, '❌ فقط ادمین‌ها می‌تونن بن کنن!')
        return
    if not message.reply_to_message:
        bot.reply_to(message, '⚠️ روی پیام کاربر reply کن!')
        return

    target = message.reply_to_message.from_user
    try:
        bot.ban_chat_member(message.chat.id, target.id)
        ban_user(target.id)
        log_event('ban', target.id, message.chat.id)
        bot.reply_to(message, f'🔴 *{target.first_name}* برای همیشه بن شد!', parse_mode='Markdown')
    except:
        bot.reply_to(message, '❌ خطا در بن کردن!')


@bot.message_handler(commands=['unban'])
def unban_cmd(message):
    if message.chat.type not in ['group', 'supergroup']:
        return
    if not is_admin_in_group(message.chat.id, message.from_user.id):
        return
    if not message.reply_to_message:
        bot.reply_to(message, '⚠️ روی پیام کاربر reply کن!')
        return

    target = message.reply_to_message.from_user
    try:
        bot.unban_chat_member(message.chat.id, target.id)
        unban_user(target.id)
        bot.reply_to(message, f'✅ بن *{target.first_name}* برداشته شد!', parse_mode='Markdown')
    except:
        bot.reply_to(message, '❌ خطا!')


@bot.message_handler(commands=['warns'])
def warns_cmd(message):
    if message.chat.type not in ['group', 'supergroup']:
        return
    if not message.reply_to_message:
        bot.reply_to(message, '⚠️ روی پیام کاربر reply کن!')
        return

    target = message.reply_to_message.from_user
    group = get_group(message.chat.id)
    warn_limit = group[7] if group else 3
    count = get_warns(target.id, message.chat.id)

    bot.reply_to(message,
        f'⚠️ *اخطارهای {target.first_name}*\n\n'
        f'تعداد: {count}/{warn_limit}',
        parse_mode='Markdown')


@bot.message_handler(commands=['clearwarns'])
def clearwarns_cmd(message):
    if message.chat.type not in ['group', 'supergroup']:
        return
    if not is_admin_in_group(message.chat.id, message.from_user.id):
        return
    if not message.reply_to_message:
        return

    target = message.reply_to_message.from_user
    clear_warns(target.id, message.chat.id)
    bot.reply_to(message, f'✅ اخطارهای *{target.first_name}* پاک شد!', parse_mode='Markdown')


@bot.message_handler(commands=['ai'])
def ai_group_cmd(message):
    if not message.text or len(message.text.split()) < 2:
        bot.reply_to(message, '💡 مثال: `/ai سوالت رو بنویس`', parse_mode='Markdown')
        return

    question = message.text.split(None, 1)[1]
    msg = bot.reply_to(message, '🤖 در حال فکر کردن...')
    reply = ask_ai(message.from_user.id, question, use_history=False)
    try:
        bot.edit_message_text(f'🤖 *پاسخ AI:*\n\n{reply}',
                              message.chat.id, msg.message_id,
                              parse_mode='Markdown')
    except:
        bot.reply_to(message, f'🤖 {reply}')


@bot.message_handler(commands=['id'])
def id_cmd(message):
    text = f'🆔 *اطلاعات شناسه*\n\n'
    text += f'👤 ID شما: `{message.from_user.id}`\n'
    if message.chat.type != 'private':
        text += f'💬 ID گروه: `{message.chat.id}`\n'
        text += f'📛 نام گروه: {message.chat.title}'
    bot.reply_to(message, text, parse_mode='Markdown')


@bot.message_handler(commands=['help'])
def help_cmd(message):
    text = (
        '📖 *دستورات ربات SFOR*\n\n'
        '🔹 *دستورات عمومی:*\n'
        '/start - شروع ربات\n'
        '/ai سوال - چت با هوش مصنوعی\n'
        '/id - نمایش ID شما\n'
        '/config - دریافت کانفیگ V2Ray رایگان\n'
        '/vpn - دریافت فایل VPN\n'
        '/help - این راهنما\n\n'
        '🔸 *دستورات گروه (ادمین):*\n'
        '/warn - اخطار به کاربر\n'
        '/kick - اخراج از گروه\n'
        '/mute [دقیقه] - میوت کردن\n'
        '/ban - بن کردن\n'
        '/unban - رفع بن\n'
        '/warns - نمایش اخطارها\n'
        '/clearwarns - پاک کردن اخطارها\n'
    )
    bot.reply_to(message, text, parse_mode='Markdown')


@bot.message_handler(commands=['config'])
def config_cmd(message):
    uid = message.from_user.id
    add_user(message.from_user)

    if has_received_config(uid) and uid != ADMIN_ID:
        bot.reply_to(message,
            '⚠️ *قبلاً کانفیگ دریافت کردی!*\n\n'
            'هر کاربر فقط یک بار می‌تونه کانفیگ دریافت کنه.\n'
            'برای کانفیگ جدید با پشتیبانی تماس بگیر 👇\n'
            't.me/Sfor34',
            parse_mode='Markdown')
        return

    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton('📲 آموزش اتصال', url='https://sfor.onrender.com'))

    bot.reply_to(message,
        '🔒 *کانفیگ‌های رایگان SFOR*\n\n'
        '⚡ ۱۳ کانفیگ V2Ray آماده:\n\n'
        f'`{V2RAY_CONFIGS}`\n\n'
        '📌 *راهنما:*\n'
        '• اپ V2RayNG (اندروید) یا V2Box (iOS)\n'
        '• کپی کن، Import from clipboard\n'
        '• بهترین کانفیگ رو با Ping تست کن\n\n'
        '✅ کانفیگ‌ها رایگان و بدون محدودیت',
        parse_mode='Markdown',
        reply_markup=markup)

    if uid != ADMIN_ID:
        mark_config_given(uid)

    log_event('config_given', uid, detail='V2Ray configs sent')


@bot.message_handler(commands=['vpn'])
def vpn_cmd(message):
    uid = message.from_user.id
    add_user(message.from_user)

    if has_received_vpn(uid) and uid != ADMIN_ID:
        bot.reply_to(message,
            '⚠️ *قبلاً فایل VPN دریافت کردی!*\n\n'
            'هر کاربر فقط یک بار می‌تونه فایل VPN دریافت کنه.\n'
            'برای فایل جدید با پشتیبانی تماس بگیر 👇\n'
            't.me/Sfor34',
            parse_mode='Markdown')
        return

    sent_count = 0
    for fname in VPN_FILES:
        if os.path.exists(fname):
            try:
                with open(fname, 'rb') as f:
                    bot.send_document(uid, f, caption=f'🔒 {fname}')
                sent_count += 1
            except Exception as e:
                pass

    if sent_count > 0:
        if uid != ADMIN_ID:
            mark_vpn_given(uid)
        log_event('vpn_given', uid, detail=f'{sent_count} files sent')
        bot.reply_to(message,
            f'✅ *{sent_count} فایل VPN ارسال شد!*\n\n'
            '📱 *نرم‌افزار مورد نیاز:* NPV Tunnel\n'
            '• اندروید: از Google Play دانلود کن\n'
            '• فایل رو Import کن و وصل شو 🚀',
            parse_mode='Markdown')
    else:
        bot.reply_to(message,
            '⏳ *فایل‌های VPN به زودی اضافه میشن!*\n\n'
            'در حال حاضر از /config برای کانفیگ V2Ray استفاده کن.',
            parse_mode='Markdown')


# ═══════════════════════════════════════════
#         👥 رویدادهای گروه
# ═══════════════════════════════════════════

@bot.message_handler(content_types=['new_chat_members'])
def welcome_new_member(message):
    add_group(message.chat)
    group = get_group(message.chat.id)

    for member in message.new_chat_members:
        me = bot.get_me()
        if member.id == me.id:
            # ربات به گروه اضافه شد
            log_event('bot_added', group_id=message.chat.id, detail=message.chat.title)
            try:
                bot.send_message(ADMIN_ID,
                    f'➕ *ربات به گروه اضافه شد!*\n\n'
                    f'📛 نام: {message.chat.title}\n'
                    f'🆔 ID: `{message.chat.id}`\n'
                    f'🕐 زمان: {datetime.now().strftime("%H:%M:%S")}',
                    parse_mode='Markdown')
            except:
                pass
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton('⚙️ تنظیمات گروه', callback_data=f'grp_settings_{message.chat.id}'))
            bot.send_message(message.chat.id,
                '👋 سلام! ربات SFOR آماده‌ست!\n\n'
                '🛡️ محافظت گروه فعال شد\n'
                '🤖 برای چت با AI از /ai استفاده کن',
                reply_markup=markup)
            return

        if group and group[5]:  # welcome فعاله
            add_user(member)
            log_event('new_member', member.id, message.chat.id)
            bot.send_message(message.chat.id,
                f'👋 *خوش اومدی {member.first_name}!*\n\n'
                f'به گروه {message.chat.title} خوش اومدی 🎉\n'
                f'برای راهنمایی /help رو بزن',
                parse_mode='Markdown')


@bot.message_handler(content_types=['left_chat_member'])
def member_left(message):
    member = message.left_chat_member
    me = bot.get_me()
    if member.id == me.id:
        log_event('bot_removed', group_id=message.chat.id, detail=message.chat.title)
        try:
            bot.send_message(ADMIN_ID,
                f'➖ *ربات از گروه حذف شد!*\n\n'
                f'📛 نام: {message.chat.title}\n'
                f'🆔 ID: `{message.chat.id}`',
                parse_mode='Markdown')
        except:
            pass


# ═══════════════════════════════════════════
#         📨 پیام‌های گروه
# ═══════════════════════════════════════════

@bot.message_handler(
    func=lambda m: m.chat.type in ['group', 'supergroup'],
    content_types=['text']
)
def handle_group_message(message):
    if not message.text:
        return

    add_group(message.chat)
    add_user(message.from_user)
    group = get_group(message.chat.id)
    if not group:
        return

    _, title, _, anti_link, anti_spam, welcome, ai_reply, warn_limit = group
    uid = message.from_user.id
    is_admin = is_admin_in_group(message.chat.id, uid)

    # ضد لینک
    if anti_link and not is_admin:
        if contains_link(message.text):
            try:
                bot.delete_message(message.chat.id, message.message_id)
            except:
                pass
            count = add_warn(uid, message.chat.id, 'ارسال لینک')
            log_event('anti_link', uid, message.chat.id)

            if count >= warn_limit:
                kick_user(message.chat.id, uid)
                clear_warns(uid, message.chat.id)
                bot.send_message(message.chat.id,
                    f'🚫 *{message.from_user.first_name}* به دلیل ارسال لینک و {count} اخطار اخراج شد!',
                    parse_mode='Markdown')
            else:
                bot.send_message(message.chat.id,
                    f'⚠️ *{message.from_user.first_name}* ارسال لینک ممنوعه! '
                    f'اخطار {count}/{warn_limit}',
                    parse_mode='Markdown')
            return

    # ضد اسپم
    if anti_spam and not is_admin:
        spam_count = check_spam(uid, message.chat.id, message.text)
        if spam_count >= 5:
            try:
                bot.delete_message(message.chat.id, message.message_id)
            except:
                pass
            mute_user(message.chat.id, uid, 300)
            log_event('anti_spam', uid, message.chat.id)
            bot.send_message(message.chat.id,
                f'🔇 *{message.from_user.first_name}* به خاطر اسپم 5 دقیقه میوت شد!',
                parse_mode='Markdown')
            return

    # پاسخ خودکار
    replies = get_auto_replies()
    for keyword, response, match_type in replies:
        if match_type == 'exact' and message.text.lower() == keyword.lower():
            bot.reply_to(message, response)
            return
        elif match_type == 'contains' and keyword.lower() in message.text.lower():
            bot.reply_to(message, response)
            return

    # AI در گروه
    if ai_reply:
        me = bot.get_me()
        mentioned = f'@{me.username}' in message.text if me.username else False
        replied_to_bot = (message.reply_to_message and
                          message.reply_to_message.from_user.id == me.id)

        if mentioned or replied_to_bot:
            question = message.text.replace(f'@{me.username}', '').strip()
            if question:
                msg = bot.reply_to(message, '🤖 در حال فکر کردن...')
                reply = ask_ai(uid, question, use_history=False)
                try:
                    bot.edit_message_text(reply, message.chat.id, msg.message_id)
                except:
                    pass


# ═══════════════════════════════════════════
#         💬 پیام‌های خصوصی
# ═══════════════════════════════════════════

@bot.message_handler(func=lambda m: m.chat.type == 'private')
def handle_private_message(message):
    uid = message.from_user.id
    add_user(message.from_user)
    state = user_states.get(uid)

    # حالت چت با AI
    if state == 'ai_chat':
        msg = bot.send_message(uid, '🤖 در حال فکر کردن...')
        reply = ask_ai(uid, message.text)
        try:
            bot.edit_message_text(
                f'🤖 *پاسخ AI:*\n\n{reply}',
                uid, msg.message_id,
                parse_mode='Markdown',
                reply_markup=ai_menu()
            )
        except:
            bot.send_message(uid, f'🤖 {reply}', reply_markup=ai_menu())
        return

    # پیام ناشناس
    if state == 'anon':
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton('↩️ پاسخ ناشناس', callback_data=f'reply_anon_{uid}'))
        bot.send_message(ADMIN_ID,
            f'👤 *پیام ناشناس:*\n\n{message.text}',
            parse_mode='Markdown', reply_markup=markup)
        bot.send_message(uid, '✅ پیامت ناشناس ارسال شد!', reply_markup=main_menu())
        user_states.pop(uid, None)
        return

    # پیام همگانی ادمین
    if state == 'broadcast' and uid == ADMIN_ID:
        users = get_all_users()
        success = 0
        fail = 0
        progress_msg = bot.send_message(uid, f'📢 در حال ارسال به {len(users)} کاربر...')

        for user_id in users:
            try:
                bot.send_message(user_id, message.text, parse_mode='Markdown')
                success += 1
                time.sleep(0.05)
            except:
                fail += 1

        bot.edit_message_text(
            f'✅ *پیام همگانی ارسال شد!*\n\n'
            f'✅ موفق: {success}\n❌ ناموفق: {fail}',
            uid, progress_msg.message_id,
            parse_mode='Markdown',
            reply_markup=back_btn('admin_back')
        )
        user_states.pop(uid, None)
        return

    # پاسخ به ناشناس
    if state and state.startswith('reply_anon_') and uid == ADMIN_ID:
        target_id = int(state.split('_')[-1])
        try:
            bot.send_message(target_id,
                f'📩 *پاسخ ادمین:*\n\n{message.text}',
                parse_mode='Markdown')
            bot.send_message(uid, '✅ پاسخ ارسال شد!', reply_markup=admin_menu())
        except:
            bot.send_message(uid, '❌ کاربر ربات رو بلاک کرده!', reply_markup=admin_menu())
        user_states.pop(uid, None)
        return

    # افزودن پاسخ خودکار
    if state == 'add_reply_keyword' and uid == ADMIN_ID:
        user_states[uid] = {'step': 'reply_response', 'keyword': message.text}
        bot.send_message(uid, f'✅ کلمه کلیدی: `{message.text}`\n\nحالا پاسخ رو بنویس:',
                         parse_mode='Markdown')
        return

    if isinstance(state, dict) and state.get('step') == 'reply_response' and uid == ADMIN_ID:
        keyword = state['keyword']
        add_auto_reply(keyword, message.text)
        user_states.pop(uid, None)
        bot.send_message(uid, f'✅ پاسخ خودکار اضافه شد!\n\nکلمه: `{keyword}`',
                         parse_mode='Markdown', reply_markup=back_btn('admin_autoreplies'))
        return

    # حذف پاسخ خودکار
    if state == 'delete_reply_keyword' and uid == ADMIN_ID:
        delete_auto_reply(message.text)
        user_states.pop(uid, None)
        bot.send_message(uid, f'✅ پاسخ خودکار برای `{message.text}` حذف شد!',
                         parse_mode='Markdown', reply_markup=back_btn('admin_autoreplies'))
        return

    # پیش‌فرض
    bot.send_message(uid, 'از منو زیر انتخاب کن 👇', reply_markup=main_menu())


# ═══════════════════════════════════════════
#         🔘 کالبک‌ها
# ═══════════════════════════════════════════

@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    uid = call.from_user.id
    cid = call.message.chat.id
    mid = call.message.message_id
    data = call.data

    # ─── منوی اصلی ───
    if data == 'back':
        user_states.pop(uid, None)
        bot.edit_message_text('منوی اصلی 👇', cid, mid, reply_markup=main_menu())

    elif data == 'ai_chat':
        user_states[uid] = 'ai_chat'
        bot.edit_message_text(
            '🤖 *هوش مصنوعی SFOR*\n\n'
            'پیامت رو بنویس، من جواب میدم!\n\n'
            '💡 *قابلیت‌ها:*\n'
            '• تاریخچه مکالمه رو نگه میداره\n'
            '• سوالات فنی و عمومی\n'
            '• کمک با کدنویسی\n\n'
            '_برای خروج از چت، دکمه برگشت رو بزن_',
            cid, mid,
            parse_mode='Markdown',
            reply_markup=ai_menu()
        )

    elif data == 'ai_clear':
        clear_ai_history(uid)
        bot.answer_callback_query(call.id, '✅ تاریخچه پاک شد!')

    elif data == 'ai_help':
        bot.answer_callback_query(call.id,
            '💡 پیامت رو بنویس! از /ai توی گروه هم میشه استفاده کرد.', show_alert=True)

    elif data == 'tools':
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(
            InlineKeyboardButton('🌐 مشاهده همه ابزارها در سایت', url=SITE_URL),
            InlineKeyboardButton('🔙 برگشت', callback_data='back')
        )
        bot.edit_message_text(
            '🛡️ *ابزارهای SFOR*\n\nبرای دانلود و مشاهده ابزارها به سایت برو:',
            cid, mid, parse_mode='Markdown', reply_markup=markup)

    elif data == 'tutorials':
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(
            InlineKeyboardButton('📚 مشاهده آموزش‌ها', url=SITE_URL),
            InlineKeyboardButton('🔙 برگشت', callback_data='back')
        )
        bot.edit_message_text(
            '📚 *آموزش‌های SFOR*\n\nمقاله • ویدیو • ترفند • باگ • نکته',
            cid, mid, parse_mode='Markdown', reply_markup=markup)

    elif data == 'anon':
        user_states[uid] = 'anon'
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton('❌ انصراف', callback_data='back'))
        bot.edit_message_text(
            '👤 *پیام ناشناس*\n\nپیامت رو بنویس، بدون اینکه هویتت لو بره به ادمین میرسه:',
            cid, mid, parse_mode='Markdown', reply_markup=markup)

    elif data == 'support':
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton('👤 تلگرام', url='https://t.me/Sfor34'),
            InlineKeyboardButton('📸 اینستا', url='https://instagram.com/mmadsfor'),
        )
        markup.add(InlineKeyboardButton('🔙 برگشت', callback_data='back'))
        bot.edit_message_text(
            '📞 *پشتیبانی SFOR*\n\n'
            '💬 تلگرام: @Sfor34\n'
            '📸 اینستاگرام: @mmadsfor\n'
            '🌐 سایت: sfor.onrender.com',
            cid, mid, parse_mode='Markdown', reply_markup=markup)

    elif data == 'share':
        bot_info = bot.get_me()
        link = f'https://t.me/{bot_info.username}?start=ref_{uid}'
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton('📤 اشتراک‌گذاری',
            url=f'https://t.me/share/url?url={link}&text=🔥 ربات SFOR - ابزارهای هک و امنیت'))
        markup.add(InlineKeyboardButton('🔙 برگشت', callback_data='back'))
        bot.edit_message_text(
            f'📣 *معرفی به دیگران*\n\nلینک اختصاصی تو:\n`{link}`',
            cid, mid, parse_mode='Markdown', reply_markup=markup)

    elif data == 'about':
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton('🌐 سایت', url=SITE_URL),
            InlineKeyboardButton('📸 اینستا', url='https://instagram.com/mmadsfor'),
        )
        markup.add(InlineKeyboardButton('🔙 برگشت', callback_data='back'))
        bot.edit_message_text(
            f'ℹ️ *درباره SFOR*\n\n'
            f'🔥 مرکز ابزارهای هک، امنیت و مود\n'
            f'⚡ بهترین و به‌روزترین ابزارهای دیجیتال\n\n'
            f'🤖 ربات نسخه: {BOT_VERSION}\n'
            f'👨‍💻 ساخته شده توسط تیم SFOR',
            cid, mid, parse_mode='Markdown', reply_markup=markup)

    elif data == 'my_profile':
        conn = db()
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE id=?', (uid,))
        user_data = c.fetchone()
        conn.close()
        if user_data:
            _, username, first_name, joined_at, is_banned, msg_count = user_data
            status = '🔴 بن شده' if is_banned else '🟢 فعال'
            bot.edit_message_text(
                f'👤 *پروفایل من*\n\n'
                f'📛 نام: {first_name}\n'
                f'🔗 یوزر: @{username or "ندارد"}\n'
                f'🆔 ID: `{uid}`\n'
                f'📅 عضویت: {format_datetime(joined_at)}\n'
                f'💬 پیام‌ها: {msg_count}\n'
                f'📊 وضعیت: {status}',
                cid, mid, parse_mode='Markdown', reply_markup=back_btn())
        else:
            bot.answer_callback_query(call.id, 'اطلاعات یافت نشد!')

    elif data == 'get_config':
        if has_received_config(uid) and uid != ADMIN_ID:
            bot.answer_callback_query(call.id,
                '⚠️ قبلاً کانفیگ دریافت کردی! برای کانفیگ جدید با پشتیبانی تماس بگیر.',
                show_alert=True)
            return
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton('📲 آموزش اتصال', url=SITE_URL))
        markup.add(InlineKeyboardButton('🔙 برگشت', callback_data='back'))
        bot.edit_message_text(
            '🔒 *کانفیگ‌های رایگان SFOR*\n\n'
            '⚡ ۱۳ کانفیگ V2Ray آماده:\n\n'
            f'`{V2RAY_CONFIGS}`\n\n'
            '📌 *راهنما:*\n'
            '• اپ V2RayNG (اندروید) یا V2Box (iOS)\n'
            '• کپی کن، Import from clipboard\n'
            '• بهترین کانفیگ رو با Ping تست کن',
            cid, mid, parse_mode='Markdown', reply_markup=markup)
        if uid != ADMIN_ID:
            mark_config_given(uid)
        log_event('config_given', uid, detail='V2Ray configs sent via menu')

    elif data == 'get_vpn':
        sent_count = 0
        if has_received_vpn(uid) and uid != ADMIN_ID:
            bot.answer_callback_query(call.id,
                '⚠️ قبلاً فایل VPN دریافت کردی! برای فایل جدید با پشتیبانی تماس بگیر.',
                show_alert=True)
            return
        for fname in VPN_FILES:
            if os.path.exists(fname):
                try:
                    with open(fname, 'rb') as f:
                        bot.send_document(uid, f, caption=f'🔒 {fname}')
                    sent_count += 1
                except:
                    pass
        if sent_count > 0:
            if uid != ADMIN_ID:
                mark_vpn_given(uid)
            log_event('vpn_given', uid, detail=f'{sent_count} files sent via menu')
            bot.answer_callback_query(call.id, f'✅ {sent_count} فایل VPN ارسال شد!')
        else:
            bot.answer_callback_query(call.id,
                '⏳ فایل‌های VPN به زودی اضافه میشن! از /config استفاده کن.',
                show_alert=True)

    # ─── پنل ادمین ───
    elif data == 'admin_back':
        bot.edit_message_text('⚡ *پنل ادمین SFOR*', cid, mid,
                              parse_mode='Markdown', reply_markup=admin_menu())

    elif data == 'admin_stats':
        if uid != ADMIN_ID:
            bot.answer_callback_query(call.id, '❌ دسترسی ندارید!')
            return
        users, groups, banned, msgs, warns = get_stats()
        bot.edit_message_text(
            f'📊 *آمار کامل ربات SFOR*\n\n'
            f'👤 کاربران: {users}\n'
            f'🏘️ گروه‌ها: {groups}\n'
            f'🔴 بن شده‌ها: {banned}\n'
            f'💬 کل پیام‌ها: {msgs}\n'
            f'⚠️ کل اخطارها: {warns}\n\n'
            f'🤖 نسخه ربات: {BOT_VERSION}\n'
            f'🕐 آخرین آپدیت: {datetime.now().strftime("%H:%M:%S")}',
            cid, mid, parse_mode='Markdown', reply_markup=back_btn('admin_back'))

    elif data == 'admin_broadcast':
        if uid != ADMIN_ID:
            bot.answer_callback_query(call.id, '❌')
            return
        user_states[uid] = 'broadcast'
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton('❌ انصراف', callback_data='admin_back'))
        bot.edit_message_text(
            '📢 *پیام همگانی*\n\nپیامت رو بنویس (از Markdown استفاده کن):',
            cid, mid, parse_mode='Markdown', reply_markup=markup)

    elif data == 'admin_users':
        if uid != ADMIN_ID:
            bot.answer_callback_query(call.id, '❌')
            return
        conn = db()
        c = conn.cursor()
        c.execute('SELECT id, first_name, username, is_banned FROM users ORDER BY id DESC LIMIT 10')
        rows = c.fetchall()
        conn.close()
        text = '👥 *آخرین کاربران:*\n\n'
        for r in rows:
            status = '🔴' if r[3] else '🟢'
            text += f'{status} {r[1]} | @{r[2] or "ندارد"} | `{r[0]}`\n'
        bot.edit_message_text(text, cid, mid, parse_mode='Markdown',
                              reply_markup=back_btn('admin_back'))

    elif data == 'admin_groups':
        if uid != ADMIN_ID:
            bot.answer_callback_query(call.id, '❌')
            return
        conn = db()
        c = conn.cursor()
        c.execute('SELECT id, title FROM groups ORDER BY joined_at DESC')
        rows = c.fetchall()
        conn.close()
        if not rows:
            bot.edit_message_text('🏘️ هنوز گروهی ثبت نشده!', cid, mid,
                                  reply_markup=back_btn('admin_back'))
            return
        markup = InlineKeyboardMarkup(row_width=1)
        for r in rows:
            markup.add(InlineKeyboardButton(f'⚙️ {r[1]}',
                                            callback_data=f'grp_settings_{r[0]}'))
        markup.add(InlineKeyboardButton('🔙 برگشت', callback_data='admin_back'))
        bot.edit_message_text('🏘️ *گروه‌های ثبت شده:*', cid, mid,
                              parse_mode='Markdown', reply_markup=markup)

    elif data == 'admin_autoreplies':
        if uid != ADMIN_ID:
            bot.answer_callback_query(call.id, '❌')
            return
        replies = get_auto_replies()
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(
            InlineKeyboardButton('➕ افزودن پاسخ جدید', callback_data='add_autoreply'),
            InlineKeyboardButton('➖ حذف پاسخ', callback_data='delete_autoreply'),
        )
        markup.add(InlineKeyboardButton('🔙 برگشت', callback_data='admin_back'))
        text = '💬 *پاسخ‌های خودکار:*\n\n'
        if replies:
            for i, (kw, resp, mt) in enumerate(replies, 1):
                text += f'{i}. 🔑 `{kw}` ← {resp[:30]}...\n'
        else:
            text += '_هنوز پاسخی ثبت نشده_'
        bot.edit_message_text(text, cid, mid, parse_mode='Markdown', reply_markup=markup)

    elif data == 'add_autoreply':
        user_states[uid] = 'add_reply_keyword'
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton('❌ انصراف', callback_data='admin_autoreplies'))
        bot.edit_message_text('➕ کلمه کلیدی رو بنویس:', cid, mid, reply_markup=markup)

    elif data == 'delete_autoreply':
        user_states[uid] = 'delete_reply_keyword'
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton('❌ انصراف', callback_data='admin_autoreplies'))
        bot.edit_message_text('➖ کلمه کلیدی که می‌خوای حذف بشه رو بنویس:',
                              cid, mid, reply_markup=markup)

    elif data == 'admin_logs':
        if uid != ADMIN_ID:
            bot.answer_callback_query(call.id, '❌')
            return
        conn = db()
        c = conn.cursor()
        c.execute('SELECT event_type, user_id, detail, created_at FROM logs ORDER BY id DESC LIMIT 10')
        rows = c.fetchall()
        conn.close()
        text = '📋 *آخرین رویدادها:*\n\n'
        icons = {
            'start': '▶️', 'warn': '⚠️', 'kick': '👢', 'ban': '🔴',
            'mute': '🔇', 'anti_link': '🔗', 'anti_spam': '🚫',
            'new_member': '👋', 'bot_added': '➕', 'bot_removed': '➖'
        }
        for r in rows:
            icon = icons.get(r[0], '📌')
            text += f'{icon} {r[0]} | `{r[1]}` | {r[3][11:16]}\n'
        bot.edit_message_text(text, cid, mid, parse_mode='Markdown',
                              reply_markup=back_btn('admin_back'))

    elif data == 'admin_settings':
        if uid != ADMIN_ID:
            bot.answer_callback_query(call.id, '❌')
            return
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(
            InlineKeyboardButton('🔄 ری‌استارت ربات', callback_data='admin_restart'),
            InlineKeyboardButton('🗑️ پاک کردن لاگ‌ها', callback_data='admin_clearlogs'),
            InlineKeyboardButton('🔙 برگشت', callback_data='admin_back'),
        )
        bot.edit_message_text('⚙️ *تنظیمات ربات:*', cid, mid,
                              parse_mode='Markdown', reply_markup=markup)

    elif data == 'admin_restart':
        if uid != ADMIN_ID:
            return
        bot.answer_callback_query(call.id, '🔄 ری‌استارت در حال انجام...', show_alert=True)
        bot.send_message(uid, '♻️ ربات در حال ری‌استارت...')
        os.execv(__file__, ['python'] + [__file__])

    elif data == 'admin_clearlogs':
        if uid != ADMIN_ID:
            return
        conn = db()
        c = conn.cursor()
        c.execute('DELETE FROM logs')
        conn.commit()
        conn.close()
        bot.answer_callback_query(call.id, '✅ لاگ‌ها پاک شدند!')

    # ─── تنظیمات گروه ───
    elif data.startswith('grp_settings_'):
        if uid != ADMIN_ID:
            bot.answer_callback_query(call.id, '❌')
            return
        group_id = int(data.split('_')[-1])
        group = get_group(group_id)
        if not group:
            add_group(type('obj', (object,), {'id': group_id, 'title': 'گروه'})())
        bot.edit_message_text(
            f'⚙️ *تنظیمات گروه*\n`{group_id}`',
            cid, mid, parse_mode='Markdown',
            reply_markup=group_settings_menu(group_id))

    elif data.startswith('grp_toggle_'):
        if uid != ADMIN_ID:
            bot.answer_callback_query(call.id, '❌')
            return
        parts = data.split('_')
        group_id = int(parts[-1])
        setting = '_'.join(parts[2:-1])
        group = get_group(group_id)
        if group:
            settings_map = {
                'anti_link': 3, 'anti_spam': 4,
                'welcome': 5, 'ai_reply': 6
            }
            idx = settings_map.get(setting)
            if idx:
                new_val = 0 if group[idx] else 1
                update_group_setting(group_id, setting, new_val)
                status = 'فعال ✅' if new_val else 'غیرفعال ❌'
                bot.answer_callback_query(call.id, f'{setting}: {status}')
                bot.edit_message_reply_markup(cid, mid,
                    reply_markup=group_settings_menu(group_id))

    # ─── پاسخ ناشناس ───
    elif data.startswith('reply_anon_'):
        if uid != ADMIN_ID:
            bot.answer_callback_query(call.id, '❌')
            return
        target_id = data.split('_')[-1]
        user_states[uid] = f'reply_anon_{target_id}'
        bot.send_message(uid, '↩️ پاسخت رو بنویس:')

    bot.answer_callback_query(call.id)


# ═══════════════════════════════════════════
#              🚀 اجرا
# ═══════════════════════════════════════════

if __name__ == '__main__':
    print(f'''
    ╔══════════════════════════════╗
    ║   🔥 SFOR BOT v{BOT_VERSION}       ║
    ║   ✅ AI: Grok (Llama-3.3)    ║
    ║   ✅ Anti-Link & Spam        ║
    ║   ✅ Group Management        ║
    ║   ✅ /config & /vpn          ║
    ║   ✅ Advanced Admin Panel    ║
    ╚══════════════════════════════╝
    ''')
    while True:
        try:
            bot.delete_webhook(drop_pending_updates=True)
            time.sleep(2)
            bot.infinity_polling(timeout=30, long_polling_timeout=30)
        except Exception as e:
            print(f'[ERROR] Bot crashed: {e}')
            time.sleep(5)
            continue
