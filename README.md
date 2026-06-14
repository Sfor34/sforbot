# 🔥 SFOR Bot v3.0

ربات تلگرام SFOR — مدیریت گروه + هوش مصنوعی + ابزارها

## ✅ قابلیت‌ها

- 🤖 هوش مصنوعی Groq (مدل llama-3.3-70b)
- 🔒 توزیع کانفیگ V2Ray رایگان
- 📁 توزیع فایل VPN
- 🛡️ مدیریت گروه (ضد لینک، ضد اسپم، ضد فحش)
- 👋 خوش‌آمد / خداحافظ
- 🔐 کپچا برای اعضای جدید
- ⚠️ سیستم اخطار
- 📊 آمار گروه و رنکینگ
- 🌤️ آب‌وهوا / قیمت کریپتو / اطلاعات IP
- ⏰ یادآور و تایمر
- 🌐 ترجمه و کوتاه‌کننده لینک
- 🎮 بازی حدس عدد
- 📣 پخش پیام همگانی

## 🚀 نصب روی Render

1. فورک یا آپلود کن
2. در Render → New Web Service بساز
3. Environment Variables رو تنظیم کن:
   - `TOKEN` — توکن ربات از @BotFather
   - `ADMIN_ID` — آیدی عددی ادمین از @userinfobot
   - `GROQ_KEY` — کلید از [console.groq.com](https://console.groq.com) (رایگان)
   - `ADMIN_PASS` — پسورد دلخواه

## ⚙️ تنظیم محلی

```bash
pip install -r requirements.txt
cp .env.example .env
# .env رو ویرایش کن
python bot.py
```

## 📁 ساختار پروژه

```
bot.py              — فایل اصلی
database.py         — توابع دیتابیس (مرجع)
modules/
  sfor_advanced.py  — دستورات پیشرفته گروه
  sfor_features.py  — ابزارها و سرگرمی
requirements.txt    — وابستگی‌ها
Procfile            — تنظیم Render
render.yaml         — تنظیمات deploy
.env.example        — نمونه متغیرهای محیطی
```
