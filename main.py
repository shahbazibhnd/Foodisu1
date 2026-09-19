import asyncio
import os
import sys
import threading
import logging
import shutil

# ==========================================
# آماده‌سازی session قبل از import balenova
# ==========================================
SESSION_DIR = "sessions"
SESSION_FILE = os.path.join(SESSION_DIR, "bale.session")
SECRET_PATH = "/etc/secrets/bale.session"

# ساخت پوشه sessions
os.makedirs(SESSION_DIR, exist_ok=True)

# ۱. اگر SESSION_DATA در Environment بود، محتواش رو در فایل بنویس
session_data = os.environ.get("SESSION_DATA")
if session_data:
    try:
        with open(SESSION_FILE, "w", encoding="utf-8") as f:
            f.write(session_data)
        print(f"✅ Session از SESSION_DATA در {SESSION_FILE} ذخیره شد")
    except Exception as e:
        print(f"❌ خطا در نوشتن session: {e}")

# ۲. اگر فایل Secret File وجود داشت، کپی کن
elif os.path.exists(SECRET_PATH):
    try:
        shutil.copy(SECRET_PATH, SESSION_FILE)
        print(f"✅ Session از {SECRET_PATH} کپی شد")
    except Exception as e:
        print(f"❌ خطا در کپی session: {e}")

else:
    print("⚠️ هیچ session ی پیدا نشد! اگر لاگین نشده‌اید، خطا می‌دهد.")


# ==========================================
# حالا balenova رو import کن
# ==========================================
from balenova import Client, events
from flask import Flask, jsonify


# ==========================================
# تنظیمات و لاگ‌گیری
# ==========================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(threadName)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

GROUP_ID = 1438433965 # ⚠️ این رو با آیدی واقعی گروه چک کنید
MESSAGE_TO_SEND = (
    "سلام و احترام 🌹\n"
    "درخواست غذا"
)


# ==========================================
# تشخیص پیام غذا
# ==========================================
def is_food_available(text):
    if not text:
        return False
    text = text.strip()
    banned_words = ["ناموجود", "موجود نیست", "نداریم", "تمام شد"]
    for word in banned_words:
        if word in text:
            return False
    allowed_words = ["شام موجود", "ناهار موجود", "نهار موجود", "غذا موجود", "موجود"]
    for word in allowed_words:
        if word in text:
            return True
    return False


# ==========================================
# پخش موزیک موفقیت (کراس پلتفرم)
# ==========================================
def play_success_sound():
    if sys.platform == "win32":
        import winsound
        melody = [(784, 300), (880, 300), (988, 300), (1047, 300)]
        for freq, dur in melody:
            winsound.Beep(freq, dur)
    else:
        logger.info("🔔 پیام با موفقیت ارسال شد")


# ==========================================
# اتصال حساب شخصی
# ==========================================
client = Client()


# ==========================================
# دریافت پیام گروه
# ==========================================
@client.on(events.NewMessage)
async def handler(event):
    try:
        msg = event.message

        # فقط گروه مشخص
        if msg.chat.peer_id != GROUP_ID:
            return

        text = msg.text or ""
        logger.info(f"📨 پیام جدید گروه: {text[:80]}")

        if not is_food_available(text):
            logger.info("ℹ️ پیام رد شد")
            return

        user_id = msg.author.id
        logger.info(f"👤 کاربر: {user_id}")

        private_peer = f"{user_id}|1"
        logger.info(f"📩 ارسال به: {private_peer}")

        await client.send_message(private_peer, MESSAGE_TO_SEND)
        logger.info("✅ ارسال موفق")

        play_success_sound()

    except Exception as e:
        logger.error(f"❌ خطا: {type(e).__name__}: {e}", exc_info=True)


# ==========================================
# اجرای کلاینت در thread جداگانه
# ==========================================
async def run_bale_client():
    logger.info("🚀 FOOD ALERT فعال شد")
    logger.info(f"گروه: {GROUP_ID}")
    logger.info("منتظر پیام غذا...")
    await client.run()


def start_bale_client():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(run_bale_client())
    except Exception as e:
        logger.error(f"❌ کلاینت بله متوقف شد: {e}")
    finally:
        loop.close()


# ==========================================
# وب سرور Flask
# ==========================================
app = Flask(__name__)


@app.route('/')
@app.route('/health')
def health_check():
    return jsonify({
        "status": "alive",
        "service": "bale-food-alert",
        "group_id": GROUP_ID
    }), 200


# ==========================================
# اجرا
# ==========================================
if __name__ == "__main__":
    bale_thread = threading.Thread(
        target=start_bale_client,
        daemon=True,
        name="BaleClient"
    )
    bale_thread.start()
    logger.info("✅ Thread کلاینت بله شروع شد")

    port = int(os.environ.get("PORT", 10000))
    logger.info(f"🌐 وب سرور Flask روی پورت {port} شروع شد")

    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
