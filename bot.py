import telebot
from telebot.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ChatPermissions, ReplyKeyboardMarkup, KeyboardButton,
    ReplyKeyboardRemove
)
import os, sys, requests, json, time, re, sqlite3, random, hashlib
from datetime import datetime, timedelta
from threading import Thread
from flask import Flask

# ═══════════════════════════════════════════
#         🌐 Flask برای Render
# ═══════════════════════════════════════════
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return '🔥 SFOR Bot v3.0 is running!'

@flask_app.route('/health')
def health():
    return 'OK', 200

def run_flask():
    port = int(os.environ.get('PORT', 8080))
    flask_app.run(host='0.0.0.0', port=port, debug=False)

flask_thread = Thread(target=run_flask, daemon=True)
flask_thread.start()

# ═══════════════════════════════════════════
#              ⚙️ تنظیمات اصلی
# ═══════════════════════════════════════════
TOKEN      = os.environ.get('TOKEN', '8576320592:AAEq0o4Zz97ZzBS3dkqGCEMAG8QfdOjhoK4')
ADMIN_ID   = int(os.environ.get('ADMIN_ID', '7533340777'))
ADMIN_PASS = 'MMad09039484636'
GEMINI_KEY = os.environ.get('GEMINI_KEY', '')
GEMINI_URL = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent'
SITE_URL   = 'https://sfor.onrender.com'
BOT_VERSION = '3.0.0'
DB_FILE    = 'sfor_bot.db'

bot = telebot.TeleBot(TOKEN, parse_mode=None)

# ═══════════════════════════════════════════
#              🗄️ دیتابیس
# ═══════════════════════════════════════════
def db():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = db()
    c = conn.cursor()
    c.executescript('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        username TEXT, first_name TEXT,
        joined_at TEXT, is_banned INTEGER DEFAULT 0,
        message_count INTEGER DEFAULT 0, is_vip INTEGER DEFAULT 0,
        last_seen TEXT
    );
    CREATE TABLE IF NOT EXISTS groups (
        id INTEGER PRIMARY KEY,
        title TEXT, joined_at TEXT,
        anti_link INTEGER DEFAULT 1,
        anti_spam INTEGER DEFAULT 1,
        anti_profanity INTEGER DEFAULT 1,
        welcome INTEGER DEFAULT 1,
        goodbye INTEGER DEFAULT 0,
        ai_reply INTEGER DEFAULT 0,
        warn_limit INTEGER DEFAULT 3,
        rules TEXT DEFAULT "",
        welcome_msg TEXT DEFAULT "",
        goodbye_msg TEXT DEFAULT "",
        filter_words TEXT DEFAULT ""
    );
    CREATE TABLE IF NOT EXISTS warns (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, group_id INTEGER,
        reason TEXT, warned_at TEXT
    );
    CREATE TABLE IF NOT EXISTS auto_replies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        keyword TEXT UNIQUE, response TEXT,
        match_type TEXT DEFAULT "contains"
    );
    CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_type TEXT, user_id INTEGER,
        group_id INTEGER, detail TEXT,
        created_at TEXT
    );
    CREATE TABLE IF NOT EXISTS spam_track (
        user_id INTEGER, group_id INTEGER,
        count INTEGER DEFAULT 0,
        last_time TEXT,
        PRIMARY KEY (user_id, group_id)
    );
    CREATE TABLE IF NOT EXISTS configs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, link TEXT,
        is_used INTEGER DEFAULT 0,
        used_by INTEGER, created_at TEXT
    );
    CREATE TABLE IF NOT EXISTS vpn_files (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, file_id TEXT,
        is_used INTEGER DEFAULT 0,
        used_by INTEGER, created_at TEXT
    );
    CREATE TABLE IF NOT EXISTS ai_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, role TEXT,
        content TEXT, created_at TEXT
    );
    CREATE TABLE IF NOT EXISTS notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, group_id INTEGER,
        name TEXT, content TEXT, created_at TEXT
    );
    CREATE TABLE IF NOT EXISTS user_configs (
        user_id INTEGER PRIMARY KEY, given_at TEXT
    );
    CREATE TABLE IF NOT EXISTS user_vpns (
        user_id INTEGER PRIMARY KEY, given_at TEXT
    );
    CREATE TABLE IF NOT EXISTS pending_admin (
        user_id INTEGER PRIMARY KEY, step TEXT, data TEXT
    );
    ''')
    conn.commit()
    conn.close()

init_db()

# ═══════════════════════════════════════════
#         🔒 کانفیگ‌های V2Ray پیش‌فرض
# ═══════════════════════════════════════════
DEFAULT_CONFIGS = [
    ('SFOR-1',  'vless://d0cfc134-447c-4c84-965a-ff5f827c9016@116.203.60.171:8080?security=none&type=tcp#SFOR-1'),
    ('SFOR-2',  'trojan://humanity@188.114.97.6:443?path=%2Fassignment&security=tls&host=www.calmloud.com&type=ws&sni=www.calmloud.com#SFOR-2'),
    ('SFOR-3',  'trojan://humanity@212.183.88.136:443?path=%2Fassignment&security=tls&host=www.calmlunch.com&type=ws&sni=www.calmlunch.com#SFOR-3'),
    ('SFOR-4',  'vless://e65c9135-5c62-4e63-9bec-bca0cdf94f52@167.172.108.83:443?security=reality&encryption=none&pbk=YIwwnfgqZKzbdxD0Mq-PiOmIDPYCvkaptHyN_HzDgFA&headerType=none&fp=firefox&type=tcp&flow=xtls-rprx-vision&sni=icloud.com&sid=844282e475538c#SFOR-4'),
    ('SFOR-5',  'trojan://Masir_Sefid@188.213.130.212:443?security=reality&pbk=w0XepGv1Hk0gBh1Apiw-nvn8SfzjWcDuxdxN1mpaF3g&headerType=none&fp=chrome&type=tcp&sni=store.steampowered.com&sid=6ced01fc4aa417#SFOR-5'),
    ('SFOR-6',  'vless://6ca8ea5b-e47f-4c19-adee-365456e1e87c@31.56.188.78:7443?security=reality&encryption=none&pbk=5QAO98ot2U7TcGs_f6EEaQjCzNOJLNHqPf6smYsdFVI&headerType=none&fp=firefox&type=tcp&flow=xtls-rprx-vision&sni=mi.com&sid=be0ce047#SFOR-6'),
    ('SFOR-7',  'vless://ad6d51ab-2d06-4d41-85b7-da9d703ea4fd@dnn4.avaaaal.ir:2087?security=tls&alpn=http%2F1.1&encryption=none&host=sv333.avaaal.ir&fp=random&type=ws&sni=sv333.avaaal.ir#SFOR-7'),
    ('SFOR-8',  'vless://8dc7722c-2767-4eea-a28b-2f8daacc07e3@sca17.myfymain.com:8880?mode=gun&security=&encryption=none&type=grpc#SFOR-8'),
    ('SFOR-9',  'vless://8dc7722c-2767-4eea-a28b-2f8daacc07e3@sca22.myfymain.com:8880?security=&encryption=none&type=grpc#SFOR-9'),
    ('SFOR-10', 'vless://931729a8-3c20-4841-89a1-f18dc9ce0a6f@46.229.243.137:8443?security=tls&encryption=none&type=tcp&sni=cdn7-09.vk-cdnvideo.com#SFOR-10'),
    ('SFOR-11', 'vless://da48859d-edf9-4a8c-a026-80910591f284@nytimes.com:80?mode=auto&path=%2FTignal&security=&encryption=none&host=tignaltofansv8.global.ssl.fastly.net&type=xhttp#SFOR-11'),
    ('SFOR-12', 'vless://0058c215-ab1e-400c-a403-b5b2fda7e846@199.232.197.131:80?path=%2F&security=&encryption=none&host=max-gb1.global.ssl.fastly.net&type=ws#SFOR-12'),
    ('SFOR-13', 'vless://8dc7722c-2767-4eea-a28b-2f8daacc07e3@sca21.myfymain.com:8880?mode=gun&security=&encryption=none&type=grpc#SFOR-13'),
]

def seed_configs():
    conn = db()
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM configs')
    if c.fetchone()[0] == 0:
        for name, link in DEFAULT_CONFIGS:
            c.execute('INSERT INTO configs (name,link,created_at) VALUES (?,?,?)',
                      (name, link, datetime.now().isoformat()))
    conn.commit()
    conn.close()

seed_configs()

# ═══════════════════════════════════════════
#         💬 پاسخ‌های خودکار پیش‌فرض
# ═══════════════════════════════════════════
DEFAULT_AUTO_REPLIES = [
    ('سلام', 'سلام! 👋 خوش اومدی به گروه SFOR'),
    ('هوش مصنوعی', '🤖 برای استفاده از AI بنویس: /ai سوالت'),
    ('فیلترشکن', '🔒 برای دریافت فیلترشکن رایگان: /config یا /vpn'),
    ('کانفیگ', '🔒 دستور /config رو بزن تا کانفیگ V2Ray رایگان بگیری!'),
    ('vpn', '🌐 دستور /vpn رو بزن تا فایل VPN رایگان بگیری!'),
    ('سایت', f'🌐 سایت SFOR: {SITE_URL}'),
    ('ربات', '🤖 این ربات SFOR هست! برای راهنما /help بزن'),
    ('هک', '🛡️ برای یادگیری هک و امنیت: ' + SITE_URL),
    ('برنامه نویسی', '💻 سوالت رو با /ai بپرس، AI جواب میده!'),
    ('ممنون', '🙏 خواهش میکنم! هر سوالی داری بپرس'),
    ('چطوری', '🔥 ممنون عالیم! تو چطوری؟'),
    ('درود', '👋 درود! خوش اومدی'),
    ('اینستاگرام', '📸 اینستا SFOR: @mmadsfor'),
    ('تلگرام', '📱 کانال و گروه SFOR رو فالو کن!'),
    ('امنیت', '🔐 برای مطالب امنیتی سایت SFOR رو چک کن: ' + SITE_URL),
    ('جوک', None),  # handled specially
    ('خلوته', None),  # handled specially
    ('حالت', '😊 ممنون که پرسیدی! حالم خوبه. تو چطوری؟'),
    ('کسله', '🎮 بیا یه بازی کنیم! به زودی بازی اضافه میشه...'),
    ('بازی', '🎮 سیستم بازی به زودی اضافه میشه! 🔜'),
    ('مشکل', '🛠️ مشکلت رو بگو، کمک میکنم!'),
]

def seed_auto_replies():
    conn = db()
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM auto_replies')
    if c.fetchone()[0] < 10:
        for kw, resp in DEFAULT_AUTO_REPLIES:
            if resp:
                try:
                    c.execute('INSERT OR IGNORE INTO auto_replies (keyword,response,match_type) VALUES (?,?,?)',
                              (kw, resp, 'contains'))
                except: pass
    conn.commit()
    conn.close()

seed_auto_replies()

# ═══════════════════════════════════════════
#         🤬 کلمات ممنوع (ضد فحش)
# ═══════════════════════════════════════════
BAD_WORDS = [
    'کصکش', 'کسکش', 'جنده', 'کونی', 'مادرجنده', 'پدرسگ',
    'گاییدم', 'کیرم', 'کسم', 'بکن', 'گائیدن', 'لاشی',
    'احمق', 'خفه', 'گمشو', 'بیشعور', 'نامرد', 'عوضی',
    'حرومزاده', 'ولدزنا', 'مادرقحبه', 'ننه', 'بابات',
]

def contains_profanity(text):
    if not text: return False
    text_lower = text.lower()
    for word in BAD_WORDS:
        if word.lower() in text_lower:
            return True
    return False

# ═══════════════════════════════════════════
#         🤣 جوک‌ها
# ═══════════════════════════════════════════
JOKES = [
    'یه برنامه‌نویس رفت دستشویی... ۳ ساعت نیومد. بعد گفت: دکمه فلاش نداشت! 😂',
    'چرا برنامه‌نویس‌ها عینک میزنن؟ چون C# میکنن! 🤓',
    'یه هکر رفت رستوران... گارسون گفت: سفارشتون؟ گفت: روت اکسس! 😅',
    'AI به انسان گفت: تو هوش مصنوعی هستی یا طبیعی؟ انسان گفت: نمیدونم، هنوز آزمایش میدم! 🤖',
    'چرا کامپیوتر سرما میخوره؟ چون Windows داره! 🤧',
    'یه ویروس رفت دکتر... دکتر گفت: آنتی‌ویروس میخوری؟ گفت: نه، میخوام firewall بشکنم! 😷',
    'برنامه‌نویس به دوستش گفت: ۱۰ نوع آدم داریم: اونایی که باینری میفهمن و اونایی که نه! 😂',
    'چرا برنامه‌نویسا با تاریکی مشکل ندارن؟ چون Dark Mode دارن! 🌙',
    'یه دانشمند AI ساخت که دروغ نمیگفت... اسمش رو گذاشت ChatGPT... بعدش پشیمون شد! 😅',
    'چرا گوگل هیچوقت تنها نیست؟ چون همیشه Search داره! 🔍',
]

LONELY_REPLIES = [
    'من اینجام! 🤗 چی میخوای؟',
    'گروه خلوته ولی منم هستم! 😄',
    'بیا باهام حرف بزن! از چی میخوای بدونی؟ 🤖',
    'خلوته ولی من همیشه آنلاینم! 24/7 خدمتگزارتم 🔥',
    'منم هستم! بپرس چی میخوای، جواب میدم 😊',
]

# ═══════════════════════════════════════════
#         🔧 توابع دیتابیس
# ═══════════════════════════════════════════
def add_user(user):
    conn = db()
    c = conn.cursor()
    c.execute('''INSERT OR IGNORE INTO users (id,username,first_name,joined_at,last_seen)
                 VALUES (?,?,?,?,?)''',
              (user.id, user.username, user.first_name,
               datetime.now().isoformat(), datetime.now().isoformat()))
    c.execute('UPDATE users SET username=?,first_name=?,last_seen=? WHERE id=?',
              (user.username, user.first_name, datetime.now().isoformat(), user.id))
    conn.commit()
    conn.close()

def add_group(chat):
    conn = db()
    c = conn.cursor()
    c.execute('''INSERT OR IGNORE INTO groups (id,title,joined_at)
                 VALUES (?,?,?)''',
              (chat.id, chat.title, datetime.now().isoformat()))
    c.execute('UPDATE groups SET title=? WHERE id=?', (chat.title, chat.id))
    conn.commit()
    conn.close()

def get_group(gid):
    conn = db()
    c = conn.cursor()
    c.execute('SELECT * FROM groups WHERE id=?', (gid,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

def update_group(gid, field, value):
    conn = db()
    c = conn.cursor()
    c.execute(f'UPDATE groups SET {field}=? WHERE id=?', (value, gid))
    conn.commit()
    conn.close()

def get_user(uid):
    conn = db()
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE id=?', (uid,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

def get_all_users():
    conn = db()
    c = conn.cursor()
    c.execute('SELECT id FROM users WHERE is_banned=0')
    rows = c.fetchall()
    conn.close()
    return [r[0] for r in rows]

def get_stats():
    conn = db()
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM users')
    users = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM groups')
    groups = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM configs WHERE is_used=0')
    configs = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM vpn_files WHERE is_used=0')
    vpns = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM logs')
    logs = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM auto_replies')
    replies = c.fetchone()[0]
    conn.close()
    return {'users': users, 'groups': groups, 'configs': configs,
            'vpns': vpns, 'logs': logs, 'replies': replies}

def add_warn(uid, gid, reason):
    conn = db()
    c = conn.cursor()
    c.execute('INSERT INTO warns (user_id,group_id,reason,warned_at) VALUES (?,?,?,?)',
              (uid, gid, reason, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_warns(uid, gid):
    conn = db()
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM warns WHERE user_id=? AND group_id=?', (uid, gid))
    count = c.fetchone()[0]
    conn.close()
    return count

def remove_warn(uid, gid):
    conn = db()
    c = conn.cursor()
    c.execute('''DELETE FROM warns WHERE id=(
        SELECT id FROM warns WHERE user_id=? AND group_id=?
        ORDER BY warned_at DESC LIMIT 1)''', (uid, gid))
    conn.commit()
    conn.close()

def clear_warns(uid, gid):
    conn = db()
    c = conn.cursor()
    c.execute('DELETE FROM warns WHERE user_id=? AND group_id=?', (uid, gid))
    conn.commit()
    conn.close()

def ban_user(uid):
    conn = db()
    c = conn.cursor()
    c.execute('UPDATE users SET is_banned=1 WHERE id=?', (uid,))
    conn.commit()
    conn.close()

def unban_user(uid):
    conn = db()
    c = conn.cursor()
    c.execute('UPDATE users SET is_banned=0 WHERE id=?', (uid,))
    conn.commit()
    conn.close()

def add_log(event, uid=None, gid=None, detail=None):
    conn = db()
    c = conn.cursor()
    c.execute('INSERT INTO logs (event_type,user_id,group_id,detail,created_at) VALUES (?,?,?,?,?)',
              (event, uid, gid, detail, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_logs(limit=20):
    conn = db()
    c = conn.cursor()
    c.execute('SELECT * FROM logs ORDER BY id DESC LIMIT ?', (limit,))
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def track_spam(uid, gid):
    conn = db()
    c = conn.cursor()
    now = datetime.now().isoformat()
    c.execute('SELECT count, last_time FROM spam_track WHERE user_id=? AND group_id=?', (uid, gid))
    row = c.fetchone()
    if row:
        last = datetime.fromisoformat(str(row[1]))  # row[1] = last_time
        if (datetime.now() - last).seconds < 10:
            new_count = row[0] + 1  # row[0] = count
        else:
            new_count = 1
        c.execute('UPDATE spam_track SET count=?,last_time=? WHERE user_id=? AND group_id=?',
                  (new_count, now, uid, gid))
    else:
        new_count = 1
        c.execute('INSERT INTO spam_track (user_id,group_id,count,last_time) VALUES (?,?,?,?)',
                  (uid, gid, 1, now))
    conn.commit()
    conn.close()
    return new_count

def reset_spam(uid, gid):
    conn = db()
    c = conn.cursor()
    c.execute('UPDATE spam_track SET count=0 WHERE user_id=? AND group_id=?', (uid, gid))
    conn.commit()
    conn.close()

def get_free_config():
    conn = db()
    c = conn.cursor()
    c.execute('SELECT id,name,link FROM configs WHERE is_used=0 LIMIT 1')
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

def mark_config_used(cid, uid):
    conn = db()
    c = conn.cursor()
    c.execute('UPDATE configs SET is_used=1,used_by=? WHERE id=?', (uid, cid))
    c.execute('INSERT OR IGNORE INTO user_configs (user_id,given_at) VALUES (?,?)',
              (uid, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def user_has_config(uid):
    conn = db()
    c = conn.cursor()
    c.execute('SELECT 1 FROM user_configs WHERE user_id=?', (uid,))
    r = c.fetchone()
    conn.close()
    return r is not None

def get_free_vpn():
    conn = db()
    c = conn.cursor()
    c.execute('SELECT id,name,file_id FROM vpn_files WHERE is_used=0 LIMIT 1')
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

def mark_vpn_used(vid, uid):
    conn = db()
    c = conn.cursor()
    c.execute('UPDATE vpn_files SET is_used=1,used_by=? WHERE id=?', (uid, vid))
    c.execute('INSERT OR IGNORE INTO user_vpns (user_id,given_at) VALUES (?,?)',
              (uid, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def user_has_vpn(uid):
    conn = db()
    c = conn.cursor()
    c.execute('SELECT 1 FROM user_vpns WHERE user_id=?', (uid,))
    r = c.fetchone()
    conn.close()
    return r is not None

def add_vpn_file(name, file_id):
    conn = db()
    c = conn.cursor()
    c.execute('INSERT INTO vpn_files (name,file_id,created_at) VALUES (?,?,?)',
              (name, file_id, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_ai_history(uid, limit=6):
    conn = db()
    c = conn.cursor()
    c.execute('SELECT role,content FROM ai_history WHERE user_id=? ORDER BY id DESC LIMIT ?',
              (uid, limit))
    rows = c.fetchall()
    conn.close()
    return list(reversed([(r[0], r[1]) for r in rows]))

def add_ai_history(uid, role, content):
    conn = db()
    c = conn.cursor()
    c.execute('INSERT INTO ai_history (user_id,role,content,created_at) VALUES (?,?,?,?)',
              (uid, role, content, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def clear_ai_history(uid):
    conn = db()
    c = conn.cursor()
    c.execute('DELETE FROM ai_history WHERE user_id=?', (uid,))
    conn.commit()
    conn.close()

def get_auto_replies():
    conn = db()
    c = conn.cursor()
    c.execute('SELECT keyword,response,match_type FROM auto_replies')
    rows = c.fetchall()
    conn.close()
    return [(r[0], r[1], r[2]) for r in rows]

def save_note(uid, gid, name, content):
    conn = db()
    c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO notes (user_id,group_id,name,content,created_at) VALUES (?,?,?,?,?)',
              (uid, gid, name, content, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_note(gid, name):
    conn = db()
    c = conn.cursor()
    c.execute('SELECT content FROM notes WHERE group_id=? AND name=?', (gid, name))
    r = c.fetchone()
    conn.close()
    return r[0] if r else None

# ═══════════════════════════════════════════
#         🤖 Gemini AI
# ═══════════════════════════════════════════
SYSTEM_PROMPT = f"""تو هوش مصنوعی ربات SFOR هستی.
سایت SFOR: {SITE_URL}
اینستاگرام: @mmadsfor

وظایف تو:
- کمک در زمینه امنیت سایبری، هک اخلاقی، برنامه‌نویسی و فناوری
- معرفی سایت SFOR به کاربران (امنیت، ابزارها، آموزش، فیلترشکن)
- پاسخ به سوالات فارسی به صورت مختصر و مفید
- اگر کسی درباره سایت، ربات یا SFOR پرسید، معرفی کن
- اگر درباره فیلترشکن پرسید، بگو /config یا /vpn بزنن

قوانین:
- همیشه فارسی جواب بده
- کوتاه و مفید باش (حداکثر 200 کلمه)
- دوستانه و صمیمی باش
- اگر سوال خطرناک یا غیراخلاقی بود، رد کن"""

def ask_gemini(uid, message):
    history = get_ai_history(uid, limit=6)
    contents = [{'role': r, 'parts': [{'text': c}]} for r, c in history]
    contents.append({'role': 'user', 'parts': [{'text': message}]})
    payload = {
        'system_instruction': {'parts': [{'text': SYSTEM_PROMPT}]},
        'contents': contents,
        'generationConfig': {'maxOutputTokens': 600, 'temperature': 0.7}
    }
    try:
        r = requests.post(
            f'{GEMINI_URL}?key={GEMINI_KEY}',
            json=payload, timeout=25
        )
        data = r.json()
        if 'candidates' in data:
            reply = data['candidates'][0]['content']['parts'][0]['text']
        elif 'error' in data:
            reply = f"⚠️ خطای AI: {data['error']['message'][:100]}"
        else:
            reply = f"⚠️ پاسخ نامشخص"
        add_ai_history(uid, 'user', message)
        add_ai_history(uid, 'model', reply)
        return reply
    except Exception as e:
        return f'⚠️ خطا در اتصال به AI: {str(e)[:80]}'

# ═══════════════════════════════════════════
#         🛡️ توابع کمکی
# ═══════════════════════════════════════════
def is_group_admin(cid, uid):
    try:
        m = bot.get_chat_member(cid, uid)
        return m.status in ['administrator', 'creator']
    except:
        return False

def is_link(text):
    if not text: return False
    patterns = [r'https?://', r't\.me/', r'telegram\.me/', r'@\w{4,}',
                r'bit\.ly', r'tinyurl', r'youtu\.be', r'wa\.me']
    return any(re.search(p, text, re.I) for p in patterns)

def mute_user(cid, uid, seconds=300):
    until = int(time.time()) + seconds
    bot.restrict_chat_member(cid, uid,
        permissions=ChatPermissions(can_send_messages=False),
        until_date=until)

def safe_delete(cid, mid):
    try:
        bot.delete_message(cid, mid)
    except: pass

def safe_send(cid, text, **kwargs):
    try:
        return bot.send_message(cid, text, **kwargs)
    except: pass

# ═══════════════════════════════════════════
#         🎨 منوها
# ═══════════════════════════════════════════
def main_menu():
    m = InlineKeyboardMarkup(row_width=2)
    m.add(
        InlineKeyboardButton('🌐 سایت SFOR', url=SITE_URL),
        InlineKeyboardButton('🤖 هوش مصنوعی', callback_data='ai_chat'),
    )
    m.add(
        InlineKeyboardButton('🔒 کانفیگ V2Ray', callback_data='get_config'),
        InlineKeyboardButton('📁 فایل VPN', callback_data='get_vpn'),
    )
    m.add(
        InlineKeyboardButton('📚 آموزش', url=f'{SITE_URL}/tutorials'),
        InlineKeyboardButton('🛡️ ابزارها', url=f'{SITE_URL}/#tools'),
    )
    m.add(
        InlineKeyboardButton('👤 پروفایل من', callback_data='my_profile'),
        InlineKeyboardButton('📨 پیام ناشناس', callback_data='anon'),
    )
    m.add(
        InlineKeyboardButton('📣 معرفی به دوستان', callback_data='share'),
        InlineKeyboardButton('ℹ️ درباره SFOR', callback_data='about'),
    )
    return m

def admin_menu():
    m = InlineKeyboardMarkup(row_width=2)
    m.add(
        InlineKeyboardButton('📊 آمار کلی', callback_data='adm_stats'),
        InlineKeyboardButton('👥 کاربران', callback_data='adm_users'),
    )
    m.add(
        InlineKeyboardButton('🏘️ گروه‌ها', callback_data='adm_groups'),
        InlineKeyboardButton('📋 لاگ‌ها', callback_data='adm_logs'),
    )
    m.add(
        InlineKeyboardButton('🔒 افزودن کانفیگ', callback_data='adm_addconfig'),
        InlineKeyboardButton('📁 آپلود VPN', callback_data='adm_addvpn'),
    )
    m.add(
        InlineKeyboardButton('💬 پاسخ خودکار', callback_data='adm_autoreplies'),
        InlineKeyboardButton('📢 پیام همگانی', callback_data='adm_broadcast'),
    )
    m.add(
        InlineKeyboardButton('⚙️ تنظیمات ربات', callback_data='adm_settings'),
        InlineKeyboardButton('🔙 منوی اصلی', callback_data='back_main'),
    )
    return m

def group_settings_menu(gid):
    g = get_group(gid)
    if not g: return InlineKeyboardMarkup()
    def s(v): return '✅' if v else '❌'
    m = InlineKeyboardMarkup(row_width=2)
    m.add(
        InlineKeyboardButton(f'🔗 ضد لینک {s(g["anti_link"])}', callback_data=f'grp_antilink_{gid}'),
        InlineKeyboardButton(f'🚫 ضد اسپم {s(g["anti_spam"])}', callback_data=f'grp_antispam_{gid}'),
    )
    m.add(
        InlineKeyboardButton(f'🤬 ضد فحش {s(g["anti_profanity"])}', callback_data=f'grp_antiprofanity_{gid}'),
        InlineKeyboardButton(f'👋 خوش‌آمد {s(g["welcome"])}', callback_data=f'grp_welcome_{gid}'),
    )
    m.add(
        InlineKeyboardButton(f'👋 خداحافظ {s(g["goodbye"])}', callback_data=f'grp_goodbye_{gid}'),
        InlineKeyboardButton(f'🤖 AI گروه {s(g["ai_reply"])}', callback_data=f'grp_ai_{gid}'),
    )
    m.add(
        InlineKeyboardButton(f'⚠️ حد اخطار: {g["warn_limit"]}', callback_data=f'grp_warnlimit_{gid}'),
        InlineKeyboardButton('📌 قوانین', callback_data=f'grp_rules_{gid}'),
    )
    m.add(
        InlineKeyboardButton('✍️ متن خوش‌آمد', callback_data=f'grp_setwelcome_{gid}'),
        InlineKeyboardButton('🔙 برگشت', callback_data='adm_groups'),
    )
    return m

# ═══════════════════════════════════════════
#         📋 راهنما
# ═══════════════════════════════════════════
HELP_TEXT = """📖 *دستورات ربات SFOR v3*

🔹 *عمومی:*
/start | /شروع — شروع ربات
/help | /راهنما — این راهنما
/id | /آیدی — نمایش آیدی
/ai سوال | /هوش سوال — هوش مصنوعی
/config | /کانفیگ — کانفیگ V2Ray رایگان
/vpn | /فیلترشکن — فایل VPN رایگان
/ping | /پینگ — تست سرعت
/time | /ساعت — ساعت سرور
/note نام متن | /یادداشت — ذخیره یادداشت
/rules | /قوانین — قوانین گروه

🔸 *مدیریت گروه (ادمین):*
/warn [دلیل] | /اخطار — اخطار به کاربر
/unwarn | /رفع‌اخطار — رفع اخطار
/warns | /اخطارها — تعداد اخطار
/clearwarns | /پاک‌اخطار — پاک کردن اخطارها
/kick | /اخراج — اخراج از گروه
/ban | /بن — بن کردن
/unban | /رفع‌بن — رفع بن
/mute [دقیقه] | /سکوت — میوت
/unmute | /رفع‌سکوت — رفع میوت
/pin | /پین — پین پیام
/setrules | /تنظیم‌قوانین — تنظیم قوانین
/settings | /تنظیمات — پنل تنظیمات گروه

🎮 *سرگرمی:*
جوک — جوک خنده‌دار
خلوته — من اینجام!

⭐ *ادمین اصلی:*
/panel — پنل مدیریت کامل
/broadcast | /همگانی — پیام همگانی
/addconfig — افزودن کانفیگ
/logs | /لاگ — لاگ رویدادها
/anon — پیام ناشناس

💡 در گروه بنویس *پنل* تا پنل مدیریت گروه بیاد!"""

# ═══════════════════════════════════════════
#         📡 دستورات
# ═══════════════════════════════════════════
@bot.message_handler(commands=['start', 'شروع'])
def start_cmd(message):
    add_user(message.from_user)
    name = message.from_user.first_name or 'کاربر'
    text = (f'سلام *{name}* عزیز! 👋\n\n'
            '🔥 به *ربات SFOR* خوش اومدی!\n\n'
            '━━━━━━━━━━━━━━━\n'
            '🤖 هوش مصنوعی Gemini\n'
            '🔒 کانفیگ V2Ray رایگان\n'
            '📁 فایل VPN رایگان\n'
            '🛡️ مدیریت هوشمند گروه\n'
            '📚 آموزش امنیت و هک\n'
            '━━━━━━━━━━━━━━━\n\n'
            'از منوی زیر انتخاب کن 👇')
    bot.send_message(message.chat.id, text, parse_mode='Markdown', reply_markup=main_menu())
    add_log('start', message.from_user.id)

@bot.message_handler(commands=['help', 'راهنما'])
def help_cmd(message):
    bot.reply_to(message, HELP_TEXT, parse_mode='Markdown')

@bot.message_handler(commands=['id', 'آیدی'])
def id_cmd(message):
    if message.reply_to_message:
        u = message.reply_to_message.from_user
    else:
        u = message.from_user
    text = f'👤 *{u.first_name}*\n🆔 `{u.id}`\n📛 @{u.username or "ندارد"}'
    bot.reply_to(message, text, parse_mode='Markdown')

@bot.message_handler(commands=['ping', 'پینگ'])
def ping_cmd(message):
    t = time.time()
    msg = bot.reply_to(message, '🏓 ...')
    ms = int((time.time() - t) * 1000)
    bot.edit_message_text(f'🏓 *Pong!*\n⚡ `{ms}ms`', message.chat.id, msg.message_id, parse_mode='Markdown')

@bot.message_handler(commands=['time', 'ساعت'])
def time_cmd(message):
    now = datetime.now().strftime('%Y/%m/%d — %H:%M:%S')
    bot.reply_to(message, f'🕐 `{now}`', parse_mode='Markdown')

@bot.message_handler(commands=['ai', 'هوش'])
def ai_cmd(message):
    add_user(message.from_user)
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, '❓ سوالت رو بعد از دستور بنویس:\n`/ai چطور هک اخلاقی یاد بگیرم؟`', parse_mode='Markdown')
        return
    msg = bot.reply_to(message, '🤖 *در حال پردازش...*', parse_mode='Markdown')
    reply = ask_gemini(message.from_user.id, parts[1])
    try:
        bot.edit_message_text(f'🤖 *SFOR AI:*\n\n{reply}', message.chat.id, msg.message_id, parse_mode='Markdown')
    except:
        bot.send_message(message.chat.id, f'🤖 *SFOR AI:*\n\n{reply}', parse_mode='Markdown')

@bot.message_handler(commands=['config', 'کانفیگ'])
def config_cmd(message):
    add_user(message.from_user)
    uid = message.from_user.id
    if user_has_config(uid) and uid != ADMIN_ID:
        bot.reply_to(message,
            '⚠️ *قبلاً کانفیگ دریافت کردی!*\n\nبرای کانفیگ جدید: t.me/Sfor34',
            parse_mode='Markdown')
        return
    cfg = get_free_config()
    if not cfg:
        bot.reply_to(message, '⏳ کانفیگ موجود نیست! به زودی اضافه میشه.', parse_mode='Markdown')
        return
    m = InlineKeyboardMarkup()
    m.add(InlineKeyboardButton('📲 آموزش اتصال', url=f'{SITE_URL}/vpn'))
    bot.reply_to(message,
        f'🔒 *کانفیگ رایگان SFOR*\n\n📛 `{cfg["name"]}`\n\n🔗\n`{cfg["link"]}`\n\n'
        '📌 V2RayNG (اندروید) یا V2Box (iOS)',
        parse_mode='Markdown', reply_markup=m)
    if uid != ADMIN_ID:
        mark_config_used(cfg['id'], uid)
    add_log('config_given', uid)

@bot.message_handler(commands=['vpn', 'فیلترشکن'])
def vpn_cmd(message):
    add_user(message.from_user)
    uid = message.from_user.id
    if user_has_vpn(uid) and uid != ADMIN_ID:
        bot.reply_to(message, '⚠️ *قبلاً VPN دریافت کردی!*\n\nبرای VPN جدید: t.me/Sfor34', parse_mode='Markdown')
        return
    vpn = get_free_vpn()
    if not vpn:
        bot.reply_to(message, '⏳ *VPN موجود نیست!*\n\nاز /config برای V2Ray استفاده کن.', parse_mode='Markdown')
        return
    try:
        bot.send_document(uid, vpn['file_id'], caption=f'🔒 {vpn["name"]}\n\n📱 نرم‌افزار: NPV Tunnel')
        if uid != ADMIN_ID:
            mark_vpn_used(vpn['id'], uid)
        add_log('vpn_given', uid)
        bot.reply_to(message, '✅ فایل VPN ارسال شد!', parse_mode='Markdown')
    except Exception as e:
        bot.reply_to(message, f'❌ خطا: {e}')

@bot.message_handler(commands=['note', 'یادداشت'])
def note_cmd(message):
    parts = message.text.split(maxsplit=2)
    if len(parts) == 3:
        save_note(message.from_user.id, message.chat.id, parts[1], parts[2])
        bot.reply_to(message, f'✅ یادداشت *{parts[1]}* ذخیره شد.', parse_mode='Markdown')
    elif len(parts) == 2:
        content = get_note(message.chat.id, parts[1])
        if content:
            bot.reply_to(message, f'📝 *{parts[1]}:*\n{content}', parse_mode='Markdown')
        else:
            bot.reply_to(message, f'❌ یادداشت *{parts[1]}* پیدا نشد.', parse_mode='Markdown')
    else:
        bot.reply_to(message, '📝 `/note نام متن` — ذخیره\n`/note نام` — خواندن', parse_mode='Markdown')

@bot.message_handler(commands=['rules', 'قوانین'])
def rules_cmd(message):
    if message.chat.type == 'private':
        bot.reply_to(message, '⚠️ این دستور فقط در گروه کار میکنه.'); return
    g = get_group(message.chat.id)
    rules = g['rules'] if g and g['rules'] else 'قوانینی تنظیم نشده.'
    bot.reply_to(message, f'📌 *قوانین گروه:*\n\n{rules}', parse_mode='Markdown')

@bot.message_handler(commands=['setrules', 'تنظیم_قوانین'])
def setrules_cmd(message):
    if message.chat.type == 'private': return
    if not is_group_admin(message.chat.id, message.from_user.id):
        bot.reply_to(message, '⛔ فقط ادمین‌ها.'); return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, '`/setrules متن قوانین`', parse_mode='Markdown'); return
    add_group(message.chat)
    update_group(message.chat.id, 'rules', parts[1])
    bot.reply_to(message, '✅ قوانین گروه تنظیم شد.')

@bot.message_handler(commands=['settings', 'تنظیمات'])
def settings_cmd(message):
    if message.chat.type == 'private':
        bot.reply_to(message, '⚠️ این دستور فقط در گروه کار میکنه.'); return
    if not is_group_admin(message.chat.id, message.from_user.id):
        bot.reply_to(message, '⛔ فقط ادمین‌ها.'); return
    add_group(message.chat)
    bot.reply_to(message, f'⚙️ *تنظیمات {message.chat.title}*',
                 parse_mode='Markdown', reply_markup=group_settings_menu(message.chat.id))

# ─── مدیریت گروه ───
@bot.message_handler(commands=['warn', 'اخطار'])
def warn_cmd(message):
    if message.chat.type == 'private': return
    if not is_group_admin(message.chat.id, message.from_user.id):
        bot.reply_to(message, '⛔ فقط ادمین‌ها.'); return
    if not message.reply_to_message:
        bot.reply_to(message, '↩️ روی پیام کاربر Reply کن.'); return
    target = message.reply_to_message.from_user
    if is_group_admin(message.chat.id, target.id):
        bot.reply_to(message, '⛔ نمیشه به ادمین اخطار داد.'); return
    parts = message.text.split(maxsplit=1)
    reason = parts[1] if len(parts) > 1 else 'بدون دلیل'
    add_warn(target.id, message.chat.id, reason)
    count = get_warns(target.id, message.chat.id)
    g = get_group(message.chat.id)
    limit = g['warn_limit'] if g else 3
    if count >= limit:
        try:
            bot.kick_chat_member(message.chat.id, target.id)
            bot.reply_to(message, f'🚫 *{target.first_name}* بعد از {count} اخطار اخراج شد!', parse_mode='Markdown')
            clear_warns(target.id, message.chat.id)
        except: pass
    else:
        bot.reply_to(message, f'⚠️ *اخطار به {target.first_name}*\n📋 {reason}\n🔢 {count}/{limit}', parse_mode='Markdown')
    add_log('warn', message.from_user.id, message.chat.id, str(target.id))

@bot.message_handler(commands=['unwarn', 'رفع_اخطار'])
def unwarn_cmd(message):
    if message.chat.type == 'private': return
    if not is_group_admin(message.chat.id, message.from_user.id):
        bot.reply_to(message, '⛔ فقط ادمین‌ها.'); return
    if not message.reply_to_message:
        bot.reply_to(message, '↩️ Reply کن.'); return
    target = message.reply_to_message.from_user
    remove_warn(target.id, message.chat.id)
    count = get_warns(target.id, message.chat.id)
    bot.reply_to(message, f'✅ یک اخطار از *{target.first_name}* حذف شد. ({count} باقیمانده)', parse_mode='Markdown')

@bot.message_handler(commands=['warns', 'اخطارها'])
def warns_cmd(message):
    if message.chat.type == 'private': return
    target = message.reply_to_message.from_user if message.reply_to_message else message.from_user
    count = get_warns(target.id, message.chat.id)
    g = get_group(message.chat.id)
    limit = g['warn_limit'] if g else 3
    bot.reply_to(message, f'⚠️ *{target.first_name}*: {count}/{limit}', parse_mode='Markdown')

@bot.message_handler(commands=['clearwarns', 'پاک_اخطار'])
def clearwarns_cmd(message):
    if message.chat.type == 'private': return
    if not is_group_admin(message.chat.id, message.from_user.id):
        bot.reply_to(message, '⛔ فقط ادمین‌ها.'); return
    if not message.reply_to_message:
        bot.reply_to(message, '↩️ Reply کن.'); return
    target = message.reply_to_message.from_user
    clear_warns(target.id, message.chat.id)
    bot.reply_to(message, f'✅ اخطارهای *{target.first_name}* پاک شد.', parse_mode='Markdown')

@bot.message_handler(commands=['kick', 'اخراج'])
def kick_cmd(message):
    if message.chat.type == 'private': return
    if not is_group_admin(message.chat.id, message.from_user.id):
        bot.reply_to(message, '⛔ فقط ادمین‌ها.'); return
    if not message.reply_to_message:
        bot.reply_to(message, '↩️ Reply کن.'); return
    target = message.reply_to_message.from_user
    try:
        bot.kick_chat_member(message.chat.id, target.id)
        bot.unban_chat_member(message.chat.id, target.id)
        bot.reply_to(message, f'🚪 *{target.first_name}* اخراج شد.', parse_mode='Markdown')
        add_log('kick', message.from_user.id, message.chat.id, str(target.id))
    except Exception as e:
        bot.reply_to(message, f'❌ {e}')

@bot.message_handler(commands=['ban', 'بن'])
def ban_cmd(message):
    if message.chat.type == 'private': return
    if not is_group_admin(message.chat.id, message.from_user.id):
        bot.reply_to(message, '⛔ فقط ادمین‌ها.'); return
    if not message.reply_to_message:
        bot.reply_to(message, '↩️ Reply کن.'); return
    target = message.reply_to_message.from_user
    try:
        bot.kick_chat_member(message.chat.id, target.id)
        ban_user(target.id)
        bot.reply_to(message, f'🔨 *{target.first_name}* بن شد.', parse_mode='Markdown')
        add_log('ban', message.from_user.id, message.chat.id, str(target.id))
    except Exception as e:
        bot.reply_to(message, f'❌ {e}')

@bot.message_handler(commands=['unban', 'رفع_بن'])
def unban_cmd(message):
    if message.chat.type == 'private': return
    if not is_group_admin(message.chat.id, message.from_user.id):
        bot.reply_to(message, '⛔ فقط ادمین‌ها.'); return
    if not message.reply_to_message:
        bot.reply_to(message, '↩️ Reply کن.'); return
    target = message.reply_to_message.from_user
    try:
        bot.unban_chat_member(message.chat.id, target.id)
        unban_user(target.id)
        bot.reply_to(message, f'✅ بن *{target.first_name}* برداشته شد.', parse_mode='Markdown')
    except Exception as e:
        bot.reply_to(message, f'❌ {e}')

@bot.message_handler(commands=['mute', 'سکوت'])
def mute_cmd(message):
    if message.chat.type == 'private': return
    if not is_group_admin(message.chat.id, message.from_user.id):
        bot.reply_to(message, '⛔ فقط ادمین‌ها.'); return
    if not message.reply_to_message:
        bot.reply_to(message, '↩️ Reply کن.'); return
    target = message.reply_to_message.from_user
    parts = message.text.split()
    minutes = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 60
    try:
        mute_user(message.chat.id, target.id, minutes * 60)
        bot.reply_to(message, f'🔇 *{target.first_name}* {minutes} دقیقه میوت شد.', parse_mode='Markdown')
        add_log('mute', message.from_user.id, message.chat.id, f'{target.id} {minutes}min')
    except Exception as e:
        bot.reply_to(message, f'❌ {e}')

@bot.message_handler(commands=['unmute', 'رفع_سکوت'])
def unmute_cmd(message):
    if message.chat.type == 'private': return
    if not is_group_admin(message.chat.id, message.from_user.id):
        bot.reply_to(message, '⛔ فقط ادمین‌ها.'); return
    if not message.reply_to_message:
        bot.reply_to(message, '↩️ Reply کن.'); return
    target = message.reply_to_message.from_user
    try:
        bot.restrict_chat_member(message.chat.id, target.id,
            permissions=ChatPermissions(
                can_send_messages=True, can_send_media_messages=True,
                can_send_polls=True, can_send_other_messages=True,
                can_add_web_page_previews=True))
        bot.reply_to(message, f'🔊 میوت *{target.first_name}* برداشته شد.', parse_mode='Markdown')
    except Exception as e:
        bot.reply_to(message, f'❌ {e}')

@bot.message_handler(commands=['pin', 'پین'])
def pin_cmd(message):
    if message.chat.type == 'private': return
    if not is_group_admin(message.chat.id, message.from_user.id):
        bot.reply_to(message, '⛔ فقط ادمین‌ها.'); return
    if not message.reply_to_message:
        bot.reply_to(message, '↩️ Reply کن.'); return
    try:
        bot.pin_chat_message(message.chat.id, message.reply_to_message.message_id)
        bot.reply_to(message, '📌 پین شد.')
    except Exception as e:
        bot.reply_to(message, f'❌ {e}')

@bot.message_handler(commands=['anon'])
def anon_cmd(message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, '📨 `/anon پیامت`', parse_mode='Markdown'); return
    try:
        bot.send_message(ADMIN_ID, f'📨 *پیام ناشناس:*\n\n{parts[1]}', parse_mode='Markdown')
        bot.reply_to(message, '✅ پیامت ارسال شد!')
    except:
        bot.reply_to(message, '❌ خطا در ارسال.')

# ─── پنل ادمین اصلی ───
@bot.message_handler(commands=['panel'])
def panel_cmd(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, '⛔ دسترسی ندارید.'); return
    stats = get_stats()
    text = (f'🔥 *پنل ادمین SFOR v{BOT_VERSION}*\n\n'
            f'👥 کاربران: `{stats["users"]}`\n'
            f'🏘️ گروه‌ها: `{stats["groups"]}`\n'
            f'🔒 کانفیگ باقیمانده: `{stats["configs"]}`\n'
            f'📁 VPN باقیمانده: `{stats["vpns"]}`\n'
            f'💬 پاسخ خودکار: `{stats["replies"]}`\n'
            f'📋 لاگ: `{stats["logs"]}`\n')
    bot.reply_to(message, text, parse_mode='Markdown', reply_markup=admin_menu())

@bot.message_handler(commands=['broadcast', 'همگانی'])
def broadcast_cmd(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, '⛔'); return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, '`/broadcast متن`', parse_mode='Markdown'); return
    users = get_all_users()
    ok = fail = 0
    for uid in users:
        try:
            bot.send_message(uid, f'📢 *پیام SFOR:*\n\n{parts[1]}', parse_mode='Markdown')
            ok += 1
        except:
            fail += 1
        time.sleep(0.05)
    bot.reply_to(message, f'✅ موفق: {ok} | ❌ ناموفق: {fail}')

@bot.message_handler(commands=['addconfig'])
def addconfig_cmd(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, '⛔'); return
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        bot.reply_to(message, '`/addconfig نام لینک`', parse_mode='Markdown'); return
    conn = db()
    c = conn.cursor()
    c.execute('INSERT INTO configs (name,link,created_at) VALUES (?,?,?)',
              (parts[1], parts[2], datetime.now().isoformat()))
    conn.commit()
    conn.close()
    bot.reply_to(message, f'✅ کانفیگ *{parts[1]}* اضافه شد.', parse_mode='Markdown')

@bot.message_handler(commands=['logs', 'لاگ'])
def logs_cmd(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, '⛔'); return
    logs = get_logs(15)
    if not logs:
        bot.reply_to(message, '📋 لاگی وجود ندارد.'); return
    text = '📋 *لاگ‌های اخیر:*\n\n'
    for log in logs:
        text += f'• `{log["event_type"]}` — u:{log["user_id"]} — {str(log["detail"] or "")[:25]}\n'
    bot.reply_to(message, text, parse_mode='Markdown')

# ═══════════════════════════════════════════
#         📁 آپلود VPN از طریق ربات
# ═══════════════════════════════════════════
pending_vpn_upload = {}

@bot.message_handler(commands=['addvpn'])
def addvpn_cmd(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, '⛔'); return
    pending_vpn_upload[ADMIN_ID] = True
    bot.reply_to(message, '📁 فایل VPN رو بفرست (npvt یا هر فرمتی):')

@bot.message_handler(content_types=['document'])
def handle_document(message):
    uid = message.from_user.id
    if uid == ADMIN_ID and pending_vpn_upload.get(ADMIN_ID):
        file_id = message.document.file_id
        name = message.document.file_name or f'VPN-{int(time.time())}'
        add_vpn_file(name, file_id)
        pending_vpn_upload.pop(ADMIN_ID, None)
        bot.reply_to(message, f'✅ فایل *{name}* آپلود شد!', parse_mode='Markdown')
        add_log('vpn_uploaded', uid, detail=name)

# ═══════════════════════════════════════════
#         👋 رویدادهای گروه
# ═══════════════════════════════════════════
@bot.message_handler(content_types=['new_chat_members'])
def welcome_handler(message):
    add_group(message.chat)
    g = get_group(message.chat.id)
    if not g or not g['welcome']: return
    for member in message.new_chat_members:
        if member.is_bot: continue
        add_user(member)
        name = member.first_name
        wmsg = g['welcome_msg'] if g['welcome_msg'] else f'👋 خوش اومدی *{name}* عزیز!\n\n🔥 به گروه SFOR خوش اومدی!'
        wmsg = wmsg.replace('{name}', f'*{name}*')
        m = InlineKeyboardMarkup()
        if g['rules']:
            m.add(InlineKeyboardButton('📜 قوانین گروه', callback_data=f'show_rules_{message.chat.id}'))
        safe_send(message.chat.id, wmsg, parse_mode='Markdown', reply_markup=m)

@bot.message_handler(content_types=['left_chat_member'])
def goodbye_handler(message):
    g = get_group(message.chat.id)
    if not g or not g['goodbye']: return
    name = message.left_chat_member.first_name
    gmsg = g['goodbye_msg'] if g['goodbye_msg'] else f'👋 *{name}* گروه رو ترک کرد.'
    gmsg = gmsg.replace('{name}', f'*{name}*')
    safe_send(message.chat.id, gmsg, parse_mode='Markdown')

# ═══════════════════════════════════════════
#         🚨 فیلتر پیام‌های گروه
# ═══════════════════════════════════════════
@bot.message_handler(func=lambda m: m.chat.type in ['group', 'supergroup'])
def group_message_handler(message):
    add_group(message.chat)
    if not message.from_user: return
    add_user(message.from_user)
    uid = message.from_user.id
    cid = message.chat.id

    # ادمین‌ها از فیلترها معاف‌اند
    if is_group_admin(cid, uid): pass
    else:
        g = get_group(cid)
        if not g: return
        text = message.text or message.caption or ''

        # ─── ضد فحش ───
        if g['anti_profanity'] and contains_profanity(text):
            safe_delete(cid, message.message_id)
            safe_send(cid, f'🤬 *{message.from_user.first_name}* کلمه ممنوع فرستاد!', parse_mode='Markdown')
            add_warn(uid, cid, 'کلمه ممنوع')
            count = get_warns(uid, cid)
            if count >= g['warn_limit']:
                try:
                    bot.kick_chat_member(cid, uid)
                    clear_warns(uid, cid)
                except: pass
            add_log('anti_profanity', uid, cid)
            return

        # ─── ضد لینک ───
        if g['anti_link'] and is_link(text):
            safe_delete(cid, message.message_id)
            safe_send(cid, f'🔗 *{message.from_user.first_name}* لینک فرستاد و حذف شد!', parse_mode='Markdown')
            add_log('anti_link', uid, cid)
            return

        # ─── ضد اسپم ───
        if g['anti_spam']:
            count = track_spam(uid, cid)
            if count >= 8:
                try:
                    mute_user(cid, uid, 300)
                    safe_send(cid, f'🚫 *{message.from_user.first_name}* اسپم کرد و ۵ دقیقه میوت شد!', parse_mode='Markdown')
                    reset_spam(uid, cid)
                    add_log('anti_spam', uid, cid)
                except: pass

        # ─── فیلتر کلمات سفارشی ───
        if g['filter_words'] and text:
            bad = [w.strip() for w in g['filter_words'].split(',') if w.strip()]
            for word in bad:
                if word.lower() in text.lower():
                    safe_delete(cid, message.message_id)
                    safe_send(cid, f'🚫 پیام *{message.from_user.first_name}* حذف شد.', parse_mode='Markdown')
                    return

    # ─── پنل در گروه ───
    if message.text and message.text.strip() in ['پنل', 'panel']:
        if is_group_admin(message.chat.id, uid):
            add_group(message.chat)
            bot.reply_to(message, f'⚙️ *پنل مدیریت {message.chat.title}*',
                         parse_mode='Markdown', reply_markup=group_settings_menu(message.chat.id))
        return

    # ─── جوک ───
    if message.text and any(w in message.text.lower() for w in ['جوک', 'joke', 'خنده']):
        bot.reply_to(message, random.choice(JOKES))
        return

    # ─── خلوته ───
    if message.text and any(w in message.text.lower() for w in ['خلوته', 'خلوت', 'کسی نیست']):
        bot.reply_to(message, random.choice(LONELY_REPLIES))
        return

    # ─── AI گروه (منشن) ───
    g = get_group(message.chat.id)
    if g and g['ai_reply'] and message.text:
        me = bot.get_me()
        if f'@{me.username}' in message.text:
            question = message.text.replace(f'@{me.username}', '').strip()
            if question:
                reply = ask_gemini(uid, question)
                bot.reply_to(message, f'🤖 {reply}')
            return

    # ─── پاسخ خودکار ───
    if message.text:
        for keyword, response, match_type in get_auto_replies():
            if match_type == 'exact' and message.text == keyword:
                bot.reply_to(message, response); break
            elif match_type == 'contains' and keyword.lower() in message.text.lower():
                bot.reply_to(message, response); break

    # ─── شمارش پیام ───
    conn = db()
    c = conn.cursor()
    c.execute('UPDATE users SET message_count=message_count+1 WHERE id=?', (uid,))
    conn.commit()
    conn.close()

# ═══════════════════════════════════════════
#         💬 پیام‌های خصوصی
# ═══════════════════════════════════════════
@bot.message_handler(func=lambda m: m.chat.type == 'private')
def private_message_handler(message):
    add_user(message.from_user)
    if not message.text or message.text.startswith('/'): return

    # جوک در خصوصی
    if any(w in message.text.lower() for w in ['جوک', 'joke']):
        bot.reply_to(message, random.choice(JOKES)); return

    # AI در خصوصی
    msg = bot.reply_to(message, '🤖 در حال پردازش...')
    reply = ask_gemini(message.from_user.id, message.text)
    try:
        bot.edit_message_text(f'🤖 *SFOR AI:*\n\n{reply}', message.chat.id, msg.message_id, parse_mode='Markdown')
    except:
        bot.send_message(message.chat.id, f'🤖 *SFOR AI:*\n\n{reply}', parse_mode='Markdown')

# ═══════════════════════════════════════════
#         🔘 Callbacks
# ═══════════════════════════════════════════
@bot.callback_query_handler(func=lambda c: True)
def callback_handler(call):
    uid  = call.from_user.id
    data = call.data
    cid  = call.message.chat.id
    mid  = call.message.message_id

    def edit(text, markup=None):
        try:
            bot.edit_message_text(text, cid, mid, parse_mode='Markdown', reply_markup=markup)
        except: pass

    def back_btn(cb='back_main'):
        m = InlineKeyboardMarkup()
        m.add(InlineKeyboardButton('🔙 برگشت', callback_data=cb))
        return m

    # ─── منوی اصلی ───
    if data == 'back_main':
        edit('🏠 *منوی اصلی SFOR*', main_menu())

    # ─── پروفایل ───
    elif data == 'my_profile':
        u = get_user(uid)
        mc = u['message_count'] if u else 0
        vip = '⭐ VIP' if u and u['is_vip'] else '👤 عادی'
        m = InlineKeyboardMarkup()
        m.add(InlineKeyboardButton('🗑️ پاک‌کردن تاریخچه AI', callback_data='clear_ai'))
        m.add(InlineKeyboardButton('🔙 برگشت', callback_data='back_main'))
        edit(f'👤 *پروفایل شما*\n\n📛 {call.from_user.first_name}\n🆔 `{uid}`\n💬 پیام‌ها: {mc}\n🏷️ {vip}', m)

    elif data == 'clear_ai':
        clear_ai_history(uid)
        bot.answer_callback_query(call.id, '✅ تاریخچه AI پاک شد!')

    # ─── AI ───
    elif data == 'ai_chat':
        edit('🤖 *هوش مصنوعی SFOR*\n\nپیامت رو مستقیم بفرست یا:\n`/ai سوالت`\n\nتاریخچه مکالمه ذخیره میشه.', back_btn())

    # ─── کانفیگ ───
    elif data == 'get_config':
        if user_has_config(uid) and uid != ADMIN_ID:
            bot.answer_callback_query(call.id, '⚠️ قبلاً کانفیگ دریافت کردی!', show_alert=True); return
        cfg = get_free_config()
        if not cfg:
            bot.answer_callback_query(call.id, '⏳ کانفیگ موجود نیست!', show_alert=True); return
        m = InlineKeyboardMarkup()
        m.add(InlineKeyboardButton('📲 آموزش', url=f'{SITE_URL}/vpn'))
        m.add(InlineKeyboardButton('🔙 برگشت', callback_data='back_main'))
        edit(f'🔒 *کانفیگ رایگان SFOR*\n\n📛 `{cfg["name"]}`\n\n🔗\n`{cfg["link"]}`\n\n📌 V2RayNG (اندروید) یا V2Box (iOS)', m)
        if uid != ADMIN_ID:
            mark_config_used(cfg['id'], uid)

    # ─── VPN ───
    elif data == 'get_vpn':
        if user_has_vpn(uid) and uid != ADMIN_ID:
            bot.answer_callback_query(call.id, '⚠️ قبلاً VPN دریافت کردی!', show_alert=True); return
        vpn = get_free_vpn()
        if not vpn:
            bot.answer_callback_query(call.id, '⏳ VPN موجود نیست! از /config استفاده کن.', show_alert=True); return
        try:
            bot.send_document(uid, vpn['file_id'], caption=f'🔒 {vpn["name"]}')
            if uid != ADMIN_ID:
                mark_vpn_used(vpn['id'], uid)
            bot.answer_callback_query(call.id, '✅ VPN ارسال شد!')
        except Exception as e:
            bot.answer_callback_query(call.id, f'❌ خطا: {str(e)[:50]}', show_alert=True)

    # ─── ناشناس ───
    elif data == 'anon':
        edit('📨 *پیام ناشناس*\n\n`/anon پیامت`\n\nپیامت بدون هویت به ادمین میرسه.', back_btn())

    # ─── معرفی ───
    elif data == 'share':
        me = bot.get_me()
        edit(f'📣 *معرفی SFOR*\n\n🔗 `t.me/{me.username}`\n\nربات رو به دوستات معرفی کن! 🙏', back_btn())

    # ─── درباره ───
    elif data == 'about':
        m = InlineKeyboardMarkup()
        m.add(InlineKeyboardButton('🌐 سایت', url=SITE_URL))
        m.add(InlineKeyboardButton('🔙 برگشت', callback_data='back_main'))
        edit(f'ℹ️ *درباره SFOR*\n\n🔥 نسخه: `{BOT_VERSION}`\n🌐 {SITE_URL}\n📸 @mmadsfor\n\n🛡️ امنیت | هک | فناوری', m)

    # ─── قوانین گروه (از دکمه خوش‌آمد) ───
    elif data.startswith('show_rules_'):
        gid = int(data.split('_')[-1])
        g = get_group(gid)
        rules = g['rules'] if g and g['rules'] else 'قوانینی تنظیم نشده.'
        bot.answer_callback_query(call.id, rules[:200], show_alert=True)

    # ═══ پنل ادمین ═══
    elif data == 'adm_stats':
        if uid != ADMIN_ID:
            bot.answer_callback_query(call.id, '⛔'); return
        stats = get_stats()
        bot.answer_callback_query(call.id,
            f'👥 کاربران: {stats["users"]}\n'
            f'🏘️ گروه‌ها: {stats["groups"]}\n'
            f'🔒 کانفیگ: {stats["configs"]}\n'
            f'📁 VPN: {stats["vpns"]}\n'
            f'💬 پاسخ‌خودکار: {stats["replies"]}',
            show_alert=True)

    elif data == 'adm_users':
        if uid != ADMIN_ID:
            bot.answer_callback_query(call.id, '⛔'); return
        conn = db()
        c = conn.cursor()
        c.execute('SELECT id,first_name,username,message_count FROM users ORDER BY message_count DESC LIMIT 10')
        rows = c.fetchall()
        conn.close()
        text = '👥 *کاربران فعال:*\n\n'
        for r in rows:
            text += f'• {r[1]} (`{r[0]}`) — {r[3]} پیام\n'
        edit(text, back_btn('adm_groups'))

    elif data == 'adm_groups':
        if uid != ADMIN_ID:
            bot.answer_callback_query(call.id, '⛔'); return
        conn = db()
        c = conn.cursor()
        c.execute('SELECT id,title FROM groups')
        rows = c.fetchall()
        conn.close()
        m = InlineKeyboardMarkup()
        for r in rows:
            m.add(InlineKeyboardButton(f'⚙️ {r[1]}', callback_data=f'grp_open_{r[0]}'))
        m.add(InlineKeyboardButton('🔙 برگشت', callback_data='back_main'))
        edit('🏘️ *گروه‌های ثبت‌شده:*', m)

    elif data.startswith('grp_open_'):
        if uid != ADMIN_ID:
            bot.answer_callback_query(call.id, '⛔'); return
        gid = int(data.split('_')[-1])
        g = get_group(gid)
        edit(f'⚙️ *تنظیمات {g["title"] if g else gid}*', group_settings_menu(gid))

    elif data == 'adm_logs':
        if uid != ADMIN_ID:
            bot.answer_callback_query(call.id, '⛔'); return
        logs = get_logs(10)
        text = '📋 *لاگ‌های اخیر:*\n\n'
        for log in logs:
            text += f'• `{log["event_type"]}` — {str(log["detail"] or "")[:20]}\n'
        edit(text, back_btn('back_main'))

    elif data == 'adm_autoreplies':
        if uid != ADMIN_ID:
            bot.answer_callback_query(call.id, '⛔'); return
        replies = get_auto_replies()
        text = f'💬 *پاسخ خودکار ({len(replies)} عدد):*\n\n'
        for kw, resp, _ in replies[:15]:
            text += f'• `{kw}` ← {str(resp or "")[:30]}\n'
        m = InlineKeyboardMarkup()
        m.add(InlineKeyboardButton('➕ افزودن', callback_data='adm_addreply'))
        m.add(InlineKeyboardButton('🔙 برگشت', callback_data='back_main'))
        edit(text, m)

    elif data == 'adm_addreply':
        if uid != ADMIN_ID:
            bot.answer_callback_query(call.id, '⛔'); return
        bot.answer_callback_query(call.id)
        bot.send_message(uid, 'دستور:\n`/addreply کلمه | پاسخ`', parse_mode='Markdown')

    elif data == 'adm_addconfig':
        if uid != ADMIN_ID:
            bot.answer_callback_query(call.id, '⛔'); return
        bot.answer_callback_query(call.id)
        bot.send_message(uid, '`/addconfig نام لینک`', parse_mode='Markdown')

    elif data == 'adm_addvpn':
        if uid != ADMIN_ID:
            bot.answer_callback_query(call.id, '⛔'); return
        bot.answer_callback_query(call.id)
        pending_vpn_upload[uid] = True
        bot.send_message(uid, '📁 فایل VPN رو بفرست:')

    elif data == 'adm_broadcast':
        if uid != ADMIN_ID:
            bot.answer_callback_query(call.id, '⛔'); return
        bot.answer_callback_query(call.id)
        bot.send_message(uid, '`/broadcast متن پیام`', parse_mode='Markdown')

    elif data == 'adm_settings':
        if uid != ADMIN_ID:
            bot.answer_callback_query(call.id, '⛔'); return
        m = InlineKeyboardMarkup()
        m.add(InlineKeyboardButton('🔄 ری‌استارت', callback_data='adm_restart'))
        m.add(InlineKeyboardButton('🗑️ پاک کردن لاگ‌ها', callback_data='adm_clearlogs'))
        m.add(InlineKeyboardButton('📊 آمار DB', callback_data='adm_dbstats'))
        m.add(InlineKeyboardButton('🔙 برگشت', callback_data='back_main'))
        edit('⚙️ *تنظیمات ربات*', m)

    elif data == 'adm_restart':
        if uid != ADMIN_ID:
            bot.answer_callback_query(call.id, '⛔'); return
        bot.answer_callback_query(call.id, '🔄 ری‌استارت...', show_alert=True)
        time.sleep(1)
        os.execv(__file__, ['python'] + [__file__])

    elif data == 'adm_clearlogs':
        if uid != ADMIN_ID:
            bot.answer_callback_query(call.id, '⛔'); return
        conn = db()
        c = conn.cursor()
        c.execute('DELETE FROM logs')
        conn.commit()
        conn.close()
        bot.answer_callback_query(call.id, '✅ لاگ‌ها پاک شدند!')

    elif data == 'adm_dbstats':
        if uid != ADMIN_ID:
            bot.answer_callback_query(call.id, '⛔'); return
        stats = get_stats()
        bot.answer_callback_query(call.id,
            f'DB Stats:\n'
            f'Users: {stats["users"]}\n'
            f'Groups: {stats["groups"]}\n'
            f'Configs: {stats["configs"]}\n'
            f'VPNs: {stats["vpns"]}\n'
            f'Logs: {stats["logs"]}',
            show_alert=True)

    # ═══ تنظیمات گروه ═══
    elif data.startswith('grp_'):
        parts = data.split('_')
        action = '_'.join(parts[1:-1])
        try:
            gid = int(parts[-1])
        except:
            bot.answer_callback_query(call.id); return

        # فقط ادمین گروه یا ادمین اصلی
        if uid != ADMIN_ID and not is_group_admin(gid, uid):
            bot.answer_callback_query(call.id, '⛔ فقط ادمین‌ها.', show_alert=True); return

        g = get_group(gid)
        if not g:
            bot.answer_callback_query(call.id, '❌ گروه پیدا نشد.'); return

        toggles = {
            'antilink': 'anti_link',
            'antispam': 'anti_spam',
            'antiprofanity': 'anti_profanity',
            'welcome': 'welcome',
            'goodbye': 'goodbye',
            'ai': 'ai_reply',
        }
        if action in toggles:
            field = toggles[action]
            new_val = 0 if g[field] else 1
            update_group(gid, field, new_val)
            status = '✅ فعال' if new_val else '❌ غیرفعال'
            bot.answer_callback_query(call.id, f'{field}: {status}')
            try:
                bot.edit_message_reply_markup(cid, mid, reply_markup=group_settings_menu(gid))
            except: pass

        elif action == 'warnlimit':
            g2 = get_group(gid)
            cur = g2['warn_limit']
            new = (cur % 5) + 1
            update_group(gid, 'warn_limit', new)
            bot.answer_callback_query(call.id, f'⚠️ حد اخطار: {new}')
            try:
                bot.edit_message_reply_markup(cid, mid, reply_markup=group_settings_menu(gid))
            except: pass

        elif action == 'rules':
            rules = g['rules'] or 'قوانینی تنظیم نشده.'
            bot.answer_callback_query(call.id, rules[:200], show_alert=True)

        elif action == 'setwelcome':
            bot.answer_callback_query(call.id)
            bot.send_message(uid, f'متن خوش‌آمد رو بفرست:\n(از {{name}} برای نام کاربر استفاده کن)\n\n`/setwelcome_{gid} متن`', parse_mode='Markdown')

        else:
            bot.answer_callback_query(call.id)

    else:
        bot.answer_callback_query(call.id)

# ─── دستور addreply ───
@bot.message_handler(commands=['addreply'])
def addreply_cmd(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, '⛔'); return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2 or '|' not in parts[1]:
        bot.reply_to(message, '`/addreply کلمه | پاسخ`', parse_mode='Markdown'); return
    kw, resp = parts[1].split('|', 1)
    conn = db()
    c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO auto_replies (keyword,response,match_type) VALUES (?,?,?)',
              (kw.strip(), resp.strip(), 'contains'))
    conn.commit()
    conn.close()
    bot.reply_to(message, f'✅ پاسخ خودکار برای *{kw.strip()}* اضافه شد.', parse_mode='Markdown')

# ─── setwelcome پویا ───
@bot.message_handler(func=lambda m: m.text and m.text.startswith('/setwelcome_'))
def setwelcome_dynamic(message):
    if message.from_user.id != ADMIN_ID: return
    parts = message.text.split(maxsplit=1)
    gid_str = parts[0].replace('/setwelcome_', '')
    try:
        gid = int(gid_str)
    except:
        return
    if len(parts) < 2:
        bot.reply_to(message, 'متن رو بنویس.'); return
    update_group(gid, 'welcome_msg', parts[1])
    bot.reply_to(message, '✅ متن خوش‌آمد تنظیم شد.')

# ═══════════════════════════════════════════
#              🚀 اجرا
# ═══════════════════════════════════════════
if __name__ == '__main__':
    sys.stdout.flush()
    print('[SFOR] Bot starting...', flush=True)
    print(f'[SFOR] Token prefix: {TOKEN[:15]}...', flush=True)
    print('[SFOR] Waiting 5s for Flask health check...', flush=True)
    time.sleep(5)
    print('[SFOR] Removing webhook...', flush=True)
    try:
        bot.remove_webhook()
        print('[SFOR] Webhook removed OK', flush=True)
    except Exception as e:
        print(f'[SFOR] Webhook error (continuing): {e}', flush=True)
    time.sleep(2)
    print('[SFOR] Starting polling...', flush=True)
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=60,
                                 skip_pending=True, restart_on_change=False)
        except Exception as e:
            print(f'[SFOR ERROR] {e}', flush=True)
            time.sleep(10)
