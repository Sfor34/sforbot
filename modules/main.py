import requests, datetime, time, re
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ChatPermissions

GROQ_KEY   = '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'
GROQ_URL   = 'https://api.groq.com/openai/v1/chat/completions'
GROQ_MODEL = 'llama-3.3-70b-versatile'
LINK_RE    = re.compile(r'(https?://|t\.me/|@\w{5,})', re.IGNORECASE)

CONFIGS = """vless://d0cfc134-447c-4c84-965a-ff5f827c9016@116.203.60.171:8080?security=none&type=tcp#SFOR-1
trojan://humanity@188.114.97.6:443?path=%2Fassignment&security=tls&host=www.calmloud.com&type=ws&sni=www.calmloud.com#SFOR-2
trojan://humanity@212.183.88.136:443?path=%2Fassignment&security=tls&host=www.calmlunch.com&type=ws&sni=www.calmlunch.com#SFOR-3
vless://e65c9135-5c62-4e63-9bec-bca0cdf94f52@167.172.108.83:443?security=reality&encryption=none&pbk=YIwwnfgqZKzbdxD0Mq-PiOmIDPYCvkaptHyN_HzDgFA&headerType=none&fp=firefox&spx=%2FwkBfIEIhNxYDFMj&type=tcp&flow=xtls-rprx-vision&sni=icloud.com&sid=844282e475538c#SFOR-4
trojan://Masir_Sefid@188.213.130.212:443?security=reality&pbk=w0XepGv1Hk0gBh1Apiw-nvn8SfzjWcDuxdxN1mpaF3g&headerType=none&fp=chrome&type=tcp&sni=store.steampowered.com&sid=6ced01fc4aa417#SFOR-5
vless://6ca8ea5b-e47f-4c19-adee-365456e1e87c@31.56.188.78:7443?security=reality&encryption=none&pbk=5QAO98ot2U7TcGs_f6EEaQjCzNOJLNHqPf6smYsdFVI&headerType=none&fp=firefox&type=tcp&flow=xtls-rprx-vision&sni=mi.com&sid=be0ce047#SFOR-6
vless://ad6d51ab-2d06-4d41-85b7-da9d703ea4fd@dnn4.avaaaal.ir:2087?path=%2F720f09dba195549b424f771551162528%2Fworkers%2Fservices6%2Fview6%2FAvaal6%2Fproduction6%2Fsettings&security=tls&alpn=http%2F1.1&encryption=none&host=sv333.avaaal.ir&fp=random&type=ws&sni=sv333.avaaal.ir#SFOR-7
vless://931729a8-3c20-4841-89a1-f18dc9ce0a6f@46.229.243.137:8443?security=tls&encryption=none&type=tcp&sni=cdn7-09.vk-cdnvideo.com#SFOR-10
vless://da48859d-edf9-4a8c-a026-80910591f284@nytimes.com:80?mode=auto&path=%2FTignal&security=&encryption=none&host=tignaltofansv8.global.ssl.fastly.net&type=xhttp#SFOR-11
vless://0058c215-ab1e-400c-a403-b5b2fda7e846@199.232.197.131:80?path=%2F&security=&encryption=none&host=max-gb1.global.ssl.fastly.net&type=ws#SFOR-12"""

# ══ helpers ══════════════════════════════════════════════════════════════════

def now(): return str(datetime.datetime.now())

def save_user(u):
    c = db()
    c.execute('INSERT OR IGNORE INTO users(id,username,first_name,joined_at) VALUES(?,?,?,?)',
              (u.id, u.username, u.first_name, now()))
    c.execute('UPDATE users SET last_seen=?,message_count=message_count+1 WHERE id=?', (now(), u.id))
    c.commit(); c.close()

def save_group(chat):
    c = db()
    c.execute('INSERT OR IGNORE INTO groups(id,title,joined_at) VALUES(?,?,?)',
              (chat.id, chat.title, now()))
    c.commit(); c.close()

def get_group(gid):
    c = db()
    g = c.execute('SELECT * FROM groups WHERE id=?', (gid,)).fetchone()
    c.close()
    return g

def is_admin(msg):
    try:
        m = bot.get_chat_member(msg.chat.id, msg.from_user.id)
        return m.status in ['administrator', 'creator']
    except: return False

def log(etype, uid, gid, detail):
    c = db()
    c.execute('INSERT INTO logs(event_type,user_id,group_id,detail,created_at) VALUES(?,?,?,?,?)',
              (etype, uid, gid, detail, now()))
    c.commit(); c.close()

def ask_ai(uid, question):
    c = db()
    rows = c.execute('SELECT role,content FROM ai_history WHERE user_id=? ORDER BY id DESC LIMIT 10',
                     (uid,)).fetchall()
    c.close()
    history = [{'role': r['role'], 'content': r['content']} for r in reversed(rows)]
    history.append({'role': 'user', 'content': question})
    try:
        r = requests.post(GROQ_URL, json={
            'model': GROQ_MODEL,
            'messages': [{'role': 'system', 'content': 'تو یه دستیار هوشمند فارسی‌زبانی. کوتاه و مفید جواب بده.'}] + history,
            'max_tokens': 1000
        }, headers={'Authorization': f'Bearer {GROQ_KEY}', 'Content-Type': 'application/json'}, timeout=30)
        answer = r.json()['choices'][0]['message']['content']
        c = db()
        c.execute('INSERT INTO ai_history(user_id,role,content,created_at) VALUES(?,?,?,?)', (uid,'user',question,now()))
        c.execute('INSERT INTO ai_history(user_id,role,content,created_at) VALUES(?,?,?,?)', (uid,'assistant',answer,now()))
        c.execute('DELETE FROM ai_history WHERE user_id=? AND id NOT IN (SELECT id FROM ai_history WHERE user_id=? ORDER BY id DESC LIMIT 20)', (uid,uid))
        c.commit(); c.close()
        return answer
    except Exception as e:
        return f'❌ خطا: {str(e)[:80]}'

# ══ keyboards ═════════════════════════════════════════════════════════════════

def kb_main():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton('🤖 هوش مصنوعی', callback_data='ai_help'),
        InlineKeyboardButton('🔒 کانفیگ V2Ray', callback_data='get_config'),
        InlineKeyboardButton('🛡️ فیلترشکن VPN', callback_data='get_vpn'),
        InlineKeyboardButton('🌐 سایت SFOR', url=SITE_URL),
        InlineKeyboardButton('📞 پشتیبانی', callback_data='support'),
        InlineKeyboardButton('ℹ️ درباره ما', callback_data='about'),
    )
    return kb

def kb_admin():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton('👥 کاربران', callback_data='adm_users'),
        InlineKeyboardButton('💬 گروه‌ها', callback_data='adm_groups'),
        InlineKeyboardButton('🔒 کانفیگ‌ها', callback_data='adm_configs'),
        InlineKeyboardButton('🛡️ VPN ها', callback_data='adm_vpns'),
        InlineKeyboardButton('📋 لاگ‌ها', callback_data='adm_logs'),
        InlineKeyboardButton('📢 همگانی', callback_data='adm_broadcast'),
    )
    return kb

def kb_group_settings(gid):
    g = get_group(gid)
    if not g: return None
    def st(v): return '✅' if v else '❌'
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton(f'{st(g["anti_link"])} ضد لینک', callback_data=f'grp_toggle_anti_link_{gid}'),
        InlineKeyboardButton(f'{st(g["anti_spam"])} ضد اسپم', callback_data=f'grp_toggle_anti_spam_{gid}'),
        InlineKeyboardButton(f'{st(g["welcome"])} خوش‌آمد', callback_data=f'grp_toggle_welcome_{gid}'),
        InlineKeyboardButton(f'{st(g["goodbye"])} خداحافظ', callback_data=f'grp_toggle_goodbye_{gid}'),
        InlineKeyboardButton(f'{st(g["ai_reply"])} AI در گروه', callback_data=f'grp_toggle_ai_reply_{gid}'),
    )
    return kb

# ══ /start /help ══════════════════════════════════════════════════════════════

@bot.message_handler(commands=['start'])
def cmd_start(msg):
    save_user(msg.from_user)
    name = msg.from_user.first_name or 'کاربر'
    text = (
        f'سلام {name}! 👋\n\n'
        '🔥 به ربات SFOR خوش اومدی\n'
        'امنیت | هک | فیلترشکن | هوش مصنوعی\n\n'
        '👇 از دکمه‌ها استفاده کن:'
    )
    bot.send_message(msg.chat.id, text, reply_markup=kb_main())

@bot.message_handler(commands=['help'])
def cmd_help(msg):
    save_user(msg.from_user)
    text = (
        '📋 راهنمای ربات SFOR\n\n'
        '🤖 هوش مصنوعی:\n'
        '• /ai سوالت — چت با AI\n'
        '• پی وی — مستقیم پیام بده\n\n'
        '🔒 فیلترشکن:\n'
        '• /config — کانفیگ V2Ray رایگان\n'
        '• /vpn — فایل VPN\n\n'
        '🔍 امنیت:\n'
        '• /scan دامنه — آنالیز امنیتی\n\n'
        '⚙️ ابزار:\n'
        '• /id — آیدی تلگرام\n'
        '• /ping — تست سرعت\n'
        '• /anon [پیام] — پیام ناشناس\n'
        '• /note [عنوان] [متن] — یادداشت\n\n'
        '👮 مدیریت گروه:\n'
        '• /warn — اخطار\n'
        '• /kick — اخراج\n'
        '• /ban — بن\n'
        '• /unban — رفع بن\n'
        '• /mute [دقیقه] — سکوت\n'
        '• /unmute — رفع سکوت\n'
        '• /rules — قوانین گروه\n'
        '• /setrules [متن] — تنظیم قوانین\n'
        '• /settings — تنظیمات گروه\n'
        '• /warns — اخطارهای کاربر\n'
        '• /clearwarns — پاک کردن اخطار'
    )
    bot.send_message(msg.chat.id, text, reply_markup=kb_main())

# ══ /id /ping ═════════════════════════════════════════════════════════════════

@bot.message_handler(commands=['id'])
def cmd_id(msg):
    save_user(msg.from_user)
    u = msg.from_user
    text = f'🆔 ID شما: {u.id}\n👤 نام: {u.first_name}'
    if u.username: text += f'\n🔗 یوزر: @{u.username}'
    if msg.chat.type in ['group', 'supergroup']:
        text += f'\n\n💬 گروه: {msg.chat.title}\n🆔 ID گروه: {msg.chat.id}'
    bot.reply_to(msg, text)

@bot.message_handler(commands=['ping'])
def cmd_ping(msg):
    t = time.time()
    m = bot.reply_to(msg, '🏓 ...')
    ms = int((time.time() - t) * 1000)
    bot.edit_message_text(f'🏓 Pong! {ms}ms', msg.chat.id, m.message_id)

# ══ /ai ═══════════════════════════════════════════════════════════════════════

@bot.message_handler(commands=['ai'])
def cmd_ai(msg):
    save_user(msg.from_user)
    parts = msg.text.split(' ', 1)
    if len(parts) < 2 or not parts[1].strip():
        bot.reply_to(msg, '❓ سوالت رو بنویس:\nمثال: /ai پایتون چیه؟')
        return
    w = bot.reply_to(msg, '🤖 در حال پردازش...')
    answer = ask_ai(msg.from_user.id, parts[1].strip())
    bot.edit_message_text(f'🤖 {answer}', msg.chat.id, w.message_id)

# ══ /scan (GODRISK) ═══════════════════════════════════════════════════════════

@bot.message_handler(commands=['scan'])
def cmd_scan(msg):
    save_user(msg.from_user)
    parts = msg.text.split(' ', 1)
    if len(parts) < 2 or not parts[1].strip():
        bot.reply_to(msg, '❓ دامنه رو بنویس:\nمثال: /scan google.com')
        return
    domain = parts[1].strip().replace('https://','').replace('http://','').split('/')[0]
    w = bot.reply_to(msg, f'🔍 در حال آنالیز {domain}...')
    score = 0
    results = []
    checks = {
        'SPF':    f'https://dns.google/resolve?name={domain}&type=TXT',
        'DMARC':  f'https://dns.google/resolve?name=_dmarc.{domain}&type=TXT',
        'DKIM':   f'https://dns.google/resolve?name=default._domainkey.{domain}&type=TXT',
        'HSTS':   f'https://hsts.badssl.com/',
        'DNSSEC': f'https://dns.google/resolve?name={domain}&type=DS',
        'CAA':    f'https://dns.google/resolve?name={domain}&type=CAA',
    }
    for name, url in checks.items():
        try:
            r = requests.get(url, timeout=5)
            data = r.json()
            has = bool(data.get('Answer'))
            if not has: score += 15
            results.append(f'{"✅" if has else "❌"} {name}')
        except:
            score += 10
            results.append(f'⚠️ {name}: خطا')

    if score >= 70: emoji = '🔴 خطرناک'
    elif score >= 40: emoji = '🟡 متوسط'
    else: emoji = '🟢 امن'

    text = f'🔍 GODRISK — آنالیز {domain}\n\n'
    text += '\n'.join(results)
    text += f'\n\n📊 امتیاز ریسک: {score}/100\n🛡️ وضعیت: {emoji}'
    bot.edit_message_text(text, msg.chat.id, w.message_id)

# ══ /config /vpn ══════════════════════════════════════════════════════════════

@bot.message_handler(commands=['config'])
def cmd_config(msg):
    save_user(msg.from_user)
    uid = msg.from_user.id
    c = db()
    already = c.execute('SELECT 1 FROM user_configs WHERE user_id=?', (uid,)).fetchone()
    if already:
        c.close()
        bot.reply_to(msg, '⚠️ قبلاً کانفیگ دریافت کردی!\nهر کاربر فقط یه بار میتونه بگیره.')
        return
    c.execute('INSERT INTO user_configs(user_id,given_at) VALUES(?,?)', (uid, now()))
    c.commit(); c.close()
    text = '🔒 کانفیگ‌های V2Ray رایگان SFOR:\n\n' + CONFIGS + '\n\n📱 توی V2rayNG یا Nekobox وارد کن.'
    bot.reply_to(msg, text)
    log('config_given', uid, 0, 'sent')

@bot.message_handler(commands=['vpn'])
def cmd_vpn(msg):
    save_user(msg.from_user)
    uid = msg.from_user.id
    c = db()
    already = c.execute('SELECT 1 FROM user_vpns WHERE user_id=?', (uid,)).fetchone()
    if already:
        c.close()
        bot.reply_to(msg, '⚠️ قبلاً فایل VPN دریافت کردی!')
        return
    vpn = c.execute('SELECT * FROM vpn_files WHERE is_used=0 LIMIT 1').fetchone()
    if not vpn:
        c.close()
        bot.reply_to(msg, '😔 فعلاً فایل VPN موجود نیست.\nزود برمیگرده!')
        return
    c.execute('UPDATE vpn_files SET is_used=1,used_by=? WHERE id=?', (uid, vpn['id']))
    c.execute('INSERT INTO user_vpns(user_id,given_at) VALUES(?,?)', (uid, now()))
    c.commit(); c.close()
    try:
        bot.send_document(msg.chat.id, vpn['file_id'],
                          caption=f'🛡️ فایل VPN: {vpn["name"]}\nبا NPV Tunnel باز کن.')
        log('vpn_given', uid, 0, vpn['name'])
    except:
        bot.reply_to(msg, '❌ خطا در ارسال فایل.')

# ══ /anon /note ═══════════════════════════════════════════════════════════════

@bot.message_handler(commands=['anon'])
def cmd_anon(msg):
    parts = msg.text.split(' ', 1)
    if len(parts) < 2 or not parts[1].strip():
        bot.reply_to(msg, '❓ پیامت رو بنویس:\nمثال: /anon سلام به همه!')
        return
    bot.send_message(msg.chat.id, f'👤 پیام ناشناس:\n\n{parts[1].strip()}')
    try: bot.delete_message(msg.chat.id, msg.message_id)
    except: pass

@bot.message_handler(commands=['note'])
def cmd_note(msg):
    save_user(msg.from_user)
    parts = msg.text.split(' ', 2)
    if len(parts) < 3:
        bot.reply_to(msg, '❓ فرمت:\n/note عنوان متن\n\nمثال: /note رمز wifi1234')
        return
    name, content = parts[1], parts[2]
    c = db()
    gid = msg.chat.id if msg.chat.type in ['group','supergroup'] else 0
    c.execute('INSERT INTO notes(user_id,group_id,name,content,created_at) VALUES(?,?,?,?,?)',
              (msg.from_user.id, gid, name, content, now()))
    c.commit(); c.close()
    bot.reply_to(msg, f'✅ یادداشت "{name}" ذخیره شد.')

@bot.message_handler(commands=['notes'])
def cmd_notes(msg):
    save_user(msg.from_user)
    c = db()
    gid = msg.chat.id if msg.chat.type in ['group','supergroup'] else 0
    rows = c.execute('SELECT name,content FROM notes WHERE user_id=? AND group_id=?',
                     (msg.from_user.id, gid)).fetchall()
    c.close()
    if not rows:
        bot.reply_to(msg, '📝 یادداشتی نداری.')
        return
    text = '📝 یادداشت‌های تو:\n\n'
    for r in rows:
        text += f'• {r["name"]}: {r["content"]}\n'
    bot.reply_to(msg, text)

# ══ group management ══════════════════════════════════════════════════════════

@bot.message_handler(commands=['warn'])
def cmd_warn(msg):
    if msg.chat.type not in ['group','supergroup']: return
    if not is_admin(msg): bot.reply_to(msg, '❌ فقط ادمین‌ها.'); return
    if not msg.reply_to_message: bot.reply_to(msg, '↩️ روی پیام کاربر ریپلای کن.'); return
    t = msg.reply_to_message.from_user
    reason = msg.text.split(' ',1)[1] if len(msg.text.split(' ',1))>1 else 'بدون دلیل'
    c = db()
    c.execute('INSERT INTO warns(user_id,group_id,reason,warned_at) VALUES(?,?,?,?)',
              (t.id, msg.chat.id, reason, now()))
    cnt = c.execute('SELECT COUNT(*) as n FROM warns WHERE user_id=? AND group_id=?',
                    (t.id, msg.chat.id)).fetchone()['n']
    grp = c.execute('SELECT warn_limit FROM groups WHERE id=?', (msg.chat.id,)).fetchone()
    lim = grp['warn_limit'] if grp else 3
    c.commit(); c.close()
    save_group(msg.chat)
    bot.reply_to(msg, f'⚠️ اخطار به {t.first_name}\nدلیل: {reason}\nاخطار: {cnt}/{lim}')
    if cnt >= lim:
        try:
            bot.kick_chat_member(msg.chat.id, t.id)
            bot.send_message(msg.chat.id, f'🚫 {t.first_name} به خاطر {cnt} اخطار اخراج شد.')
        except: bot.send_message(msg.chat.id, '❌ نتونستم اخراج کنم. ربات ادمینه؟')

@bot.message_handler(commands=['warns'])
def cmd_warns(msg):
    if not msg.reply_to_message: bot.reply_to(msg, '↩️ ریپلای کن.'); return
    t = msg.reply_to_message.from_user
    c = db()
    cnt = c.execute('SELECT COUNT(*) as n FROM warns WHERE user_id=? AND group_id=?',
                    (t.id, msg.chat.id)).fetchone()['n']
    c.close()
    bot.reply_to(msg, f'📋 {t.first_name}: {cnt} اخطار')

@bot.message_handler(commands=['clearwarns'])
def cmd_clearwarns(msg):
    if not is_admin(msg): return
    if not msg.reply_to_message: bot.reply_to(msg, '↩️ ریپلای کن.'); return
    t = msg.reply_to_message.from_user
    c = db()
    c.execute('DELETE FROM warns WHERE user_id=? AND group_id=?', (t.id, msg.chat.id))
    c.commit(); c.close()
    bot.reply_to(msg, f'✅ اخطارهای {t.first_name} پاک شد.')

@bot.message_handler(commands=['kick'])
def cmd_kick(msg):
    if not is_admin(msg): return
    if not msg.reply_to_message: bot.reply_to(msg, '↩️ ریپلای کن.'); return
    t = msg.reply_to_message.from_user
    try:
        bot.kick_chat_member(msg.chat.id, t.id)
        bot.unban_chat_member(msg.chat.id, t.id)
        bot.reply_to(msg, f'👢 {t.first_name} اخراج شد.')
    except: bot.reply_to(msg, '❌ نتونستم اخراج کنم.')

@bot.message_handler(commands=['ban'])
def cmd_ban(msg):
    if not is_admin(msg): return
    if not msg.reply_to_message: bot.reply_to(msg, '↩️ ریپلای کن.'); return
    t = msg.reply_to_message.from_user
    try:
        bot.kick_chat_member(msg.chat.id, t.id)
        bot.reply_to(msg, f'🚫 {t.first_name} بن شد.')
        log('ban', t.id, msg.chat.id, 'banned')
    except: bot.reply_to(msg, '❌ نتونستم بن کنم.')

@bot.message_handler(commands=['unban'])
def cmd_unban(msg):
    if not is_admin(msg): return
    if not msg.reply_to_message: bot.reply_to(msg, '↩️ ریپلای کن.'); return
    t = msg.reply_to_message.from_user
    try:
        bot.unban_chat_member(msg.chat.id, t.id)
        bot.reply_to(msg, f'✅ بن {t.first_name} برداشته شد.')
    except: bot.reply_to(msg, '❌ خطا.')

@bot.message_handler(commands=['mute'])
def cmd_mute(msg):
    if not is_admin(msg): return
    if not msg.reply_to_message: bot.reply_to(msg, '↩️ ریپلای کن.'); return
    t = msg.reply_to_message.from_user
    try: mins = int(msg.text.split()[1])
    except: mins = 10
    until = int(time.time()) + mins * 60
    try:
        bot.restrict_chat_member(msg.chat.id, t.id,
            permissions=ChatPermissions(can_send_messages=False), until_date=until)
        bot.reply_to(msg, f'🔇 {t.first_name} برای {mins} دقیقه سکوت شد.')
    except: bot.reply_to(msg, '❌ نتونستم میوت کنم.')

@bot.message_handler(commands=['unmute'])
def cmd_unmute(msg):
    if not is_admin(msg): return
    if not msg.reply_to_message: bot.reply_to(msg, '↩️ ریپلای کن.'); return
    t = msg.reply_to_message.from_user
    try:
        bot.restrict_chat_member(msg.chat.id, t.id,
            permissions=ChatPermissions(
                can_send_messages=True, can_send_media_messages=True,
                can_send_polls=True, can_send_other_messages=True,
                can_add_web_page_previews=True))
        bot.reply_to(msg, f'🔊 سکوت {t.first_name} برداشته شد.')
    except: bot.reply_to(msg, '❌ خطا.')

@bot.message_handler(commands=['rules'])
def cmd_rules(msg):
    if msg.chat.type not in ['group','supergroup']: return
    g = get_group(msg.chat.id)
    if not g or not g['rules']:
        bot.reply_to(msg, '📜 قوانینی تنظیم نشده.\nادمین از /setrules استفاده کنه.')
        return
    bot.reply_to(msg, f'📜 قوانین گروه:\n\n{g["rules"]}')

@bot.message_handler(commands=['setrules'])
def cmd_setrules(msg):
    if msg.chat.type not in ['group','supergroup']: return
    if not is_admin(msg): bot.reply_to(msg, '❌ فقط ادمین‌ها.'); return
    parts = msg.text.split(' ', 1)
    if len(parts) < 2: bot.reply_to(msg, '❓ متن قوانین رو بنویس.'); return
    save_group(msg.chat)
    c = db()
    c.execute('UPDATE groups SET rules=? WHERE id=?', (parts[1], msg.chat.id))
    c.commit(); c.close()
    bot.reply_to(msg, '✅ قوانین گروه ذخیره شد.')

@bot.message_handler(commands=['settings'])
def cmd_settings(msg):
    if msg.chat.type not in ['group','supergroup']: return
    if not is_admin(msg): bot.reply_to(msg, '❌ فقط ادمین‌ها.'); return
    save_group(msg.chat)
    bot.reply_to(msg, '⚙️ تنظیمات گروه:', reply_markup=kb_group_settings(msg.chat.id))

# ══ admin commands ════════════════════════════════════════════════════════════

@bot.message_handler(commands=['panel'])
def cmd_panel(msg):
    if msg.from_user.id != ADMIN_ID: return
    c = db()
    u = c.execute('SELECT COUNT(*) as n FROM users').fetchone()['n']
    g = c.execute('SELECT COUNT(*) as n FROM groups').fetchone()['n']
    cfg = c.execute('SELECT COUNT(*) as n FROM user_configs').fetchone()['n']
    vpn_free = c.execute('SELECT COUNT(*) as n FROM vpn_files WHERE is_used=0').fetchone()['n']
    vpn_used = c.execute('SELECT COUNT(*) as n FROM vpn_files WHERE is_used=1').fetchone()['n']
    c.close()
    text = (f'⚙️ پنل ادمین SFOR\n\n'
            f'👥 کاربران: {u}\n💬 گروه‌ها: {g}\n'
            f'🔒 کانفیگ داده شده: {cfg}\n'
            f'🛡️ VPN آزاد: {vpn_free} | داده شده: {vpn_used}')
    bot.send_message(msg.chat.id, text, reply_markup=kb_admin())

@bot.message_handler(commands=['broadcast'])
def cmd_broadcast(msg):
    if msg.from_user.id != ADMIN_ID: return
    parts = msg.text.split(' ', 1)
    if len(parts) < 2: bot.reply_to(msg, '❌ پیام بنویس.'); return
    text = parts[1]
    c = db()
    users = c.execute('SELECT id FROM users WHERE is_banned=0').fetchall()
    c.close()
    sent = 0
    for u in users:
        try: bot.send_message(u['id'], f'📢 پیام SFOR:\n\n{text}'); sent += 1; time.sleep(0.05)
        except: pass
    bot.reply_to(msg, f'✅ {sent} نفر دریافت کردن.')

@bot.message_handler(commands=['logs'])
def cmd_logs(msg):
    if msg.from_user.id != ADMIN_ID: return
    c = db()
    rows = c.execute('SELECT * FROM logs ORDER BY id DESC LIMIT 10').fetchall()
    c.close()
    if not rows: bot.reply_to(msg, '📋 لاگی وجود نداره.'); return
    text = '📋 آخرین لاگ‌ها:\n\n'
    for r in rows:
        text += f'• {r["event_type"]} | user:{r["user_id"]} | {r["detail"]}\n'
    bot.reply_to(msg, text)

@bot.message_handler(commands=['addvpn'])
def cmd_addvpn(msg):
    if msg.from_user.id != ADMIN_ID: return
    if not msg.reply_to_message or not msg.reply_to_message.document:
        bot.reply_to(msg, '↩️ روی فایل .npvt ریپلای کن و /addvpn بزن.')
        return
    doc = msg.reply_to_message.document
    c = db()
    c.execute('INSERT INTO vpn_files(name,file_id,created_at) VALUES(?,?,?)',
              (doc.file_name, doc.file_id, now()))
    c.commit(); c.close()
    bot.reply_to(msg, f'✅ فایل {doc.file_name} اضافه شد.')

# ══ welcome / goodbye ═════════════════════════════════════════════════════════

@bot.message_handler(content_types=['new_chat_members'])
def welcome(msg):
    save_group(msg.chat)
    g = get_group(msg.chat.id)
    if not g or not g['welcome']: return
    for member in msg.new_chat_members:
        if member.is_bot: continue
        text = g['welcome_msg'] if g['welcome_msg'] else f'👋 سلام {member.first_name}!\nبه {msg.chat.title} خوش اومدی 🔥'
        bot.send_message(msg.chat.id, text)

@bot.message_handler(content_types=['left_chat_member'])
def goodbye(msg):
    g = get_group(msg.chat.id)
    if not g or not g['goodbye']: return
    member = msg.left_chat_member
    if member.is_bot: return
    text = g['goodbye_msg'] if g['goodbye_msg'] else f'👋 {member.first_name} گروه رو ترک کرد.'
    bot.send_message(msg.chat.id, text)

# ══ callbacks ═════════════════════════════════════════════════════════════════

@bot.callback_query_handler(func=lambda c: True)
def handle_callback(call):
    uid = call.from_user.id
    cid = call.message.chat.id
    data = call.data

    # ── main menu ──
    if data == 'ai_help':
        bot.answer_callback_query(call.id)
        bot.send_message(cid, '🤖 پیامت رو مستقیم بنویس یا:\n/ai سوالت')

    elif data == 'get_config':
        bot.answer_callback_query(call.id)
        c = db()
        already = c.execute('SELECT 1 FROM user_configs WHERE user_id=?', (uid,)).fetchone()
        if already:
            c.close(); bot.send_message(cid, '⚠️ قبلاً کانفیگ دریافت کردی!'); return
        c.execute('INSERT INTO user_configs(user_id,given_at) VALUES(?,?)', (uid, now()))
        c.commit(); c.close()
        bot.send_message(cid, '🔒 کانفیگ‌های V2Ray رایگان SFOR:\n\n' + CONFIGS + '\n\n📱 توی V2rayNG یا Nekobox وارد کن.')

    elif data == 'get_vpn':
        bot.answer_callback_query(call.id)
        c = db()
        already = c.execute('SELECT 1 FROM user_vpns WHERE user_id=?', (uid,)).fetchone()
        if already:
            c.close(); bot.send_message(cid, '⚠️ قبلاً فایل VPN دریافت کردی!'); return
        vpn = c.execute('SELECT * FROM vpn_files WHERE is_used=0 LIMIT 1').fetchone()
        if not vpn:
            c.close(); bot.send_message(cid, '😔 فعلاً فایل VPN موجود نیست.'); return
        c.execute('UPDATE vpn_files SET is_used=1,used_by=? WHERE id=?', (uid, vpn['id']))
        c.execute('INSERT INTO user_vpns(user_id,given_at) VALUES(?,?)', (uid, now()))
        c.commit(); c.close()
        try: bot.send_document(cid, vpn['file_id'], caption=f'🛡️ {vpn["name"]}\nبا NPV Tunnel باز کن.')
        except: bot.send_message(cid, '❌ خطا در ارسال فایل.')

    elif data == 'support':
        bot.answer_callback_query(call.id)
        bot.send_message(cid, '📞 پشتیبانی:\nتلگرام: @mmadsfor\nاینستاگرام: @mmadsfor')

    elif data == 'about':
        bot.answer_callback_query(call.id)
        bot.send_message(cid,
            '🔥 ربات SFOR\n\nنسخه: 4.0.0\n'
            'امنیت | هک | فیلترشکن | هوش مصنوعی\n\n'
            f'🌐 {SITE_URL}\n📱 @mmadsfor')

    # ── admin panel ──
    elif data == 'adm_users' and uid == ADMIN_ID:
        bot.answer_callback_query(call.id)
        c = db()
        total = c.execute('SELECT COUNT(*) as n FROM users').fetchone()['n']
        banned = c.execute('SELECT COUNT(*) as n FROM users WHERE is_banned=1').fetchone()['n']
        c.close()
        bot.send_message(cid, f'👥 کل کاربران: {total}\n🚫 بن شده: {banned}')

    elif data == 'adm_groups' and uid == ADMIN_ID:
        bot.answer_callback_query(call.id)
        c = db()
        cnt = c.execute('SELECT COUNT(*) as n FROM groups').fetchone()['n']
        c.close()
        bot.send_message(cid, f'💬 گروه‌ها: {cnt}')

    elif data == 'adm_configs' and uid == ADMIN_ID:
        bot.answer_callback_query(call.id)
        c = db()
        given = c.execute('SELECT COUNT(*) as n FROM user_configs').fetchone()['n']
        c.close()
        bot.send_message(cid, f'🔒 کانفیگ داده شده: {given}')

    elif data == 'adm_vpns' and uid == ADMIN_ID:
        bot.answer_callback_query(call.id)
        c = db()
        free = c.execute('SELECT COUNT(*) as n FROM vpn_files WHERE is_used=0').fetchone()['n']
        used = c.execute('SELECT COUNT(*) as n FROM vpn_files WHERE is_used=1').fetchone()['n']
        c.close()
        bot.send_message(cid, f'🛡️ VPN آزاد: {free}\n✅ داده شده: {used}')

    elif data == 'adm_logs' and uid == ADMIN_ID:
        bot.answer_callback_query(call.id)
        c = db()
        rows = c.execute('SELECT * FROM logs ORDER BY id DESC LIMIT 5').fetchall()
        c.close()
        if not rows: bot.send_message(cid, '📋 لاگی نیست.'); return
        text = '📋 آخرین لاگ‌ها:\n\n'
        for r in rows:
            text += f'• {r["event_type"]} | {r["user_id"]} | {r["detail"]}\n'
        bot.send_message(cid, text)

    elif data == 'adm_broadcast' and uid == ADMIN_ID:
        bot.answer_callback_query(call.id)
        bot.send_message(cid, '📢 پیام همگانی:\n/broadcast متن پیام')

    # ── group settings toggles ──
    elif data.startswith('grp_toggle_') and uid == ADMIN_ID:
        bot.answer_callback_query(call.id)
        parts = data.split('_')
        # grp_toggle_anti_link_-100xxx  یا grp_toggle_welcome_-100xxx
        # parts: [grp, toggle, field1, (field2?), gid]
        gid = int(parts[-1])
        field = '_'.join(parts[2:-1])
        c = db()
        g = c.execute('SELECT * FROM groups WHERE id=?', (gid,)).fetchone()
        if g:
            new_val = 0 if g[field] else 1
            c.execute(f'UPDATE groups SET {field}=? WHERE id=?', (new_val, gid))
            c.commit()
        c.close()
        try:
            bot.edit_message_reply_markup(cid, call.message.message_id,
                                          reply_markup=kb_group_settings(gid))
        except: pass

    else:
        bot.answer_callback_query(call.id)

# ══ text handler (AI + فارسی + گروه) ════════════════════════════════════════

@bot.message_handler(func=lambda m: True, content_types=['text'])
def handle_text(msg):
    if not msg.from_user or not msg.text: return
    save_user(msg.from_user)
    text = msg.text.strip()
    uid = msg.from_user.id

    # دستورات فارسی
    persian = {
        'راهنما': cmd_help, 'کمک': cmd_help, 'منو': cmd_start, 'شروع': cmd_start,
        'کانفیگ': cmd_config, 'کانفیگ‌ها': cmd_config,
        'فیلترشکن': cmd_vpn, 'vpn': cmd_vpn, 'وی پی ان': cmd_vpn,
        'آیدی': cmd_id, 'id': cmd_id,
        'پینگ': cmd_ping, 'ping': cmd_ping,
        'پنل': cmd_panel, 'panel': cmd_panel,
        'لاگ': cmd_logs, 'logs': cmd_logs,
    }
    if text.lower() in persian:
        return persian[text.lower()](msg)

    # گروه
    if msg.chat.type in ['group', 'supergroup']:
        save_group(msg.chat)
        g = get_group(msg.chat.id)
        if not g: return

        # آنتی لینک
        if g['anti_link'] and LINK_RE.search(text):
            try:
                if not is_admin(msg):
                    bot.delete_message(msg.chat.id, msg.message_id)
                    bot.send_message(msg.chat.id, f'🚫 {msg.from_user.first_name}، لینک ممنوعه!')
                    return
            except: pass

        # آنتی اسپم
        if g['anti_spam']:
            t_now = time.time()
            c = db()
            row = c.execute('SELECT count,last_time FROM spam_track WHERE user_id=? AND group_id=?',
                            (uid, msg.chat.id)).fetchone()
            if row:
                elapsed = t_now - float(row['last_time'] or 0)
                cnt = row['count'] + 1 if elapsed < 5 else 1
                c.execute('UPDATE spam_track SET count=?,last_time=? WHERE user_id=? AND group_id=?',
                          (cnt, t_now, uid, msg.chat.id))
            else:
                cnt = 1
                c.execute('INSERT INTO spam_track(user_id,group_id,count,last_time) VALUES(?,?,?,?)',
                          (uid, msg.chat.id, 1, t_now))
            c.commit(); c.close()
            if cnt >= 8:
                try:
                    bot.restrict_chat_member(msg.chat.id, uid,
                        permissions=ChatPermissions(can_send_messages=False),
                        until_date=int(t_now) + 300)
                    bot.send_message(msg.chat.id, f'🔇 {msg.from_user.first_name} به خاطر اسپم ۵ دقیقه سکوت شد.')
                except: pass

        # AI در گروه (اگه فعال باشه)
        if g['ai_reply'] and not text.startswith('/'):
            w = bot.reply_to(msg, '🤖 ...')
            answer = ask_ai(uid, text)
            bot.edit_message_text(f'🤖 {answer}', msg.chat.id, w.message_id)
        return

    # پی وی — AI جواب میده
    if not text.startswith('/'):
        w = bot.reply_to(msg, '🤖 در حال پردازش...')
        answer = ask_ai(uid, text)
        bot.edit_message_text(f'🤖 {answer}', msg.chat.id, w.message_id)
