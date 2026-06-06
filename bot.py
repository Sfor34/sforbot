import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask
import threading
import requests
import time
import os

TOKEN = '8576320592:AAFLipMaJiDFJyDCalDemS5ZikTcM-OYC-0'
ADMIN_ID = 7533340777
SITE_URL = 'https://sfor.onrender.com'
BOT_URL = 'https://sforbot.onrender.com'

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)
user_states = {}

@app.route('/')
def home():
    return 'SFOR Bot is running! ✅'

@app.route('/ping')
def ping():
    return 'pong'

def keep_alive():
    while True:
        try:
            requests.get(f'{BOT_URL}/ping')
        except:
            pass
        time.sleep(840)  # هر 14 دقیقه

def main_menu():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton('🌐 ورود به سایت', url=SITE_URL),
        InlineKeyboardButton('📁 فایل‌های مهم', callback_data='files'),
        InlineKeyboardButton('👤 پیام ناشناس', callback_data='anon'),
        InlineKeyboardButton('📞 پشتیبانی', callback_data='support'),
        InlineKeyboardButton('📣 معرفی به دیگران', callback_data='share'),
        InlineKeyboardButton('ℹ️ درباره ما', callback_data='about')
    )
    return markup

def admin_menu():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton('📢 پیام همگانی', callback_data='admin_broadcast'),
        InlineKeyboardButton('🌐 سایت', url=SITE_URL)
    )
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    user = message.from_user
    name = user.first_name or 'کاربر'
    if user.id != ADMIN_ID:
        try:
            bot.send_message(ADMIN_ID,
                f'👤 کاربر جدید:\nنام: {name}\nیوزر: @{user.username or "ندارد"}\nID: {user.id}')
        except:
            pass
    if user.id == ADMIN_ID:
        bot.send_message(message.chat.id, '⚡ پنل ادمین:', reply_markup=admin_menu())
    bot.send_message(message.chat.id,
        f'سلام {name} عزیز! 👋\n\nبه ربات *SFOR* خوش اومدی 🔥\nمرکز ابزارهای هک و امنیت دیجیتال\n\nاز منو زیر انتخاب کن 👇',
        parse_mode='Markdown', reply_markup=main_menu())

@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    uid = call.from_user.id
    cid = call.message.chat.id
    mid = call.message.message_id

    if call.data == 'files':
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(
            InlineKeyboardButton('🌐 مشاهده ابزارها در سایت', url=SITE_URL),
            InlineKeyboardButton('🔙 برگشت', callback_data='back')
        )
        bot.edit_message_text('📁 *فایل‌های مهم*\n\nبرای دانلود ابزارها به سایت برو:',
            cid, mid, parse_mode='Markdown', reply_markup=markup)

    elif call.data == 'anon':
        user_states[uid] = 'anon'
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton('❌ انصراف', callback_data='back'))
        bot.edit_message_text('👤 *پیام ناشناس*\n\nپیامت رو بنویس:',
            cid, mid, parse_mode='Markdown', reply_markup=markup)

    elif call.data == 'support':
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton('🔙 برگشت', callback_data='back'))
        bot.edit_message_text('📞 *پشتیبانی*\n\n👤 @Sfor34\n🌐 sfor.onrender.com',
            cid, mid, parse_mode='Markdown', reply_markup=markup)

    elif call.data == 'share':
        bot_info = bot.get_me()
        link = f'https://t.me/{bot_info.username}?start=ref_{uid}'
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton('📤 اشتراک‌گذاری',
            url=f'https://t.me/share/url?url={link}&text=ربات SFOR - ابزارهای هک و امنیت'))
        markup.add(InlineKeyboardButton('🔙 برگشت', callback_data='back'))
        bot.edit_message_text(f'📣 *معرفی به دیگران*\n\nلینک تو:\n`{link}`',
            cid, mid, parse_mode='Markdown', reply_markup=markup)

    elif call.data == 'about':
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton('🌐 سایت ما', url=SITE_URL))
        markup.add(InlineKeyboardButton('🔙 برگشت', callback_data='back'))
        bot.edit_message_text('ℹ️ *درباره SFOR*\n\nمرکز ابزارهای هک، امنیت و مود\n⚡ ساخته شده توسط تیم SFOR',
            cid, mid, parse_mode='Markdown', reply_markup=markup)

    elif call.data == 'back':
        bot.edit_message_text('منوی اصلی 👇', cid, mid, reply_markup=main_menu())

    elif call.data == 'admin_broadcast' and uid == ADMIN_ID:
        user_states[uid] = 'broadcast'
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton('❌ انصراف', callback_data='admin_back'))
        bot.edit_message_text('📢 پیام همگانی رو بنویس:', cid, mid, reply_markup=markup)

    elif call.data == 'admin_back':
        bot.edit_message_text('⚡ پنل ادمین:', cid, mid, reply_markup=admin_menu())

    bot.answer_callback_query(call.id)

@bot.message_handler(func=lambda m: True)
def handle_text(message):
    uid = message.from_user.id
    state = user_states.get(uid)

    if state == 'anon':
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton('↩️ پاسخ', callback_data='reply_anon'))
        bot.send_message(ADMIN_ID,
            f'👤 *پیام ناشناس:*\n\n{message.text}',
            parse_mode='Markdown', reply_markup=markup)
        bot.send_message(uid, '✅ پیامت ناشناس ارسال شد!', reply_markup=main_menu())
        user_states.pop(uid, None)

    elif state == 'broadcast' and uid == ADMIN_ID:
        bot.send_message(uid, f'✅ پیام ارسال شد!')
        user_states.pop(uid, None)

    else:
        bot.send_message(uid, 'از منو زیر انتخاب کن 👇', reply_markup=main_menu())

def run_bot():
    bot.infinity_polling()

def run_flask():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

if __name__ == '__main__':
    t1 = threading.Thread(target=run_bot)
    t2 = threading.Thread(target=keep_alive)
    t1.start()
    t2.start()
    run_flask()
