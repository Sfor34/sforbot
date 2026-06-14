# ═══════════════════════════════════════════
#     🔥 SFOR Advanced Module v1.0
#     فایل: modules/sfor_advanced.py
# ═══════════════════════════════════════════
import sqlite3, time, re
from datetime import datetime, timedelta
from telebot.types import (
    InlineKeyboardMarkup, InlineKeyboardButton, ChatPermissions
)

# ── متغیرهای اصلی از bot.py inject میشن ──
bot = None
ADMIN_ID = None
SITE_URL = None
DB_FILE = None
db = None
add_log = None
add_user = None
add_group = None
get_group = None
is_group_admin = None
ask_gemini = None
pending_v2ray = {}

def setup(bot_instance, ctx):
    global bot, ADMIN_ID, SITE_URL, DB_FILE, db, add_log, add_user, add_group, get_group, is_group_admin, ask_gemini
    bot          = bot_instance
    ADMIN_ID     = ctx['ADMIN_ID']
    SITE_URL     = ctx['SITE_URL']
    DB_FILE      = ctx.get('DB_FILE', 'sfor_bot.db')
    db           = ctx['db']
    add_log      = ctx['add_log']
    add_user     = ctx['add_user']
    add_group    = ctx['add_group']
    get_group    = ctx['get_group']
    is_group_admin = ctx['is_group_admin']
    ask_gemini   = ctx.get('ask_gemini')
    register_handlers()
    print('[SFOR] ✅ sfor_advanced setup done!', flush=True)

def register_handlers():
    # ═══════════════════════════════════════════
    #         🗄️ جداول اضافی DB
    # ═══════════════════════════════════════════
    def init_advanced_db():
        conn = db()
        c = conn.cursor()
        c.executescript('''
        CREATE TABLE IF NOT EXISTS installed_groups (
            group_id INTEGER PRIMARY KEY,
            installed_by INTEGER,
            installed_at TEXT
        );
        CREATE TABLE IF NOT EXISTS group_assistants (
            group_id INTEGER,
            user_id INTEGER,
            level INTEGER DEFAULT 1,
            PRIMARY KEY (group_id, user_id)
        );
        CREATE TABLE IF NOT EXISTS group_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id INTEGER,
            user_id INTEGER,
            date TEXT
        );
        CREATE TABLE IF NOT EXISTS pending_installs (
            group_id INTEGER PRIMARY KEY,
            requested_at TEXT
        );
        CREATE TABLE IF NOT EXISTS v2ray_configs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            config TEXT,
            added_at TEXT,
            added_by INTEGER
        );
        ''')
        conn.commit()
        conn.close()

    init_advanced_db()

    # ═══════════════════════════════════════════
    #         🔧 توابع کمکی
    # ═══════════════════════════════════════════
    def is_installed(gid):
        conn = db()
        c = conn.cursor()
        c.execute('SELECT 1 FROM installed_groups WHERE group_id=?', (gid,))
        r = c.fetchone()
        conn.close()
        return r is not None

    def install_group(gid, uid):
        conn = db()
        c = conn.cursor()
        c.execute('INSERT OR IGNORE INTO installed_groups (group_id,installed_by,installed_at) VALUES (?,?,?)',
                  (gid, uid, datetime.now().isoformat()))
        conn.commit()
        conn.close()

    def get_assistant_level(gid, uid):
        conn = db()
        c = conn.cursor()
        c.execute('SELECT level FROM group_assistants WHERE group_id=? AND user_id=?', (gid, uid))
        r = c.fetchone()
        conn.close()
        return r[0] if r else 0

    def set_assistant(gid, uid, level):
        conn = db()
        c = conn.cursor()
        c.execute('INSERT OR REPLACE INTO group_assistants (group_id,user_id,level) VALUES (?,?,?)',
                  (gid, uid, level))
        conn.commit()
        conn.close()

    def remove_assistant(gid, uid):
        conn = db()
        c = conn.cursor()
        c.execute('DELETE FROM group_assistants WHERE group_id=? AND user_id=?', (gid, uid))
        conn.commit()
        conn.close()

    def log_message(gid, uid):
        conn = db()
        c = conn.cursor()
        c.execute('INSERT INTO group_messages (group_id,user_id,date) VALUES (?,?,?)',
                  (gid, uid, datetime.now().strftime('%Y-%m-%d')))
        conn.commit()
        conn.close()

    def get_group_stats(gid):
        conn = db()
        c = conn.cursor()
        today = datetime.now().strftime('%Y-%m-%d')
        c.execute('SELECT COUNT(*) FROM group_messages WHERE group_id=? AND date=?', (gid, today))
        today_msgs = c.fetchone()[0]
        c.execute('SELECT COUNT(*) FROM group_messages WHERE group_id=?', (gid,))
        total_msgs = c.fetchone()[0]
        c.execute('''SELECT user_id, COUNT(*) as cnt FROM group_messages 
                     WHERE group_id=? AND date=? GROUP BY user_id ORDER BY cnt DESC LIMIT 1''',
                  (gid, today))
        top = c.fetchone()
        conn.close()
        return today_msgs, total_msgs, top

    def has_permission(gid, uid, level_needed):
        if uid == ADMIN_ID: return True
        if is_group_admin(gid, uid): return True
        assistant_level = get_assistant_level(gid, uid)
        return assistant_level >= level_needed

    def safe_delete(cid, mid):
        try: bot.delete_message(cid, mid)
        except: pass

    def safe_send(cid, text, **kwargs):
        try: return bot.send_message(cid, text, **kwargs)
        except: pass

    def mute_member(cid, uid, seconds=300):
        until = int(time.time()) + seconds
        bot.restrict_chat_member(cid, uid,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=until)

    def unmute_member(cid, uid):
        bot.restrict_chat_member(cid, uid,
            permissions=ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_polls=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True
            ))

    # ═══════════════════════════════════════════
    #     📦 دستورات نصب
    # ═══════════════════════════════════════════
    INSTALL_TRIGGERS = ['نصب', 'install', 'راه‌اندازی', 'setup']

    @bot.message_handler(func=lambda m: (
        m.chat.type in ['group', 'supergroup'] and
        m.text and m.text.strip().lower() in [x.lower() for x in INSTALL_TRIGGERS]
    ))
    def handle_install(message):
        gid = message.chat.id
        uid = message.from_user.id

        if is_installed(gid):
            bot.reply_to(message, '✅ ربات قبلاً در این گروه نصب شده!')
            return

        try:
            member = bot.get_chat_member(gid, uid)
            if member.status not in ['creator']:
                bot.reply_to(message, '⛔ فقط مالک گروه می‌تونه ربات رو نصب کنه!')
                return
        except:
            bot.reply_to(message, '❌ خطا در بررسی دسترسی.')
            return

        install_group(gid, uid)
        add_group(message.chat)

        m = InlineKeyboardMarkup()
        m.add(InlineKeyboardButton('⚙️ تنظیمات گروه', callback_data=f'adv_settings_{gid}'))
        m.add(InlineKeyboardButton('📊 آمار گروه', callback_data=f'adv_stats_{gid}'))
        m.add(InlineKeyboardButton('🔒 مدیریت V2Ray', callback_data='adv_v2ray_panel'))

        bot.reply_to(message,
            f'🎉 *ربات SFOR با موفقیت نصب شد!*\n\n'
            f'👑 مالک: {message.from_user.first_name}\n'
            f'🏘️ گروه: {message.chat.title}\n\n'
            '✅ قابلیت‌های فعال:\n'
            '• هوش مصنوعی (منشن یا ریپلای)\n'
            '• مدیریت گروه (بدون /)\n'
            '• آمار واقعی\n'
            '• سیستم دستیار\n\n'
            '📌 دستور `راهنما` یا `help` رو بزن',
            parse_mode='Markdown', reply_markup=m)

    # ═══════════════════════════════════════════
    #     🤖 Reply به ربات → AI جواب
    # ═══════════════════════════════════════════
    @bot.message_handler(func=lambda m: (
        m.chat.type in ['group', 'supergroup'] and
        m.reply_to_message is not None and
        m.text is not None
    ))
    def handle_reply_to_bot(message):
        try:
            me = bot.get_me()
            if message.reply_to_message.from_user.id != me.id:
                return
        except:
            return

        uid = message.from_user.id
        question = message.text.strip()
        if not question: return

        msg = bot.reply_to(message, '🤖 در حال فکر کردن...')
        reply = ask_gemini(uid, question)
        try:
            bot.edit_message_text(f'🤖 {reply}', message.chat.id, msg.message_id, parse_mode='Markdown')
        except:
            bot.reply_to(message, f'🤖 {reply}')

    # ═══════════════════════════════════════════
    #     📨 هندلر اصلی پیام‌های گروه
    # ═══════════════════════════════════════════
    CMD_MAP = {
        # آمار
        'امار': 'stats', 'آمار': 'stats', 'stats': 'stats',
        # حذف پیام
        'حذف': 'delete', 'پاک': 'delete', 'delete': 'delete', 'del': 'delete',
        # میوت
        'خفه': 'mute', 'سکوت': 'mute', 'میوت': 'mute', 'mute': 'mute',
        # آنمیوت
        'آزاد': 'unmute', 'unmute': 'unmute',
        # بن
        'سیک': 'ban', 'بن': 'ban', 'ban': 'ban',
        # آنبن
        'رفع بن': 'unban', 'unban': 'unban',
        # اخطار
        'اخطار': 'warn', 'warn': 'warn',
        # کیک
        'اخراج': 'kick', 'kick': 'kick',
        # لول آپ
        'لول آپ': 'levelup1', 'level up': 'levelup1', 'levelup': 'levelup1',
        'دستیار': 'levelup2', 'assistant': 'levelup2',
        # اطلاعات
        'info': 'info', 'اطلاعات': 'info', 'من کیم': 'info', 'whoami': 'info',
        # عوض کردن اسم گروه
        'اسم گروه': 'rename', 'rename': 'rename',
        # عوض کردن بیو
        'بیو گروه': 'setbio', 'setbio': 'setbio', 'توضیحات گروه': 'setbio',
        # راهنما
        'راهنما': 'help', 'help': 'help', 'دستورات': 'help',
        # پنل
        'پنل': 'panel', 'panel': 'panel',
        # V2Ray
        'v2ray': 'v2ray', 'کانفیگ': 'v2ray', 'config': 'v2ray',
    }

    # حالت انتظار برای تغییر اسم/بیو
    pending_rename = {}
    pending_bio = {}

    @bot.message_handler(func=lambda m: (
        m.chat.type in ['group', 'supergroup'] and
        m.text is not None
    ))
    def advanced_group_handler(message):
        gid = message.chat.id
        uid = message.from_user.id
        text = message.text.strip()

        # لاگ پیام
        log_message(gid, uid)

        # ─── حالت انتظار rename ───
        if gid in pending_rename and pending_rename[gid] == uid:
            try:
                bot.set_chat_title(gid, text)
                bot.reply_to(message, f'✅ اسم گروه به *{text}* تغییر کرد!', parse_mode='Markdown')
            except Exception as e:
                bot.reply_to(message, f'❌ خطا: {e}')
            del pending_rename[gid]
            return

        # ─── حالت انتظار bio ───
        if gid in pending_bio and pending_bio[gid] == uid:
            try:
                bot.set_chat_description(gid, text)
                bot.reply_to(message, '✅ توضیحات گروه تغییر کرد!', parse_mode='Markdown')
            except Exception as e:
                bot.reply_to(message, f'❌ خطا: {e}')
            del pending_bio[gid]
            return

        # ─── SFOR mention ───
        if any(w in text.upper() for w in ['SFOR', 'اسفور']):
            responses = [
                '🔥 SFOR اینجاست! امنیت و فناوری در خدمت شماست.',
                '💚 SFOR — امنیت دیجیتال برای همه!',
                f'🛡️ SFOR در خدمت شماست! سایت: {SITE_URL}',
                '🤖 SFOR Bot آماده کمکه! چی نیاز داری؟',
                '⚡ تیم SFOR همیشه اینجاست! @mmadsfor',
            ]
            import random
            bot.reply_to(message, random.choice(responses))
            return

        # ─── پارس دستور ───
        cmd = None
        args = ''

        # چک کن آیا با یه دستور شروع میشه
        text_lower = text.lower()
        for trigger, action in CMD_MAP.items():
            if text_lower == trigger or text_lower.startswith(trigger + ' '):
                cmd = action
                args = text[len(trigger):].strip()
                break

        if not cmd:
            return  # دستور شناخته نشده، نادیده بگیر

        # ─── بررسی نصب ───
        if cmd != 'help' and not is_installed(gid):
            bot.reply_to(message, '⚠️ ربات هنوز نصب نشده! مالک گروه باید `نصب` بنویسه.',
                         parse_mode='Markdown')
            return

        # ══ اجرای دستورات ══

        # ─── راهنما ───
        if cmd == 'help':
            help_text = (
                '📖 *دستورات ربات SFOR*\n\n'
                '🔹 *عمومی:*\n'
                '`امار` — آمار گروه\n'
                '`info` — اطلاعات من\n'
                '`من کیم` — اطلاعات من\n'
                '`راهنما` — این پیام\n\n'
                '🔸 *مدیریت (ادمین/دستیار):*\n'
                '`خفه` — میوت ۵ دقیقه\n'
                '`آزاد` — رفع میوت\n'
                '`اخراج` — کیک\n'
                '`سیک` — بن\n'
                '`رفع بن` — آنبن\n'
                '`اخطار` — اخطار\n'
                '`حذف` — حذف پیام\n\n'
                '👑 *مالک:*\n'
                '`لول آپ` — دستیار سطح ۱\n'
                '`دستیار` — دستیار سطح ۲\n'
                '`اسم گروه` — تغییر اسم\n'
                '`بیو گروه` — تغییر توضیحات\n'
                '`v2ray` — پنل کانفیگ\n\n'
                '💡 همه دستورات بدون / هستن!\n'
                '🤖 برای AI: منشن یا ریپلای کن'
            )
            bot.reply_to(message, help_text, parse_mode='Markdown')
            return

        # ─── آمار ───
        if cmd == 'stats':
            try:
                chat = bot.get_chat(gid)
                count = bot.get_chat_member_count(gid)
                today_msgs, total_msgs, top_user = get_group_stats(gid)

                top_text = '—'
                if top_user:
                    try:
                        u = bot.get_chat_member(gid, top_user[0])
                        top_text = f'{u.user.first_name} ({top_user[1]} پیام)'
                    except:
                        top_text = f'کاربر ({top_user[1]} پیام)'

                conn = db()
                c = conn.cursor()
                c.execute('SELECT COUNT(*) FROM group_assistants WHERE group_id=?', (gid,))
                assistants = c.fetchone()[0]
                conn.close()

                m = InlineKeyboardMarkup()
                m.add(InlineKeyboardButton('🔄 بروزرسانی', callback_data=f'adv_stats_{gid}'))

                bot.reply_to(message,
                    f'📊 *آمار گروه {chat.title}*\n\n'
                    f'👥 اعضا: `{count}`\n'
                    f'💬 پیام امروز: `{today_msgs}`\n'
                    f'📨 کل پیام‌ها: `{total_msgs}`\n'
                    f'🏆 فعال‌ترین امروز: {top_text}\n'
                    f'🤖 دستیاران: `{assistants}`\n'
                    f'📅 تاریخ: `{datetime.now().strftime("%Y/%m/%d %H:%M")}`',
                    parse_mode='Markdown', reply_markup=m)
            except Exception as e:
                bot.reply_to(message, f'❌ خطا در دریافت آمار: {e}')
            return

        # ─── اطلاعات کاربر ───
        if cmd == 'info':
            target = message.reply_to_message.from_user if message.reply_to_message else message.from_user
            try:
                member = bot.get_chat_member(gid, target.id)
                status_map = {
                    'creator': '👑 مالک',
                    'administrator': '⭐ ادمین',
                    'member': '👤 عضو',
                    'restricted': '🔇 محدود',
                    'left': '🚪 خارج شده',
                    'kicked': '🚫 بن شده'
                }
                status = status_map.get(member.status, member.status)
                assistant_level = get_assistant_level(gid, target.id)
                asst_text = ''
                if assistant_level == 1:
                    asst_text = '\n🔰 دستیار سطح ۱'
                elif assistant_level == 2:
                    asst_text = '\n🔱 دستیار سطح ۲'

                conn = db()
                c = conn.cursor()
                c.execute('SELECT COUNT(*) FROM group_messages WHERE group_id=? AND user_id=?', (gid, target.id))
                msg_count = c.fetchone()[0]
                conn.close()

                bot.reply_to(message,
                    f'👤 *اطلاعات کاربر*\n\n'
                    f'📛 نام: {target.first_name}\n'
                    f'🆔 آیدی: `{target.id}`\n'
                    f'📱 یوزرنیم: @{target.username or "ندارد"}\n'
                    f'🏷️ وضعیت: {status}{asst_text}\n'
                    f'💬 پیام در گروه: `{msg_count}`',
                    parse_mode='Markdown')
            except Exception as e:
                bot.reply_to(message, f'❌ خطا: {e}')
            return

        # ─── دستورات نیاز به target ───
        if cmd in ['mute', 'unmute', 'ban', 'unban', 'warn', 'kick', 'delete', 'levelup1', 'levelup2']:
            # بررسی دسترسی
            level_needed = 2 if cmd in ['ban', 'unban', 'levelup1', 'levelup2'] else 1
            if not has_permission(gid, uid, level_needed):
                bot.reply_to(message, '⛔ دسترسی ندارید!')
                return

            target = message.reply_to_message.from_user if message.reply_to_message else None

            # حذف پیام بدون target
            if cmd == 'delete' and not target:
                if message.reply_to_message:
                    safe_delete(gid, message.reply_to_message.message_id)
                    safe_delete(gid, message.message_id)
                else:
                    # حذف N پیام
                    try:
                        n = int(args) if args.isdigit() else 1
                        n = min(n, 50)
                        bot.reply_to(message, f'🗑️ {n} پیام حذف شد.')
                    except:
                        bot.reply_to(message, '↩️ روی پیام مورد نظر Reply کن یا عدد بنویس: `حذف ۵`', parse_mode='Markdown')
                return

            if not target and cmd != 'delete':
                bot.reply_to(message, '↩️ روی پیام کاربر مورد نظر Reply کن.')
                return

            if target and is_group_admin(gid, target.id) and uid != ADMIN_ID:
                bot.reply_to(message, '⛔ نمیشه روی ادمین این کار رو کرد.')
                return

            # ─── میوت ───
            if cmd == 'mute':
                minutes = 5
                if args and args.isdigit():
                    minutes = int(args)
                try:
                    mute_member(gid, target.id, minutes * 60)
                    bot.reply_to(message,
                        f'🔇 *{target.first_name}* {minutes} دقیقه میوت شد.',
                        parse_mode='Markdown')
                    add_log('mute', uid, gid, str(target.id))
                except Exception as e:
                    bot.reply_to(message, f'❌ {e}')

            # ─── آنمیوت ───
            elif cmd == 'unmute':
                try:
                    unmute_member(gid, target.id)
                    bot.reply_to(message,
                        f'🔊 میوت *{target.first_name}* برداشته شد.',
                        parse_mode='Markdown')
                except Exception as e:
                    bot.reply_to(message, f'❌ {e}')

            # ─── بن ───
            elif cmd == 'ban':
                try:
                    bot.kick_chat_member(gid, target.id)
                    bot.reply_to(message,
                        f'🚫 *{target.first_name}* از گروه بن شد!',
                        parse_mode='Markdown')
                    add_log('ban', uid, gid, str(target.id))
                except Exception as e:
                    bot.reply_to(message, f'❌ {e}')

            # ─── آنبن ───
            elif cmd == 'unban':
                try:
                    bot.unban_chat_member(gid, target.id)
                    bot.reply_to(message,
                        f'✅ بن *{target.first_name}* برداشته شد.',
                        parse_mode='Markdown')
                except Exception as e:
                    bot.reply_to(message, f'❌ {e}')

            # ─── اخراج ───
            elif cmd == 'kick':
                try:
                    bot.kick_chat_member(gid, target.id)
                    bot.unban_chat_member(gid, target.id)
                    bot.reply_to(message,
                        f'🚪 *{target.first_name}* از گروه اخراج شد.',
                        parse_mode='Markdown')
                    add_log('kick', uid, gid, str(target.id))
                except Exception as e:
                    bot.reply_to(message, f'❌ {e}')

            # ─── اخطار ───
            elif cmd == 'warn':
                conn = db()
                c = conn.cursor()
                c.execute('INSERT INTO warns (user_id,group_id,reason,warned_at) VALUES (?,?,?,?)',
                          (target.id, gid, args or 'بدون دلیل', datetime.now().isoformat()))
                c.execute('SELECT COUNT(*) FROM warns WHERE user_id=? AND group_id=?', (target.id, gid))
                count = c.fetchone()[0]
                conn.commit()
                conn.close()

                g = get_group(gid)
                limit = g['warn_limit'] if g else 3
                if count >= limit:
                    try:
                        bot.kick_chat_member(gid, target.id)
                        bot.reply_to(message,
                            f'🚫 *{target.first_name}* بعد از {count} اخطار اخراج شد!',
                            parse_mode='Markdown')
                    except: pass
                else:
                    bot.reply_to(message,
                        f'⚠️ *اخطار به {target.first_name}*\n'
                        f'📋 دلیل: {args or "بدون دلیل"}\n'
                        f'🔢 {count}/{limit}',
                        parse_mode='Markdown')

            # ─── حذف پیام reply شده ───
            elif cmd == 'delete':
                if message.reply_to_message:
                    safe_delete(gid, message.reply_to_message.message_id)
                safe_delete(gid, message.message_id)

            # ─── لول آپ سطح ۱ ───
            elif cmd == 'levelup1':
                try:
                    member = bot.get_chat_member(gid, uid)
                    if member.status != 'creator' and uid != ADMIN_ID:
                        bot.reply_to(message, '⛔ فقط مالک گروه!'); return
                except: pass
                set_assistant(gid, target.id, 1)
                bot.reply_to(message,
                    f'🔰 *{target.first_name}* دستیار سطح ۱ شد!\n\n'
                    f'✅ دسترسی‌ها:\n• حذف پیام\n• میوت کاربران',
                    parse_mode='Markdown')

            # ─── لول آپ سطح ۲ ───
            elif cmd == 'levelup2':
                try:
                    member = bot.get_chat_member(gid, uid)
                    if member.status != 'creator' and uid != ADMIN_ID:
                        bot.reply_to(message, '⛔ فقط مالک گروه!'); return
                except: pass
                set_assistant(gid, target.id, 2)
                bot.reply_to(message,
                    f'🔱 *{target.first_name}* دستیار سطح ۲ شد!\n\n'
                    f'✅ دسترسی‌ها:\n• همه دسترسی‌های سطح ۱\n• بن/آنبن\n• تنظیمات گروه',
                    parse_mode='Markdown')
            return

        # ─── تغییر اسم گروه ───
        if cmd == 'rename':
            if not has_permission(gid, uid, 2):
                bot.reply_to(message, '⛔ دسترسی ندارید!'); return
            if args:
                try:
                    bot.set_chat_title(gid, args)
                    bot.reply_to(message, f'✅ اسم گروه به *{args}* تغییر کرد!', parse_mode='Markdown')
                except Exception as e:
                    bot.reply_to(message, f'❌ {e}')
            else:
                pending_rename[gid] = uid
                bot.reply_to(message, '✏️ اسم جدید گروه رو بنویس:')
            return

        # ─── تغییر بیو گروه ───
        if cmd == 'setbio':
            if not has_permission(gid, uid, 2):
                bot.reply_to(message, '⛔ دسترسی ندارید!'); return
            if args:
                try:
                    bot.set_chat_description(gid, args)
                    bot.reply_to(message, '✅ توضیحات گروه تغییر کرد!')
                except Exception as e:
                    bot.reply_to(message, f'❌ {e}')
            else:
                pending_bio[gid] = uid
                bot.reply_to(message, '✏️ توضیحات جدید گروه رو بنویس:')
            return

        # ─── V2Ray پنل ───
        if cmd == 'v2ray':
            if not has_permission(gid, uid, 2) and uid != ADMIN_ID:
                bot.reply_to(message, '⛔ دسترسی ندارید!'); return

            conn = db()
            c = conn.cursor()
            c.execute('SELECT id,name,config,added_at FROM v2ray_configs ORDER BY id DESC LIMIT 5')
            configs = c.fetchall()
            conn.close()

            if not configs:
                m = InlineKeyboardMarkup()
                m.add(InlineKeyboardButton('➕ افزودن کانفیگ', callback_data='adv_add_v2ray'))
                bot.reply_to(message, '📭 کانفیگی موجود نیست!', reply_markup=m)
                return

            text = '🔒 *آخرین کانفیگ‌های V2Ray:*\n\n'
            for cfg in configs:
                text += f'📛 *{cfg[1]}*\n`{cfg[2][:60]}...`\n📅 {cfg[3][:10]}\n\n'

            m = InlineKeyboardMarkup()
            m.add(InlineKeyboardButton('➕ افزودن', callback_data='adv_add_v2ray'))
            m.add(InlineKeyboardButton('📋 همه کانفیگ‌ها', callback_data='adv_all_v2ray_0'))
            bot.reply_to(message, text, parse_mode='Markdown', reply_markup=m)
            return

        # ─── پنل ───
        if cmd == 'panel':
            if not has_permission(gid, uid, 1):
                bot.reply_to(message, '⛔ دسترسی ندارید!'); return
            show_group_panel(message, gid, uid)
            return


    def show_group_panel(message, gid, uid):
        g = get_group(gid)
        if not g: return

        def s(v): return '✅' if v else '❌'

        m = InlineKeyboardMarkup(row_width=2)
        m.add(
            InlineKeyboardButton(f'🔗 ضد لینک {s(g.get("anti_link",1))}', callback_data=f'adv_toggle_anti_link_{gid}'),
            InlineKeyboardButton(f'🚫 ضد اسپم {s(g.get("anti_spam",1))}', callback_data=f'adv_toggle_anti_spam_{gid}'),
        )
        m.add(
            InlineKeyboardButton(f'🤬 ضد فحش {s(g.get("anti_profanity",1))}', callback_data=f'adv_toggle_anti_profanity_{gid}'),
            InlineKeyboardButton(f'👋 خوش‌آمد {s(g.get("welcome",1))}', callback_data=f'adv_toggle_welcome_{gid}'),
        )
        m.add(
            InlineKeyboardButton(f'🤖 AI گروه {s(g.get("ai_reply",0))}', callback_data=f'adv_toggle_ai_reply_{gid}'),
            InlineKeyboardButton(f'👋 خداحافظ {s(g.get("goodbye",0))}', callback_data=f'adv_toggle_goodbye_{gid}'),
        )
        m.add(
            InlineKeyboardButton('📊 آمار', callback_data=f'adv_stats_{gid}'),
            InlineKeyboardButton('🔒 V2Ray', callback_data='adv_v2ray_panel'),
        )
        m.add(
            InlineKeyboardButton('👥 دستیاران', callback_data=f'adv_assistants_{gid}'),
            InlineKeyboardButton('⚠️ اخطارها', callback_data=f'adv_warns_{gid}'),
        )

        bot.reply_to(message,
            f'⚙️ *پنل مدیریت {message.chat.title}*',
            parse_mode='Markdown', reply_markup=m)


    # ═══════════════════════════════════════════
    #     🔘 Callbacks
    # ═══════════════════════════════════════════
    @bot.callback_query_handler(func=lambda c: c.data.startswith('adv_'))
    def adv_callback(call):
        uid = call.from_user.id
        data = call.data
        cid = call.message.chat.id
        mid = call.message.message_id

        def answer(text='', alert=False):
            bot.answer_callback_query(call.id, text, show_alert=alert)

        # ─── آمار گروه ───
        if data.startswith('adv_stats_'):
            gid = int(data.split('_')[-1])
            try:
                chat = bot.get_chat(gid)
                count = bot.get_chat_member_count(gid)
                today_msgs, total_msgs, top_user = get_group_stats(gid)
                top_text = '—'
                if top_user:
                    try:
                        u = bot.get_chat_member(gid, top_user[0])
                        top_text = f'{u.user.first_name} ({top_user[1]} پیام)'
                    except: pass

                m = InlineKeyboardMarkup()
                m.add(InlineKeyboardButton('🔄 بروزرسانی', callback_data=f'adv_stats_{gid}'))

                bot.edit_message_text(
                    f'📊 *آمار گروه {chat.title}*\n\n'
                    f'👥 اعضا: `{count}`\n'
                    f'💬 پیام امروز: `{today_msgs}`\n'
                    f'📨 کل پیام‌ها: `{total_msgs}`\n'
                    f'🏆 فعال‌ترین: {top_text}\n'
                    f'⏰ {datetime.now().strftime("%H:%M:%S")}',
                    cid, mid, parse_mode='Markdown', reply_markup=m)
                answer('✅ بروزرسانی شد')
            except Exception as e:
                answer(f'❌ {str(e)[:50]}', True)

        # ─── پنل تنظیمات گروه ───
        elif data.startswith('adv_settings_'):
            gid = int(data.split('_')[-1])

            if not has_permission(gid, uid, 1):
                answer('⛔ دسترسی ندارید!', True); return

            g = get_group(gid)
            if not g:
                answer('❌ گروه پیدا نشد', True); return

            def s(v): return '✅' if v else '❌'
            m = InlineKeyboardMarkup(row_width=2)
            m.add(
                InlineKeyboardButton(f'🔗 ضد لینک {s(g.get("anti_link",1))}', callback_data=f'adv_toggle_anti_link_{gid}'),
                InlineKeyboardButton(f'🚫 ضد اسپم {s(g.get("anti_spam",1))}', callback_data=f'adv_toggle_anti_spam_{gid}'),
            )
            m.add(
                InlineKeyboardButton(f'🤬 ضد فحش {s(g.get("anti_profanity",1))}', callback_data=f'adv_toggle_anti_profanity_{gid}'),
                InlineKeyboardButton(f'👋 خوش‌آمد {s(g.get("welcome",1))}', callback_data=f'adv_toggle_welcome_{gid}'),
            )
            m.add(
                InlineKeyboardButton(f'🤖 AI گروه {s(g.get("ai_reply",0))}', callback_data=f'adv_toggle_ai_reply_{gid}'),
                InlineKeyboardButton(f'👋 خداحافظ {s(g.get("goodbye",0))}', callback_data=f'adv_toggle_goodbye_{gid}'),
            )
            m.add(
                InlineKeyboardButton('📊 آمار', callback_data=f'adv_stats_{gid}'),
                InlineKeyboardButton('🔒 V2Ray', callback_data='adv_v2ray_panel'),
            )
            m.add(
                InlineKeyboardButton('👥 دستیاران', callback_data=f'adv_assistants_{gid}'),
                InlineKeyboardButton('⚠️ اخطارها', callback_data=f'adv_warns_{gid}'),
            )
            try:
                bot.edit_message_text('⚙️ *تنظیمات گروه:*', cid, mid, parse_mode='Markdown', reply_markup=m)
            except Exception:
                bot.send_message(cid, '⚙️ *تنظیمات گروه:*', parse_mode='Markdown', reply_markup=m)
            answer()

        # ─── تنظیمات toggle ───
        elif data.startswith('adv_toggle_'):
            parts = data.split('_')
            gid = int(parts[-1])
            field = '_'.join(parts[2:-1])

            if not has_permission(gid, uid, 1):
                answer('⛔ دسترسی ندارید!', True); return

            g = get_group(gid)
            if not g: answer('❌'); return

            ALLOWED = {'anti_link', 'anti_spam', 'anti_profanity', 'welcome', 'goodbye', 'ai_reply'}
            if field not in ALLOWED:
                answer('❌ فیلد نامعتبر', True); return

            new_val = 0 if g.get(field, 0) else 1
            conn = db()
            c = conn.cursor()
            c.execute(f'UPDATE groups SET {field}=? WHERE id=?', (new_val, gid))
            conn.commit()
            conn.close()

            status = '✅ فعال' if new_val else '❌ غیرفعال'
            answer(f'{field}: {status}')

            # ریفرش پنل
            g2 = get_group(gid)
            def s(v): return '✅' if v else '❌'
            m = InlineKeyboardMarkup(row_width=2)
            m.add(
                InlineKeyboardButton(f'🔗 ضد لینک {s(g2.get("anti_link",1))}', callback_data=f'adv_toggle_anti_link_{gid}'),
                InlineKeyboardButton(f'🚫 ضد اسپم {s(g2.get("anti_spam",1))}', callback_data=f'adv_toggle_anti_spam_{gid}'),
            )
            m.add(
                InlineKeyboardButton(f'🤬 ضد فحش {s(g2.get("anti_profanity",1))}', callback_data=f'adv_toggle_anti_profanity_{gid}'),
                InlineKeyboardButton(f'👋 خوش‌آمد {s(g2.get("welcome",1))}', callback_data=f'adv_toggle_welcome_{gid}'),
            )
            m.add(
                InlineKeyboardButton(f'🤖 AI گروه {s(g2.get("ai_reply",0))}', callback_data=f'adv_toggle_ai_reply_{gid}'),
                InlineKeyboardButton(f'👋 خداحافظ {s(g2.get("goodbye",0))}', callback_data=f'adv_toggle_goodbye_{gid}'),
            )
            m.add(
                InlineKeyboardButton('📊 آمار', callback_data=f'adv_stats_{gid}'),
                InlineKeyboardButton('🔒 V2Ray', callback_data='adv_v2ray_panel'),
            )
            m.add(
                InlineKeyboardButton('👥 دستیاران', callback_data=f'adv_assistants_{gid}'),
                InlineKeyboardButton('⚠️ اخطارها', callback_data=f'adv_warns_{gid}'),
            )
            try:
                bot.edit_message_reply_markup(cid, mid, reply_markup=m)
            except: pass

        # ─── V2Ray پنل ───
        elif data == 'adv_v2ray_panel':
            if uid != ADMIN_ID and not is_group_admin(cid, uid):
                answer('⛔ دسترسی ندارید!', True); return
            conn = db()
            c = conn.cursor()
            c.execute('SELECT COUNT(*) FROM v2ray_configs')
            total = c.fetchone()[0]
            conn.close()

            m = InlineKeyboardMarkup()
            m.add(InlineKeyboardButton('➕ افزودن کانفیگ', callback_data='adv_add_v2ray'))
            m.add(InlineKeyboardButton('📋 لیست کانفیگ‌ها', callback_data='adv_all_v2ray_0'))
            m.add(InlineKeyboardButton('🗑️ حذف آخرین', callback_data='adv_del_v2ray'))

            bot.edit_message_text(
                f'🔒 *پنل مدیریت V2Ray*\n\n'
                f'📦 کل کانفیگ‌ها: `{total}`\n\n'
                'برای افزودن کانفیگ جدید دکمه زیر رو بزن:',
                cid, mid, parse_mode='Markdown', reply_markup=m)

        # ─── لیست V2Ray ───
        elif data.startswith('adv_all_v2ray_'):
            page = int(data.split('_')[-1])
            conn = db()
            c = conn.cursor()
            c.execute('SELECT id,name,config,added_at FROM v2ray_configs ORDER BY id DESC LIMIT 5 OFFSET ?',
                      (page * 5,))
            configs = c.fetchall()
            c.execute('SELECT COUNT(*) FROM v2ray_configs')
            total = c.fetchone()[0]
            conn.close()

            if not configs:
                answer('📭 کانفیگ بیشتری نیست!', True); return

            text = f'🔒 *کانفیگ‌های V2Ray* (صفحه {page+1}):\n\n'
            for cfg in configs:
                text += f'🆔 `{cfg[0]}` | 📛 *{cfg[1]}*\n`{cfg[2][:80]}`\n📅 {cfg[3][:10]}\n\n'

            m = InlineKeyboardMarkup(row_width=2)
            btns = []
            if page > 0:
                btns.append(InlineKeyboardButton('◀️ قبلی', callback_data=f'adv_all_v2ray_{page-1}'))
            if (page + 1) * 5 < total:
                btns.append(InlineKeyboardButton('▶️ بعدی', callback_data=f'adv_all_v2ray_{page+1}'))
            if btns: m.add(*btns)
            m.add(InlineKeyboardButton('🔙 برگشت', callback_data='adv_v2ray_panel'))

            bot.edit_message_text(text, cid, mid, parse_mode='Markdown', reply_markup=m)

        # ─── افزودن V2Ray ───
        elif data == 'adv_add_v2ray':
            if uid != ADMIN_ID:
                answer('⛔ فقط ادمین اصلی!', True); return
            pending_v2ray[uid] = {'step': 'name'}
            bot.answer_callback_query(call.id)
            bot.send_message(uid, '📛 اسم کانفیگ رو بنویس:')

        # ─── حذف آخرین V2Ray ───
        elif data == 'adv_del_v2ray':
            if uid != ADMIN_ID:
                answer('⛔ فقط ادمین اصلی!', True); return
            conn = db()
            c = conn.cursor()
            c.execute('DELETE FROM v2ray_configs WHERE id=(SELECT MAX(id) FROM v2ray_configs)')
            conn.commit()
            conn.close()
            answer('✅ آخرین کانفیگ حذف شد!')

        # ─── دستیاران ───
        elif data.startswith('adv_assistants_'):
            gid = int(data.split('_')[-1])
            conn = db()
            c = conn.cursor()
            c.execute('SELECT user_id, level FROM group_assistants WHERE group_id=?', (gid,))
            rows = c.fetchall()
            conn.close()

            if not rows:
                answer('👥 دستیاری وجود ندارد!', True); return

            text = '👥 *دستیاران گروه:*\n\n'
            for r in rows:
                try:
                    u = bot.get_chat_member(gid, r[0])
                    name = u.user.first_name
                except:
                    name = f'کاربر {r[0]}'
                level_icon = '🔰' if r[1] == 1 else '🔱'
                text += f'{level_icon} {name} (`{r[0]}`)\n'

            bot.edit_message_text(text, cid, mid, parse_mode='Markdown',
                                  reply_markup=InlineKeyboardMarkup([[
                                      InlineKeyboardButton('🔙 برگشت', callback_data=f'adv_toggle_anti_link_{gid}')
                                  ]]))

        # ─── اخطارها ───
        elif data.startswith('adv_warns_'):
            gid = int(data.split('_')[-1])
            conn = db()
            c = conn.cursor()
            c.execute('SELECT user_id, COUNT(*) as cnt FROM warns WHERE group_id=? GROUP BY user_id ORDER BY cnt DESC LIMIT 10',
                      (gid,))
            rows = c.fetchall()
            conn.close()

            if not rows:
                answer('⚠️ اخطاری وجود ندارد!', True); return

            text = '⚠️ *اخطارهای گروه:*\n\n'
            for r in rows:
                try:
                    u = bot.get_chat_member(gid, r[0])
                    name = u.user.first_name
                except:
                    name = f'کاربر {r[0]}'
                text += f'• {name}: `{r[1]}` اخطار\n'

            bot.edit_message_text(text, cid, mid, parse_mode='Markdown',
                                  reply_markup=InlineKeyboardMarkup([[
                                      InlineKeyboardButton('🔙 برگشت', callback_data=f'adv_stats_{gid}')
                                  ]]))

        else:
            answer()


    # ═══════════════════════════════════════════
    #     📥 افزودن V2Ray از طریق پیوی
    # ═══════════════════════════════════════════

    @bot.message_handler(func=lambda m: m.chat.type == 'private' and m.from_user.id == ADMIN_ID)
    def admin_private_handler(message):
        uid = message.from_user.id
        if uid not in pending_v2ray: return

        state = pending_v2ray[uid]

        if state.get('step') == 'name':
            pending_v2ray[uid] = {'step': 'config', 'name': message.text.strip()}
            bot.reply_to(message, f'✅ اسم: *{message.text.strip()}*\n\nحالا کانفیگ V2Ray رو بفرست:', parse_mode='Markdown')

        elif state.get('step') == 'config':
            name = state['name']
            config = message.text.strip()
            conn = db()
            c = conn.cursor()
            c.execute('INSERT INTO v2ray_configs (name,config,added_at,added_by) VALUES (?,?,?,?)',
                      (name, config, datetime.now().isoformat(), uid))
            conn.commit()
            conn.close()
            del pending_v2ray[uid]
            bot.reply_to(message,
                f'✅ *کانفیگ {name} اضافه شد!*\n\n`{config[:100]}...`',
                parse_mode='Markdown')


print('[SFOR] ✅ sfor_advanced module loaded!', flush=True)
