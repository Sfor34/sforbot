import requests
import datetime
import time

GROQ_KEY = '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'
GROQ_URL = 'https://api.groq.com/openai/v1/chat/completions'
GROQ_MODEL = 'llama-3.3-70b-versatile'

# ─── helpers ──────────────────────────────────────────────────────────────────

def save_user(user):
    conn = db()
    conn.execute('''
        INSERT OR IGNORE INTO users (id, username, first_name, joined_at)
        VALUES (?, ?, ?, ?)
    ''', (user.id, user.username, user.first_name, str(datetime.datetime.now())))
    conn.execute('UPDATE users SET last_seen=?, message_count=message_count+1 WHERE id=?',
                 (str(datetime.datetime.now()), user.id))
    conn.commit()
    conn.close()

def save_group(chat):
    conn = db()
    conn.execute('''
        INSERT OR IGNORE INTO groups (id, title, joined_at)
        VALUES (?, ?, ?)
    ''', (chat.id, chat.title, str(datetime.datetime.now())))
    conn.commit()
    conn.close()

def is_group_admin(message):
    try:
        member = bot.get_chat_member(message.chat.id, message.from_user.id)
        return member.status in ['administrator', 'creator']
    except:
        return False

def log_event(event_type, user_id, group_id, detail):
    conn = db()
    conn.execute('''INSERT INTO logs (event_type, user_id, group_id, detail, created_at)
                    VALUES (?, ?, ?, ?, ?)''',
                 (event_type, user_id, group_id, detail, str(datetime.datetime.now())))
    conn.commit()
    conn.close()

# ─── /start ───────────────────────────────────────────────────────────────────

@bot.message_handler(commands=['start', 'help'])
def cmd_start(message):
    save_user(message.from_user)
    name = message.from_user.first_name or 'کاربر'
    text = (
        f'👋 سلام {name}!\n\n'
        '🔥 به ربات SFOR خوش اومدی\n\n'
        '📋 دستورات:\n'
        '/ai [سوال] — چت با هوش مصنوعی\n'
        '/config — دریافت کانفیگ V2Ray رایگان\n'
        '/vpn — دریافت فایل VPN\n'
        '/id — نمایش ID تلگرام\n'
        '/ping — تست سرعت ربات\n\n'
        f'🌐 سایت: {SITE_URL}'
    )
    bot.reply_to(message, text)

# ─── /id ──────────────────────────────────────────────────────────────────────

@bot.message_handler(commands=['id'])
def cmd_id(message):
    save_user(message.from_user)
    u = message.from_user
    text = (
        f'🆔 اطلاعات شما:\n\n'
        f'ID: {u.id}\n'
        f'نام: {u.first_name}\n'
    )
    if u.username:
        text += f'یوزرنیم: @{u.username}\n'
    if message.chat.type in ['group', 'supergroup']:
        text += f'\n👥 گروه: {message.chat.title}\nID گروه: {message.chat.id}'
    bot.reply_to(message, text)

# ─── /ping ────────────────────────────────────────────────────────────────────

@bot.message_handler(commands=['ping'])
def cmd_ping(message):
    t = time.time()
    msg = bot.reply_to(message, '🏓 ...')
    ms = int((time.time() - t) * 1000)
    bot.edit_message_text(f'🏓 Pong! {ms}ms', message.chat.id, msg.message_id)

# ─── /ai ──────────────────────────────────────────────────────────────────────

@bot.message_handler(commands=['ai'])
def cmd_ai(message):
    save_user(message.from_user)
    parts = message.text.split(' ', 1)
    if len(parts) < 2 or not parts[1].strip():
        bot.reply_to(message, '❓ سوالت رو بنویس:\nمثال: /ai پایتون چیه؟')
        return

    question = parts[1].strip()
    wait_msg = bot.reply_to(message, '🤖 در حال پردازش...')

    # get history
    conn = db()
    rows = conn.execute('''SELECT role, content FROM ai_history
                           WHERE user_id=? ORDER BY id DESC LIMIT 10''',
                        (message.from_user.id,)).fetchall()
    conn.close()

    history = [{'role': r['role'], 'content': r['content']} for r in reversed(rows)]
    history.append({'role': 'user', 'content': question})

    try:
        resp = requests.post(GROQ_URL, json={
            'model': GROQ_MODEL,
            'messages': [
                {'role': 'system', 'content': 'تو یه دستیار هوشمند فارسی‌زبان هستی. کوتاه و مفید جواب بده.'}
            ] + history,
            'max_tokens': 1000
        }, headers={
            'Authorization': f'Bearer {GROQ_KEY}',
            'Content-Type': 'application/json'
        }, timeout=30)

        answer = resp.json()['choices'][0]['message']['content']

        # save history
        conn = db()
        conn.execute('INSERT INTO ai_history (user_id, role, content, created_at) VALUES (?,?,?,?)',
                     (message.from_user.id, 'user', question, str(datetime.datetime.now())))
        conn.execute('INSERT INTO ai_history (user_id, role, content, created_at) VALUES (?,?,?,?)',
                     (message.from_user.id, 'assistant', answer, str(datetime.datetime.now())))
        # keep last 20
        conn.execute('''DELETE FROM ai_history WHERE user_id=? AND id NOT IN
                        (SELECT id FROM ai_history WHERE user_id=? ORDER BY id DESC LIMIT 20)''',
                     (message.from_user.id, message.from_user.id))
        conn.commit()
        conn.close()

        bot.edit_message_text(f'🤖 {answer}', message.chat.id, wait_msg.message_id)

    except Exception as e:
        bot.edit_message_text(f'❌ خطا: {str(e)[:100]}', message.chat.id, wait_msg.message_id)

# ─── /config ──────────────────────────────────────────────────────────────────

CONFIGS = [
    'vless://d0cfc134-447c-4c84-965a-ff5f827c9016@116.203.60.171:8080?security=none&type=tcp#SFOR-1',
    'trojan://humanity@188.114.97.6:443?path=%2Fassignment&security=tls&host=www.calmloud.com&type=ws&sni=www.calmloud.com#SFOR-2',
    'trojan://humanity@212.183.88.136:443?path=%2Fassignment&security=tls&host=www.calmlunch.com&type=ws&sni=www.calmlunch.com#SFOR-3',
    'vless://e65c9135-5c62-4e63-9bec-bca0cdf94f52@167.172.108.83:443?security=reality&encryption=none&pbk=YIwwnfgqZKzbdxD0Mq-PiOmIDPYCvkaptHyN_HzDgFA&headerType=none&fp=firefox&spx=%2FwkBfIEIhNxYDFMj&type=tcp&flow=xtls-rprx-vision&sni=icloud.com&sid=844282e475538c#SFOR-4',
    'trojan://Masir_Sefid@188.213.130.212:443?security=reality&pbk=w0XepGv1Hk0gBh1Apiw-nvn8SfzjWcDuxdxN1mpaF3g&headerType=none&fp=chrome&type=tcp&sni=store.steampowered.com&sid=6ced01fc4aa417#SFOR-5',
    'vless://6ca8ea5b-e47f-4c19-adee-365456e1e87c@31.56.188.78:7443?security=reality&encryption=none&pbk=5QAO98ot2U7TcGs_f6EEaQjCzNOJLNHqPf6smYsdFVI&headerType=none&fp=firefox&type=tcp&flow=xtls-rprx-vision&sni=mi.com&sid=be0ce047#SFOR-6',
    'vless://ad6d51ab-2d06-4d41-85b7-da9d703ea4fd@dnn4.avaaaal.ir:2087?path=%2F720f09dba195549b424f771551162528%2Fworkers%2Fservices6%2Fview6%2FAvaal6%2Fproduction6%2Fsettings&security=tls&alpn=http%2F1.1&encryption=none&host=sv333.avaaal.ir&fp=random&type=ws&sni=sv333.avaaal.ir#SFOR-7',
    'vless://931729a8-3c20-4841-89a1-f18dc9ce0a6f@46.229.243.137:8443?security=tls&encryption=none&type=tcp&sni=cdn7-09.vk-cdnvideo.com#SFOR-10',
    'vless://da48859d-edf9-4a8c-a026-80910591f284@nytimes.com:80?mode=auto&path=%2FTignal&security=&encryption=none&host=tignaltofansv8.global.ssl.fastly.net&type=xhttp#SFOR-11',
    'vless://0058c215-ab1e-400c-a403-b5b2fda7e846@199.232.197.131:80?path=%2F&security=&encryption=none&host=max-gb1.global.ssl.fastly.net&type=ws#SFOR-12',
]

@bot.message_handler(commands=['config'])
def cmd_config(message):
    save_user(message.from_user)
    uid = message.from_user.id

    conn = db()
    already = conn.execute('SELECT 1 FROM user_configs WHERE user_id=?', (uid,)).fetchone()

    if already:
        conn.close()
        bot.reply_to(message, '⚠️ قبلاً کانفیگ دریافت کردی!\n\nهر کاربر فقط یه بار میتونه کانفیگ بگیره.')
        return

    # give all configs
    text = '🔒 کانفیگ‌های V2Ray رایگان SFOR:\n\n'
    text += '\n\n'.join(CONFIGS)
    text += '\n\n📱 این کانفیگ‌ها رو توی V2rayNG یا Nekobox وارد کن.'

    conn.execute('INSERT INTO user_configs (user_id, given_at) VALUES (?, ?)',
                 (uid, str(datetime.datetime.now())))
    conn.commit()
    conn.close()

    bot.reply_to(message, text)
    log_event('config_given', uid, 0, 'config sent')

# ─── /vpn ─────────────────────────────────────────────────────────────────────

@bot.message_handler(commands=['vpn'])
def cmd_vpn(message):
    save_user(message.from_user)
    uid = message.from_user.id

    conn = db()
    already = conn.execute('SELECT 1 FROM user_vpns WHERE user_id=?', (uid,)).fetchone()

    if already:
        conn.close()
        bot.reply_to(message, '⚠️ قبلاً فایل VPN دریافت کردی!\n\nهر کاربر فقط یه بار میتونه فایل بگیره.')
        return

    # check if vpn files exist in db
    vpn = conn.execute('SELECT * FROM vpn_files WHERE is_used=0 LIMIT 1').fetchone()

    if not vpn:
        conn.close()
        bot.reply_to(message, '😔 فعلاً فایل VPN موجود نیست.\n\nزود برمیگرده!')
        return

    conn.execute('UPDATE vpn_files SET is_used=1, used_by=? WHERE id=?', (uid, vpn['id']))
    conn.execute('INSERT INTO user_vpns (user_id, given_at) VALUES (?, ?)',
                 (uid, str(datetime.datetime.now())))
    conn.commit()
    conn.close()

    try:
        bot.send_document(message.chat.id, vpn['file_id'],
                          caption=f'🛡️ فایل VPN: {vpn["name"]}\n\nبا NPV Tunnel باز کن.')
        log_event('vpn_given', uid, 0, f'vpn {vpn["name"]} sent')
    except:
        bot.reply_to(message, '❌ خطا در ارسال فایل. دوباره امتحان کن.')

# ─── group management ─────────────────────────────────────────────────────────

@bot.message_handler(commands=['warn'])
def cmd_warn(message):
    if message.chat.type not in ['group', 'supergroup']: return
    if not is_group_admin(message):
        bot.reply_to(message, '❌ فقط ادمین‌ها میتونن اخطار بدن.')
        return
    if not message.reply_to_message:
        bot.reply_to(message, '↩️ روی پیام کاربر ریپلای کن.')
        return

    target = message.reply_to_message.from_user
    parts = message.text.split(' ', 1)
    reason = parts[1] if len(parts) > 1 else 'بدون دلیل'

    conn = db()
    conn.execute('INSERT INTO warns (user_id, group_id, reason, warned_at) VALUES (?,?,?,?)',
                 (target.id, message.chat.id, reason, str(datetime.datetime.now())))

    warn_count = conn.execute('SELECT COUNT(*) as c FROM warns WHERE user_id=? AND group_id=?',
                               (target.id, message.chat.id)).fetchone()['c']

    group = conn.execute('SELECT warn_limit FROM groups WHERE id=?',
                          (message.chat.id,)).fetchone()
    limit = group['warn_limit'] if group else 3
    conn.commit()
    conn.close()

    save_group(message.chat)

    bot.reply_to(message,
        f'⚠️ اخطار به {target.first_name}\n'
        f'دلیل: {reason}\n'
        f'اخطارها: {warn_count}/{limit}')

    if warn_count >= limit:
        try:
            bot.kick_chat_member(message.chat.id, target.id)
            bot.send_message(message.chat.id,
                f'🚫 {target.first_name} به دلیل {warn_count} اخطار اخراج شد.')
        except:
            bot.send_message(message.chat.id, '❌ نتونستم اخراج کنم. مطمئن شو ربات ادمینه.')

@bot.message_handler(commands=['warns'])
def cmd_warns(message):
    if message.chat.type not in ['group', 'supergroup']: return
    if not message.reply_to_message:
        bot.reply_to(message, '↩️ روی پیام کاربر ریپلای کن.')
        return
    target = message.reply_to_message.from_user
    conn = db()
    count = conn.execute('SELECT COUNT(*) as c FROM warns WHERE user_id=? AND group_id=?',
                          (target.id, message.chat.id)).fetchone()['c']
    conn.close()
    bot.reply_to(message, f'📋 {target.first_name}: {count} اخطار')

@bot.message_handler(commands=['clearwarns'])
def cmd_clearwarns(message):
    if message.chat.type not in ['group', 'supergroup']: return
    if not is_group_admin(message):
        bot.reply_to(message, '❌ فقط ادمین‌ها.')
        return
    if not message.reply_to_message:
        bot.reply_to(message, '↩️ روی پیام کاربر ریپلای کن.')
        return
    target = message.reply_to_message.from_user
    conn = db()
    conn.execute('DELETE FROM warns WHERE user_id=? AND group_id=?',
                 (target.id, message.chat.id))
    conn.commit()
    conn.close()
    bot.reply_to(message, f'✅ اخطارهای {target.first_name} پاک شد.')

@bot.message_handler(commands=['kick'])
def cmd_kick(message):
    if message.chat.type not in ['group', 'supergroup']: return
    if not is_group_admin(message):
        bot.reply_to(message, '❌ فقط ادمین‌ها.')
        return
    if not message.reply_to_message:
        bot.reply_to(message, '↩️ روی پیام کاربر ریپلای کن.')
        return
    target = message.reply_to_message.from_user
    try:
        bot.kick_chat_member(message.chat.id, target.id)
        bot.unban_chat_member(message.chat.id, target.id)
        bot.reply_to(message, f'👢 {target.first_name} اخراج شد.')
    except:
        bot.reply_to(message, '❌ نتونستم اخراج کنم.')

@bot.message_handler(commands=['ban'])
def cmd_ban(message):
    if message.chat.type not in ['group', 'supergroup']: return
    if not is_group_admin(message):
        bot.reply_to(message, '❌ فقط ادمین‌ها.')
        return
    if not message.reply_to_message:
        bot.reply_to(message, '↩️ روی پیام کاربر ریپلای کن.')
        return
    target = message.reply_to_message.from_user
    try:
        bot.kick_chat_member(message.chat.id, target.id)
        bot.reply_to(message, f'🚫 {target.first_name} بن شد.')
        log_event('ban', target.id, message.chat.id, 'banned')
    except:
        bot.reply_to(message, '❌ نتونستم بن کنم.')

@bot.message_handler(commands=['unban'])
def cmd_unban(message):
    if message.chat.type not in ['group', 'supergroup']: return
    if not is_group_admin(message):
        bot.reply_to(message, '❌ فقط ادمین‌ها.')
        return
    if not message.reply_to_message:
        bot.reply_to(message, '↩️ روی پیام کاربر ریپلای کن.')
        return
    target = message.reply_to_message.from_user
    try:
        bot.unban_chat_member(message.chat.id, target.id)
        bot.reply_to(message, f'✅ بن {target.first_name} برداشته شد.')
    except:
        bot.reply_to(message, '❌ خطا.')

@bot.message_handler(commands=['mute'])
def cmd_mute(message):
    if message.chat.type not in ['group', 'supergroup']: return
    if not is_group_admin(message):
        bot.reply_to(message, '❌ فقط ادمین‌ها.')
        return
    if not message.reply_to_message:
        bot.reply_to(message, '↩️ روی پیام کاربر ریپلای کن.')
        return

    parts = message.text.split(' ', 1)
    minutes = 10
    try:
        minutes = int(parts[1]) if len(parts) > 1 else 10
    except:
        pass

    target = message.reply_to_message.from_user
    until = int(time.time()) + (minutes * 60)

    try:
        from telebot.types import ChatPermissions
        bot.restrict_chat_member(message.chat.id, target.id,
                                  permissions=ChatPermissions(can_send_messages=False),
                                  until_date=until)
        bot.reply_to(message, f'🔇 {target.first_name} برای {minutes} دقیقه میوت شد.')
    except:
        bot.reply_to(message, '❌ نتونستم میوت کنم.')

# ─── admin panel ──────────────────────────────────────────────────────────────

@bot.message_handler(commands=['panel'])
def cmd_panel(message):
    if message.from_user.id != ADMIN_ID: return
    conn = db()
    users = conn.execute('SELECT COUNT(*) as c FROM users').fetchone()['c']
    groups = conn.execute('SELECT COUNT(*) as c FROM groups').fetchone()['c']
    configs_left = conn.execute('SELECT COUNT(*) as c FROM configs WHERE is_used=0').fetchone()['c']
    vpns_left = conn.execute('SELECT COUNT(*) as c FROM vpn_files WHERE is_used=0').fetchone()['c']
    conn.close()

    text = (
        f'⚙️ پنل ادمین SFOR\n\n'
        f'👥 کاربران: {users}\n'
        f'💬 گروه‌ها: {groups}\n'
        f'🔒 کانفیگ باقیمانده: {configs_left}\n'
        f'🛡️ VPN باقیمانده: {vpns_left}\n\n'
        f'دستورات ادمین:\n'
        f'/broadcast [پیام] — پیام همگانی\n'
        f'/addvpn — افزودن فایل VPN (ریپلای به فایل)\n'
    )
    bot.reply_to(message, text)

@bot.message_handler(commands=['broadcast'])
def cmd_broadcast(message):
    if message.from_user.id != ADMIN_ID: return
    parts = message.text.split(' ', 1)
    if len(parts) < 2:
        bot.reply_to(message, '❌ پیام رو بنویس.')
        return
    text = parts[1]
    conn = db()
    users = conn.execute('SELECT id FROM users WHERE is_banned=0').fetchall()
    conn.close()

    sent = 0
    for u in users:
        try:
            bot.send_message(u['id'], f'📢 پیام SFOR:\n\n{text}')
            sent += 1
            time.sleep(0.05)
        except:
            pass

    bot.reply_to(message, f'✅ پیام به {sent} نفر ارسال شد.')

@bot.message_handler(commands=['addvpn'], content_types=['text'])
def cmd_addvpn_hint(message):
    if message.from_user.id != ADMIN_ID: return
    bot.reply_to(message, '📎 روی فایل .npvt ریپلای کن و /addvpn بنویس.')

@bot.message_handler(commands=['addvpn'], content_types=['document'])
def cmd_addvpn(message):
    if message.from_user.id != ADMIN_ID: return
    if not message.reply_to_message or not message.reply_to_message.document:
        bot.reply_to(message, '↩️ روی فایل ریپلای کن.')
        return
    doc = message.reply_to_message.document
    conn = db()
    conn.execute('INSERT INTO vpn_files (name, file_id, created_at) VALUES (?,?,?)',
                 (doc.file_name, doc.file_id, str(datetime.datetime.now())))
    conn.commit()
    conn.close()
    bot.reply_to(message, f'✅ فایل {doc.file_name} اضافه شد.')

# ─── anti-spam & anti-link ────────────────────────────────────────────────────

import re

LINK_PATTERN = re.compile(r'(https?://|t\.me/|@\w{5,})', re.IGNORECASE)

@bot.message_handler(func=lambda m: m.chat.type in ['group', 'supergroup'])
def group_filter(message):
    if not message.from_user: return
    save_user(message.from_user)
    save_group(message.chat)

    # check anti-link
    conn = db()
    group = conn.execute('SELECT * FROM groups WHERE id=?', (message.chat.id,)).fetchone()
    conn.close()

    if not group: return

    # anti link
    if group['anti_link'] and message.text:
        if LINK_PATTERN.search(message.text):
            try:
                is_admin = is_group_admin(message)
                if not is_admin:
                    bot.delete_message(message.chat.id, message.message_id)
                    bot.send_message(message.chat.id,
                        f'🚫 {message.from_user.first_name}، ارسال لینک ممنوعه!')
                    return
            except:
                pass

    # anti spam
    if group['anti_spam']:
        now = time.time()
        conn = db()
        row = conn.execute('SELECT count, last_time FROM spam_track WHERE user_id=? AND group_id=?',
                            (message.from_user.id, message.chat.id)).fetchone()

        if row:
            elapsed = now - float(row['last_time'] or 0)
            count = row['count'] + 1 if elapsed < 5 else 1
            conn.execute('UPDATE spam_track SET count=?, last_time=? WHERE user_id=? AND group_id=?',
                         (count, now, message.from_user.id, message.chat.id))
        else:
            count = 1
            conn.execute('INSERT INTO spam_track (user_id, group_id, count, last_time) VALUES (?,?,?,?)',
                         (message.from_user.id, message.chat.id, 1, now))

        conn.commit()
        conn.close()

        if count >= 8:
            try:
                from telebot.types import ChatPermissions
                bot.restrict_chat_member(message.chat.id, message.from_user.id,
                                          permissions=ChatPermissions(can_send_messages=False),
                                          until_date=int(now) + 300)
                bot.send_message(message.chat.id,
                    f'🔇 {message.from_user.first_name} به خاطر اسپم ۵ دقیقه میوت شد.')
            except:
                pass
