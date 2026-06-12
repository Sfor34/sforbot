# ═══════════════════════════════════════════
#     🔥 SFOR Features Module v2.0
#     فایل: modules/sfor_features.py
#     قرار بده توی پوشه modules/
# ═══════════════════════════════════════════
import time, re, requests, random, sqlite3
from datetime import datetime, timedelta
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ChatPermissions

# متغیرها از bot.py inject میشن
bot = None
ADMIN_ID = None
SITE_URL = None
db = None
add_user = None
add_group = None
get_group = None
update_group = None
is_group_admin = None
safe_delete = None
safe_send = None
add_log = None
add_warn = None
get_warns = None
clear_warns = None
ban_user = None
mute_user = None
ask_gemini = None

def setup(bot_instance, ctx):
    global bot, ADMIN_ID, SITE_URL, db, add_user, add_group, get_group
    global update_group, is_group_admin, safe_delete, safe_send, add_log
    global add_warn, get_warns, clear_warns, ban_user, mute_user, ask_gemini
    bot = bot_instance
    ADMIN_ID  = ctx['ADMIN_ID']
    SITE_URL  = ctx['SITE_URL']
    db        = ctx['db']
    add_user  = ctx['add_user']
    add_group = ctx['add_group']
    get_group = ctx['get_group']
    update_group   = ctx['update_group']
    is_group_admin = ctx['is_group_admin']
    safe_delete    = ctx['safe_delete']
    safe_send      = ctx['safe_send']
    add_log        = ctx['add_log']
    add_warn       = ctx['add_warn']
    get_warns      = ctx['get_warns']
    clear_warns    = ctx['clear_warns']
    ban_user       = ctx['ban_user']
    mute_user      = ctx['mute_user']
    ask_gemini     = ctx['ask_gemini']
    init_features_db()
    register_handlers()
    print('[SFOR] ✅ sfor_features module loaded!', flush=True)

# ═══════════════════════════════════════════
#         🗄️ دیتابیس
# ═══════════════════════════════════════════
def init_features_db():
    conn = db()
    c = conn.cursor()
    c.executescript('''
    CREATE TABLE IF NOT EXISTS user_scores (
        user_id INTEGER,
        group_id INTEGER,
        score INTEGER DEFAULT 0,
        PRIMARY KEY (user_id, group_id)
    );
    CREATE TABLE IF NOT EXISTS reminders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        chat_id INTEGER,
        text TEXT,
        remind_at TEXT,
        done INTEGER DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS scheduled_msgs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id INTEGER,
        text TEXT,
        send_at TEXT,
        done INTEGER DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS captcha_pending (
        user_id INTEGER,
        group_id INTEGER,
        answer INTEGER,
        expires_at TEXT,
        msg_id INTEGER,
        PRIMARY KEY (user_id, group_id)
    );
    CREATE TABLE IF NOT EXISTS games (
        chat_id INTEGER PRIMARY KEY,
        type TEXT,
        data TEXT,
        created_at TEXT
    );
    ''')
    conn.commit()
    conn.close()

# ═══════════════════════════════════════════
#         🌤️ آب‌وهوا
# ═══════════════════════════════════════════
def get_weather(city):
    try:
        url = f'https://wttr.in/{city}?format=j1&lang=fa'
        r = requests.get(url, timeout=10)
        data = r.json()
        current = data['current_condition'][0]
        temp = current['temp_C']
        feels = current['FeelsLikeC']
        humidity = current['humidity']
        desc = current['lang_fa'][0]['value'] if current.get('lang_fa') else current['weatherDesc'][0]['value']
        return (f'🌤️ *آب‌وهوای {city}*\n\n'
                f'🌡️ دما: {temp}°C\n'
                f'🤔 احساس: {feels}°C\n'
                f'💧 رطوبت: {humidity}%\n'
                f'📋 وضعیت: {desc}')
    except:
        return '❌ شهر پیدا نشد. مثال: `/weather Tehran`'

# ═══════════════════════════════════════════
#         💰 نرخ ارز و کریپتو
# ═══════════════════════════════════════════
def get_prices():
    try:
        # کریپتو از CoinGecko
        r = requests.get(
            'https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,tether,tron&vs_currencies=usd',
            timeout=10)
        crypto = r.json()
        btc = crypto.get('bitcoin', {}).get('usd', '?')
        eth = crypto.get('ethereum', {}).get('usd', '?')
        usdt = crypto.get('tether', {}).get('usd', '?')

        text = ('💰 *قیمت لحظه‌ای*\n\n'
                f'₿ بیت‌کوین: `${btc:,}`\n'
                f'Ξ اتریوم: `${eth:,}`\n'
                f'₮ تتر: `${usdt}`\n\n'
                f'⏰ {datetime.now().strftime("%H:%M:%S")}')
        return text
    except:
        return '❌ خطا در دریافت قیمت‌ها.'

# ═══════════════════════════════════════════
#         🔗 کوتاه‌کننده لینک
# ═══════════════════════════════════════════
def shorten_url(url):
    try:
        r = requests.get(f'https://tinyurl.com/api-create.php?url={url}', timeout=10)
        if r.status_code == 200:
            return r.text.strip()
        return None
    except:
        return None

# ═══════════════════════════════════════════
#         🌐 اطلاعات IP
# ═══════════════════════════════════════════
def get_ip_info(ip):
    try:
        r = requests.get(f'https://ipapi.co/{ip}/json/', timeout=10)
        data = r.json()
        if 'error' in data:
            return '❌ IP نامعتبر است.'
        return (f'🌐 *اطلاعات IP*\n\n'
                f'📍 IP: `{data.get("ip","?")}`\n'
                f'🌍 کشور: {data.get("country_name","?")}\n'
                f'🏙️ شهر: {data.get("city","?")}\n'
                f'📡 ISP: {data.get("org","?")}\n'
                f'🕐 تایم‌زون: {data.get("timezone","?")}')
    except:
        return '❌ خطا در دریافت اطلاعات IP.'

# ═══════════════════════════════════════════
#         🕐 ساعت ایران
# ═══════════════════════════════════════════
def get_iran_time():
    try:
        r = requests.get('https://timeapi.io/api/Time/current/zone?timeZone=Asia/Tehran', timeout=5)
        data = r.json()
        return f'🕐 *ساعت ایران:* `{data["time"]}`\n📅 *تاریخ:* `{data["date"]}`'
    except:
        from datetime import timezone
        now = datetime.now()
        return f'🕐 *ساعت سرور:* `{now.strftime("%H:%M:%S")}`'

# ═══════════════════════════════════════════
#         🎮 بازی حدس عدد
# ═══════════════════════════════════════════
active_games = {}

def start_number_game(cid):
    number = random.randint(1, 100)
    active_games[cid] = {'type': 'number', 'answer': number, 'tries': 0}
    return f'🎮 *بازی حدس عدد شروع شد!*\n\nمن یه عدد بین ۱ تا ۱۰۰ فکر کردم.\nعدد مورد نظر رو حدس بزن! 🤔'

def check_number_game(cid, text):
    if cid not in active_games: return None
    game = active_games[cid]
    if game['type'] != 'number': return None
    try:
        guess = int(text)
    except:
        return None
    game['tries'] += 1
    if guess == game['answer']:
        del active_games[cid]
        return f'🎉 *آفرین! درسته!*\n\nعدد {guess} بود!\n✅ در {game["tries"]} تلاش پیدا کردی!'
    elif guess < game['answer']:
        return f'⬆️ بیشتر! (تلاش {game["tries"]})'
    else:
        return f'⬇️ کمتر! (تلاش {game["tries"]})'

# ═══════════════════════════════════════════
#         📊 امتیاز کاربران
# ═══════════════════════════════════════════
def add_score(uid, gid, points=1):
    conn = db()
    c = conn.cursor()
    c.execute('INSERT OR IGNORE INTO user_scores (user_id,group_id,score) VALUES (?,?,0)', (uid, gid))
    c.execute('UPDATE user_scores SET score=score+? WHERE user_id=? AND group_id=?', (points, uid, gid))
    conn.commit()
    conn.close()

def get_top_users(gid, limit=10):
    conn = db()
    c = conn.cursor()
    c.execute('SELECT user_id, score FROM user_scores WHERE group_id=? ORDER BY score DESC LIMIT ?', (gid, limit))
    rows = c.fetchall()
    conn.close()
    return rows

def get_user_score(uid, gid):
    conn = db()
    c = conn.cursor()
    c.execute('SELECT score FROM user_scores WHERE user_id=? AND group_id=?', (uid, gid))
    r = c.fetchone()
    conn.close()
    return r[0] if r else 0

# ═══════════════════════════════════════════
#         🔔 یادآور
# ═══════════════════════════════════════════
def add_reminder(uid, cid, text, minutes):
    remind_at = (datetime.now() + timedelta(minutes=minutes)).isoformat()
    conn = db()
    c = conn.cursor()
    c.execute('INSERT INTO reminders (user_id,chat_id,text,remind_at) VALUES (?,?,?,?)',
              (uid, cid, text, remind_at))
    conn.commit()
    conn.close()

def check_reminders():
    while True:
        try:
            conn = db()
            c = conn.cursor()
            now = datetime.now().isoformat()
            c.execute('SELECT id,user_id,chat_id,text FROM reminders WHERE remind_at<=? AND done=0', (now,))
            rows = c.fetchall()
            for row in rows:
                try:
                    bot.send_message(row[2], f'🔔 *یادآور:*\n\n{row[3]}',
                                     parse_mode='Markdown')
                    c.execute('UPDATE reminders SET done=1 WHERE id=?', (row[0],))
                except: pass
            conn.commit()
            conn.close()
        except: pass
        time.sleep(30)

# ═══════════════════════════════════════════
#         🛡️ کپچا
# ═══════════════════════════════════════════
def send_captcha(cid, uid, name):
    a = random.randint(1, 10)
    b = random.randint(1, 10)
    answer = a + b
    expires = (datetime.now() + timedelta(minutes=2)).isoformat()

    # میوت کاربر تا جواب بده
    try:
        bot.restrict_chat_member(cid, uid,
            permissions=ChatPermissions(can_send_messages=False))
    except: pass

    m = InlineKeyboardMarkup(row_width=3)
    options = [answer, answer+random.randint(1,5), answer-random.randint(1,5),
               answer+random.randint(6,10), answer-random.randint(6,10), random.randint(1,20)]
    options = list(set([max(1,o) for o in options]))[:6]
    random.shuffle(options)
    buttons = [InlineKeyboardButton(str(o), callback_data=f'captcha_{uid}_{o}') for o in options]
    m.add(*buttons)

    msg = bot.send_message(cid,
        f'👋 سلام *{name}*!\n\n'
        f'🔐 برای ورود به گروه، جواب بده:\n\n'
        f'*{a} + {b} = ?*\n\n'
        f'⏰ ۲ دقیقه وقت داری!',
        parse_mode='Markdown', reply_markup=m)

    conn = db()
    c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO captcha_pending (user_id,group_id,answer,expires_at,msg_id) VALUES (?,?,?,?,?)',
              (uid, cid, answer, expires, msg.message_id))
    conn.commit()
    conn.close()

# ═══════════════════════════════════════════
#         📊 رنکینگ
# ═══════════════════════════════════════════
def get_ranking_text(gid):
    rows = get_top_users(gid, 10)
    if not rows:
        return '📊 هنوز امتیازی ثبت نشده!'
    medals = ['🥇', '🥈', '🥉', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟']
    text = '🏆 *رنکینگ فعال‌ترین کاربران:*\n\n'
    for i, (uid, score) in enumerate(rows):
        try:
            u = bot.get_chat_member(gid, uid)
            name = u.user.first_name
        except:
            name = f'کاربر {uid}'
        text += f'{medals[i]} {name}: `{score}` امتیاز\n'
    return text

# ═══════════════════════════════════════════
#         📋 نقل‌قول تصادفی
# ═══════════════════════════════════════════
QUOTES = [
    '💡 "دانش قدرت است." — فرانسیس بیکن',
    '🔥 "موفقیت نهایی نیست، شکست کشنده نیست، شجاعت ادامه دادن است." — چرچیل',
    '🌟 "هر متخصصی روزی مبتدی بوده." — هلن هیز',
    '💪 "تنها راه انجام کار عالی، عشق به کار است." — استیو جابز',
    '🚀 "رویاهایت را بزرگ داشته باش، با کوچکترین قدم شروع کن."',
    '🎯 "هدف بدون برنامه فقط یک آرزوست." — آنتوان دو سنت اگزوپری',
    '🔐 "امنیت توهم نیست، یک فرآیند است." — بروس اشنایر',
    '💻 "کد خوب مثل شعر خوبه - ساده، زیبا، قابل فهم."',
    '🌐 "اینترنت آزادی اطلاعات است، از آن محافظت کن."',
    '🛡️ "بهترین هکرها، بهترین مدافعانند."',
]

# ═══════════════════════════════════════════
#         🔧 هندلرها
# ═══════════════════════════════════════════
def register_handlers():

    # ─── آب‌وهوا ───
    @bot.message_handler(commands=['weather', 'هوا'])
    def weather_cmd(message):
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            bot.reply_to(message, '🌤️ مثال: `/weather Tehran`', parse_mode='Markdown'); return
        msg = bot.reply_to(message, '⏳ در حال دریافت...')
        result = get_weather(parts[1])
        bot.edit_message_text(result, message.chat.id, msg.message_id, parse_mode='Markdown')

    # ─── قیمت ارز ───
    @bot.message_handler(commands=['price', 'قیمت', 'crypto'])
    def price_cmd(message):
        msg = bot.reply_to(message, '⏳ در حال دریافت قیمت‌ها...')
        result = get_prices()
        m = InlineKeyboardMarkup()
        m.add(InlineKeyboardButton('🔄 بروزرسانی', callback_data='refresh_price'))
        bot.edit_message_text(result, message.chat.id, msg.message_id,
                              parse_mode='Markdown', reply_markup=m)

    # ─── کوتاه‌کننده لینک ───
    @bot.message_handler(commands=['short', 'کوتاه'])
    def short_cmd(message):
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            bot.reply_to(message, '🔗 مثال: `/short https://example.com`', parse_mode='Markdown'); return
        url = parts[1].strip()
        if not url.startswith('http'):
            bot.reply_to(message, '❌ لینک باید با http شروع بشه.'); return
        result = shorten_url(url)
        if result:
            bot.reply_to(message, f'✅ لینک کوتاه:\n`{result}`', parse_mode='Markdown')
        else:
            bot.reply_to(message, '❌ خطا در کوتاه کردن لینک.')

    # ─── اطلاعات IP ───
    @bot.message_handler(commands=['ip'])
    def ip_cmd(message):
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            bot.reply_to(message, '🌐 مثال: `/ip 8.8.8.8`', parse_mode='Markdown'); return
        result = get_ip_info(parts[1].strip())
        bot.reply_to(message, result, parse_mode='Markdown')

    # ─── ساعت ایران ───
    @bot.message_handler(commands=['time', 'ساعت'])
    def time_cmd(message):
        result = get_iran_time()
        bot.reply_to(message, result, parse_mode='Markdown')

    # ─── نقل‌قول ───
    @bot.message_handler(commands=['quote', 'نقلقول', 'انگیزه'])
    def quote_cmd(message):
        bot.reply_to(message, random.choice(QUOTES), parse_mode='Markdown')

    # ─── بازی حدس عدد ───
    @bot.message_handler(commands=['game', 'بازی'])
    def game_cmd(message):
        result = start_number_game(message.chat.id)
        bot.reply_to(message, result, parse_mode='Markdown')

    # ─── رنکینگ ───
    @bot.message_handler(commands=['rank', 'رنک', 'رنکینگ'])
    def rank_cmd(message):
        if message.chat.type == 'private':
            bot.reply_to(message, '⚠️ این دستور فقط در گروه کار میکنه.'); return
        text = get_ranking_text(message.chat.id)
        bot.reply_to(message, text, parse_mode='Markdown')

    # ─── امتیاز من ───
    @bot.message_handler(commands=['score', 'امتیاز'])
    def score_cmd(message):
        if message.chat.type == 'private':
            bot.reply_to(message, '⚠️ این دستور فقط در گروه کار میکنه.'); return
        target = message.reply_to_message.from_user if message.reply_to_message else message.from_user
        score = get_user_score(target.id, message.chat.id)
        bot.reply_to(message,
            f'⭐ *امتیاز {target.first_name}:* `{score}` امتیاز',
            parse_mode='Markdown')

    # ─── یادآور ───
    @bot.message_handler(commands=['remind', 'یادآور'])
    def remind_cmd(message):
        parts = message.text.split(maxsplit=2)
        if len(parts) < 3 or not parts[1].isdigit():
            bot.reply_to(message, '🔔 مثال: `/remind 30 خرید کردن`\n(۳۰ دقیقه دیگه یادآوری میکنه)', parse_mode='Markdown'); return
        minutes = int(parts[1])
        text = parts[2]
        add_reminder(message.from_user.id, message.chat.id, text, minutes)
        bot.reply_to(message,
            f'✅ یادآور تنظیم شد!\n⏰ {minutes} دقیقه دیگه: *{text}*',
            parse_mode='Markdown')

    # ─── تایمر ───
    @bot.message_handler(commands=['timer', 'تایمر'])
    def timer_cmd(message):
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2 or not parts[1].isdigit():
            bot.reply_to(message, '⏱️ مثال: `/timer 60` (ثانیه)', parse_mode='Markdown'); return
        seconds = min(int(parts[1]), 3600)
        msg = bot.reply_to(message, f'⏱️ تایمر {seconds} ثانیه شروع شد...')
        import threading
        def finish():
            time.sleep(seconds)
            try:
                bot.edit_message_text(
                    f'⏰ *تایمر تموم شد!*\n⏱️ {seconds} ثانیه گذشت.',
                    message.chat.id, msg.message_id, parse_mode='Markdown')
                bot.send_message(message.chat.id,
                    f'🔔 {message.from_user.first_name} تایمرت تموم شد!',
                    parse_mode='Markdown')
            except: pass
        threading.Thread(target=finish, daemon=True).start()

    # ─── ترجمه ───
    @bot.message_handler(commands=['translate', 'ترجمه'])
    def translate_cmd(message):
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            bot.reply_to(message, '🌐 مثال: `/translate Hello World`', parse_mode='Markdown'); return
        text = parts[1]
        msg = bot.reply_to(message, '⏳ در حال ترجمه...')
        reply = ask_gemini(message.from_user.id,
            f'این متن رو به فارسی ترجمه کن، فقط ترجمه رو بگو بدون توضیح اضافه: "{text}"')
        bot.edit_message_text(f'🌐 *ترجمه:*\n\n{reply}',
                              message.chat.id, msg.message_id, parse_mode='Markdown')

    # ─── فونت زیباساز ───
    @bot.message_handler(commands=['font', 'فونت'])
    def font_cmd(message):
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            bot.reply_to(message, '✨ مثال: `/font متن شما`', parse_mode='Markdown'); return
        text = parts[1]
        results = (
            f'✨ *فونت‌های زیبا:*\n\n'
            f'𝟏: `𝗦𝗙𝗢𝗥` ← Bold\n'
            f'𝟐: `𝘚𝘍𝘖𝘙` ← Italic\n'
            f'𝟑: `𝙎𝙁𝙊𝙍` ← Bold Italic\n\n'
            f'متن اصلی: *{text}*'
        )
        bot.reply_to(message, results, parse_mode='Markdown')

    # ─── کپچا callback ───
    @bot.callback_query_handler(func=lambda c: c.data.startswith('captcha_'))
    def captcha_callback(call):
        parts = call.data.split('_')
        target_uid = int(parts[1])
        answer = int(parts[2])
        uid = call.from_user.id
        cid = call.message.chat.id

        if uid != target_uid:
            bot.answer_callback_query(call.id, '⛔ این کپچا برای تو نیست!', show_alert=True); return

        conn = db()
        c = conn.cursor()
        c.execute('SELECT answer, expires_at FROM captcha_pending WHERE user_id=? AND group_id=?',
                  (uid, cid))
        row = c.fetchone()

        if not row:
            bot.answer_callback_query(call.id, '❌ کپچا پیدا نشد.', show_alert=True)
            conn.close(); return

        correct_answer = row[0]
        expires_at = datetime.fromisoformat(row[1])

        if datetime.now() > expires_at:
            bot.answer_callback_query(call.id, '⏰ وقت کپچا تموم شد!', show_alert=True)
            c.execute('DELETE FROM captcha_pending WHERE user_id=? AND group_id=?', (uid, cid))
            conn.commit(); conn.close()
            try: bot.kick_chat_member(cid, uid)
            except: pass
            return

        if answer == correct_answer:
            # آزاد کردن کاربر
            try:
                bot.restrict_chat_member(cid, uid,
                    permissions=ChatPermissions(
                        can_send_messages=True, can_send_media_messages=True,
                        can_send_polls=True, can_send_other_messages=True,
                        can_add_web_page_previews=True))
            except: pass
            c.execute('DELETE FROM captcha_pending WHERE user_id=? AND group_id=?', (uid, cid))
            conn.commit(); conn.close()
            bot.answer_callback_query(call.id, '✅ درسته! خوش اومدی!', show_alert=True)
            try: bot.delete_message(cid, call.message.message_id)
            except: pass
            safe_send(cid, f'✅ *{call.from_user.first_name}* تایید شد! خوش اومدی 👋',
                      parse_mode='Markdown')
        else:
            bot.answer_callback_query(call.id, '❌ اشتباهه! دوباره امتحان کن.', show_alert=True)
            conn.close()

    # ─── بروزرسانی قیمت ───
    @bot.callback_query_handler(func=lambda c: c.data == 'refresh_price')
    def refresh_price(call):
        result = get_prices()
        m = InlineKeyboardMarkup()
        m.add(InlineKeyboardButton('🔄 بروزرسانی', callback_data='refresh_price'))
        try:
            bot.edit_message_text(result, call.message.chat.id, call.message.message_id,
                                  parse_mode='Markdown', reply_markup=m)
            bot.answer_callback_query(call.id, '✅ بروز شد!')
        except:
            bot.answer_callback_query(call.id, 'تغییری نبود.')

    # ─── امتیاز خودکار پیام‌های گروه ───
    @bot.message_handler(func=lambda m: m.chat.type in ['group', 'supergroup'] and m.text)
    def score_tracker(message):
        if message.from_user and not message.from_user.is_bot:
            add_score(message.from_user.id, message.chat.id, 1)
            # چک بازی حدس عدد
            result = check_number_game(message.chat.id, message.text)
            if result:
                bot.reply_to(message, result, parse_mode='Markdown')

    # ─── شروع reminder thread ───
    import threading
    threading.Thread(target=check_reminders, daemon=True).start()

    print('[SFOR] ✅ All feature handlers registered!', flush=True)
