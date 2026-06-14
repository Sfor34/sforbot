import sqlite3
from datetime import datetime

DB_FILE = 'sfor_bot.db'

# ═══════════════════════════════════════════
#              🗄️ اتصال به دیتابیس
# ═══════════════════════════════════════════
def db():
    return sqlite3.connect(DB_FILE)

# ═══════════════════════════════════════════
#              🏗️ ساخت جداول
# ═══════════════════════════════════════════
def init_db():
    conn = db()
    c = conn.cursor()

    # کاربران
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        joined_at TEXT,
        is_banned INTEGER DEFAULT 0,
        message_count INTEGER DEFAULT 0,
        is_vip INTEGER DEFAULT 0
    )''')

    # گروه‌ها
    c.execute('''CREATE TABLE IF NOT EXISTS groups (
        id INTEGER PRIMARY KEY,
        title TEXT,
        joined_at TEXT,
        anti_link INTEGER DEFAULT 1,
        anti_spam INTEGER DEFAULT 1,
        welcome INTEGER DEFAULT 1,
        goodbye INTEGER DEFAULT 0,
        ai_reply INTEGER DEFAULT 0,
        warn_limit INTEGER DEFAULT 3,
        rules TEXT DEFAULT '',
        welcome_msg TEXT DEFAULT 'خوش اومدی {name}! 👋',
        goodbye_msg TEXT DEFAULT '{name} گروه رو ترک کرد 👋',
        filter_words TEXT DEFAULT ''
    )''')

    # اخطارها
    c.execute('''CREATE TABLE IF NOT EXISTS warns (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        group_id INTEGER,
        reason TEXT,
        warned_at TEXT
    )''')

    # پاسخ خودکار
    c.execute('''CREATE TABLE IF NOT EXISTS auto_replies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        keyword TEXT,
        response TEXT,
        match_type TEXT DEFAULT 'contains'
    )''')

    # لاگ رویدادها
    c.execute('''CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_type TEXT,
        user_id INTEGER,
        group_id INTEGER,
        detail TEXT,
        created_at TEXT
    )''')

    # ردیابی اسپم
    c.execute('''CREATE TABLE IF NOT EXISTS spam_track (
        user_id INTEGER,
        group_id INTEGER,
        message_count INTEGER DEFAULT 0,
        last_message TEXT,
        PRIMARY KEY (user_id, group_id)
    )''')

    # کانفیگ‌های V2Ray
    c.execute('''CREATE TABLE IF NOT EXISTS configs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        link TEXT,
        is_used INTEGER DEFAULT 0,
        used_by INTEGER DEFAULT NULL,
        created_at TEXT
    )''')

    # اکانت‌های VPN
    c.execute('''CREATE TABLE IF NOT EXISTS vpn_accounts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        service TEXT,
        username TEXT,
        password TEXT,
        is_used INTEGER DEFAULT 0,
        used_by INTEGER DEFAULT NULL,
        created_at TEXT
    )''')

    # یادداشت‌ها
    c.execute('''CREATE TABLE IF NOT EXISTS notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        group_id INTEGER,
        name TEXT,
        content TEXT,
        created_at TEXT
    )''')

    # مکالمه AI
    c.execute('''CREATE TABLE IF NOT EXISTS ai_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        role TEXT,
        content TEXT,
        created_at TEXT
    )''')

    conn.commit()
    conn.close()

# ═══════════════════════════════════════════
#              👤 توابع کاربران
# ═══════════════════════════════════════════
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

def get_user(user_id):
    conn = db()
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE id=?', (user_id,))
    row = c.fetchone()
    conn.close()
    return row

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

def is_banned(user_id):
    conn = db()
    c = conn.cursor()
    c.execute('SELECT is_banned FROM users WHERE id=?', (user_id,))
    row = c.fetchone()
    conn.close()
    return row and row[0] == 1

def get_all_users():
    conn = db()
    c = conn.cursor()
    c.execute('SELECT id FROM users WHERE is_banned=0')
    rows = c.fetchall()
    conn.close()
    return [r[0] for r in rows]

def get_user_count():
    conn = db()
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM users')
    count = c.fetchone()[0]
    conn.close()
    return count

def set_vip(user_id, status=1):
    conn = db()
    c = conn.cursor()
    c.execute('UPDATE users SET is_vip=? WHERE id=?', (status, user_id))
    conn.commit()
    conn.close()

# ═══════════════════════════════════════════
#              🏘️ توابع گروه‌ها
# ═══════════════════════════════════════════
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

def get_group_count():
    conn = db()
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM groups')
    count = c.fetchone()[0]
    conn.close()
    return count

def update_group(group_id, field, value):
    conn = db()
    c = conn.cursor()
    c.execute(f'UPDATE groups SET {field}=? WHERE id=?', (value, group_id))
    conn.commit()
    conn.close()

# ═══════════════════════════════════════════
#              ⚠️ توابع اخطار
# ═══════════════════════════════════════════
def add_warn(user_id, group_id, reason):
    conn = db()
    c = conn.cursor()
    c.execute('''INSERT INTO warns (user_id, group_id, reason, warned_at)
                 VALUES (?, ?, ?, ?)''',
              (user_id, group_id, reason, datetime.now().isoformat()))
    conn.commit()
    conn.close()

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

def remove_warn(user_id, group_id):
    conn = db()
    c = conn.cursor()
    c.execute('''DELETE FROM warns WHERE id=(
        SELECT id FROM warns WHERE user_id=? AND group_id=? ORDER BY warned_at DESC LIMIT 1
    )''', (user_id, group_id))
    conn.commit()
    conn.close()

# ═══════════════════════════════════════════
#              🚫 ردیابی اسپم
# ═══════════════════════════════════════════
def track_spam(user_id, group_id):
    conn = db()
    c = conn.cursor()
    now = datetime.now().isoformat()
    c.execute('''INSERT INTO spam_track (user_id, group_id, message_count, last_message)
                 VALUES (?, ?, 1, ?)
                 ON CONFLICT(user_id, group_id) DO UPDATE SET
                 message_count=message_count+1, last_message=?''',
              (user_id, group_id, now, now))
    c.execute('SELECT message_count FROM spam_track WHERE user_id=? AND group_id=?', (user_id, group_id))
    count = c.fetchone()[0]
    conn.commit()
    conn.close()
    return count

def reset_spam(user_id, group_id):
    conn = db()
    c = conn.cursor()
    c.execute('UPDATE spam_track SET message_count=0 WHERE user_id=? AND group_id=?', (user_id, group_id))
    conn.commit()
    conn.close()

# ═══════════════════════════════════════════
#              📝 پاسخ خودکار
# ═══════════════════════════════════════════
def add_auto_reply(keyword, response, match_type='contains'):
    conn = db()
    c = conn.cursor()
    c.execute('INSERT INTO auto_replies (keyword, response, match_type) VALUES (?, ?, ?)',
              (keyword, response, match_type))
    conn.commit()
    conn.close()

def get_auto_replies():
    conn = db()
    c = conn.cursor()
    c.execute('SELECT keyword, response, match_type FROM auto_replies')
    rows = c.fetchall()
    conn.close()
    return rows

def delete_auto_reply(keyword):
    conn = db()
    c = conn.cursor()
    c.execute('DELETE FROM auto_replies WHERE keyword=?', (keyword,))
    conn.commit()
    conn.close()

# ═══════════════════════════════════════════
#              📋 لاگ
# ═══════════════════════════════════════════
def add_log(event_type, user_id=None, group_id=None, detail=None):
    conn = db()
    c = conn.cursor()
    c.execute('''INSERT INTO logs (event_type, user_id, group_id, detail, created_at)
                 VALUES (?, ?, ?, ?, ?)''',
              (event_type, user_id, group_id, detail, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_logs(limit=20):
    conn = db()
    c = conn.cursor()
    c.execute('SELECT * FROM logs ORDER BY created_at DESC LIMIT ?', (limit,))
    rows = c.fetchall()
    conn.close()
    return rows

# ═══════════════════════════════════════════
#              🔒 کانفیگ V2Ray
# ═══════════════════════════════════════════
def add_config(name, link):
    conn = db()
    c = conn.cursor()
    c.execute('INSERT INTO configs (name, link, created_at) VALUES (?, ?, ?)',
              (name, link, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_free_config():
    conn = db()
    c = conn.cursor()
    c.execute('SELECT id, name, link FROM configs WHERE is_used=0 LIMIT 1')
    row = c.fetchone()
    conn.close()
    return row

def mark_config_used(config_id, user_id):
    conn = db()
    c = conn.cursor()
    c.execute('UPDATE configs SET is_used=1, used_by=? WHERE id=?', (user_id, config_id))
    conn.commit()
    conn.close()

def user_has_config(user_id):
    conn = db()
    c = conn.cursor()
    c.execute('SELECT id FROM configs WHERE used_by=?', (user_id,))
    row = c.fetchone()
    conn.close()
    return row is not None

def get_config_count():
    conn = db()
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM configs WHERE is_used=0')
    count = c.fetchone()[0]
    conn.close()
    return count

# ═══════════════════════════════════════════
#              🌐 اکانت VPN
# ═══════════════════════════════════════════
def add_vpn(service, username, password):
    conn = db()
    c = conn.cursor()
    c.execute('INSERT INTO vpn_accounts (service, username, password, created_at) VALUES (?, ?, ?, ?)',
              (service, username, password, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_free_vpn():
    conn = db()
    c = conn.cursor()
    c.execute('SELECT id, service, username, password FROM vpn_accounts WHERE is_used=0 LIMIT 1')
    row = c.fetchone()
    conn.close()
    return row

def mark_vpn_used(vpn_id, user_id):
    conn = db()
    c = conn.cursor()
    c.execute('UPDATE vpn_accounts SET is_used=1, used_by=? WHERE id=?', (user_id, vpn_id))
    conn.commit()
    conn.close()

def user_has_vpn(user_id):
    conn = db()
    c = conn.cursor()
    c.execute('SELECT id FROM vpn_accounts WHERE used_by=?', (user_id,))
    row = c.fetchone()
    conn.close()
    return row is not None

def get_vpn_count():
    conn = db()
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM vpn_accounts WHERE is_used=0')
    count = c.fetchone()[0]
    conn.close()
    return count

# ═══════════════════════════════════════════
#              📝 یادداشت‌ها
# ═══════════════════════════════════════════
def save_note(user_id, group_id, name, content):
    conn = db()
    c = conn.cursor()
    c.execute('''INSERT OR REPLACE INTO notes (user_id, group_id, name, content, created_at)
                 VALUES (?, ?, ?, ?, ?)''',
              (user_id, group_id, name, content, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_note(group_id, name):
    conn = db()
    c = conn.cursor()
    c.execute('SELECT content FROM notes WHERE group_id=? AND name=?', (group_id, name))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

def delete_note(group_id, name):
    conn = db()
    c = conn.cursor()
    c.execute('DELETE FROM notes WHERE group_id=? AND name=?', (group_id, name))
    conn.commit()
    conn.close()

# ═══════════════════════════════════════════
#              🤖 تاریخچه AI
# ═══════════════════════════════════════════
def add_ai_history(user_id, role, content):
    conn = db()
    c = conn.cursor()
    c.execute('''INSERT INTO ai_history (user_id, role, content, created_at)
                 VALUES (?, ?, ?, ?)''',
              (user_id, role, content, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_ai_history(user_id, limit=10):
    conn = db()
    c = conn.cursor()
    c.execute('''SELECT role, content FROM ai_history
                 WHERE user_id=? ORDER BY created_at DESC LIMIT ?''',
              (user_id, limit))
    rows = c.fetchall()
    conn.close()
    return list(reversed(rows))

def clear_ai_history(user_id):
    conn = db()
    c = conn.cursor()
    c.execute('DELETE FROM ai_history WHERE user_id=?', (user_id,))
    conn.commit()
    conn.close()

# ═══════════════════════════════════════════
#              📊 آمار کلی
# ═══════════════════════════════════════════
def get_stats():
    conn = db()
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM users')
    users = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM groups')
    groups = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM configs WHERE is_used=0')
    configs = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM vpn_accounts WHERE is_used=0')
    vpns = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM logs')
    logs = c.fetchone()[0]
    conn.close()
    return {
        'users': users,
        'groups': groups,
        'configs': configs,
        'vpns': vpns,
        'logs': logs
    }

# اجرای اولیه
init_db()
