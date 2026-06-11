import telebot, os, sys, time, sqlite3, importlib.util, glob
from threading import Thread
from flask import Flask

flask_app = Flask(__name__)

@flask_app.route('/')
def home(): return '🔥 SFOR Bot v4.0'

@flask_app.route('/health')
def health(): return 'OK', 200

Thread(target=lambda: flask_app.run(
    host='0.0.0.0', port=int(os.environ.get('PORT', 8080)), debug=False
), daemon=True).start()

TOKEN     = os.environ.get('TOKEN', '8576320592:AAEq0o4Zz97ZzBS3dkqGCEMAG8QfdOjhoK4')
ADMIN_ID  = int(os.environ.get('ADMIN_ID', '7533340777'))
SITE_URL  = 'https://sfor.onrender.com'
DB_FILE   = 'sfor_bot.db'
BOT_VERSION = '4.0.0'

bot = telebot.TeleBot(TOKEN, parse_mode=None)

def db():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = db()
    conn.cursor().executescript('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY, username TEXT, first_name TEXT,
        joined_at TEXT, is_banned INTEGER DEFAULT 0,
        message_count INTEGER DEFAULT 0, is_vip INTEGER DEFAULT 0, last_seen TEXT
    );
    CREATE TABLE IF NOT EXISTS groups (
        id INTEGER PRIMARY KEY, title TEXT, joined_at TEXT,
        anti_link INTEGER DEFAULT 1, anti_spam INTEGER DEFAULT 1,
        anti_profanity INTEGER DEFAULT 1, welcome INTEGER DEFAULT 1,
        goodbye INTEGER DEFAULT 0, ai_reply INTEGER DEFAULT 0,
        warn_limit INTEGER DEFAULT 3, rules TEXT DEFAULT "",
        welcome_msg TEXT DEFAULT "", goodbye_msg TEXT DEFAULT "",
        filter_words TEXT DEFAULT "",
        anti_porn INTEGER DEFAULT 0,
        anti_bot INTEGER DEFAULT 0,
        auto_clean INTEGER DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS warns (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, group_id INTEGER, reason TEXT, warned_at TEXT
    );
    CREATE TABLE IF NOT EXISTS auto_replies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        keyword TEXT UNIQUE, response TEXT, match_type TEXT DEFAULT "contains"
    );
    CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_type TEXT, user_id INTEGER, group_id INTEGER, detail TEXT, created_at TEXT
    );
    CREATE TABLE IF NOT EXISTS spam_track (
        user_id INTEGER, group_id INTEGER,
        count INTEGER DEFAULT 0, last_time TEXT,
        PRIMARY KEY (user_id, group_id)
    );
    CREATE TABLE IF NOT EXISTS configs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, link TEXT, is_used INTEGER DEFAULT 0,
        used_by INTEGER, created_at TEXT
    );
    CREATE TABLE IF NOT EXISTS vpn_files (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, file_id TEXT, is_used INTEGER DEFAULT 0,
        used_by INTEGER, created_at TEXT
    );
    CREATE TABLE IF NOT EXISTS ai_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, role TEXT, content TEXT, created_at TEXT
    );
    CREATE TABLE IF NOT EXISTS notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, group_id INTEGER,
        name TEXT, content TEXT, created_at TEXT
    );
    CREATE TABLE IF NOT EXISTS user_configs (user_id INTEGER PRIMARY KEY, given_at TEXT);
    CREATE TABLE IF NOT EXISTS user_vpns (user_id INTEGER PRIMARY KEY, given_at TEXT);
    ''')
    conn.commit()
    conn.close()

init_db()

def load_modules():
    modules_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'modules')
    os.makedirs(modules_dir, exist_ok=True)
    files = sorted(glob.glob(os.path.join(modules_dir, '*.py')))
    for f in files:
        name = os.path.splitext(os.path.basename(f))[0]
        if name.startswith('_'): continue
        try:
            spec = importlib.util.spec_from_file_location(name, f)
            mod = importlib.util.module_from_spec(spec)
            mod.bot      = bot
            mod.ADMIN_ID = ADMIN_ID
            mod.SITE_URL = SITE_URL
            mod.DB_FILE  = DB_FILE
            mod.db       = db
            spec.loader.exec_module(mod)
            print(f'[SFOR] ✅ {name}', flush=True)
        except Exception as e:
            print(f'[SFOR] ❌ {name}: {e}', flush=True)

load_modules()

if __name__ == '__main__':
    print(f'[SFOR] v{BOT_VERSION} starting...', flush=True)
    time.sleep(5)
    try: bot.remove_webhook()
    except: pass
    time.sleep(2)
    print('[SFOR] Polling...', flush=True)
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=60, skip_pending=True)
        except Exception as e:
            print(f'[SFOR ERROR] {e}', flush=True)
            time.sleep(10)
