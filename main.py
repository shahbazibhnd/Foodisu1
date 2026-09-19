import asyncio
import os
import sys
import threading
import logging

from flask import Flask, jsonify
from balenova import Client, events

# ==========================================
# تنظیمات و لاگ‌گیری
# ==========================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(threadName)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# تنظیمات ربات
GROUP_ID = 1124146857
MESSAGE_TO_SEND = (
    "سلام و احترام 🌹\n"
    "درخواست غذا"
)

# ==========================================
# توابع کمکی
# ==========================================
def is_food_available(text):
    """تشخیص وجود غذا در متن پیام"""
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

def play_success_sound():
    """پخش صدای موفقیت (کراس پلتفرم)"""
    if sys.platform == "win32":
        import winsound
        melody = [(784, 300), (880, 300), (988, 300), (1047, 300)]
        for freq, dur in melody:
            winsound.Beep(freq, dur)
    else:
        # در لینوکس/Render فقط لاگ می‌کنیم
        logger.info("🔔 پیام با موفقیت ارسال شد")

# ==========================================
# راه‌اندازی کلاینت بله
# ==========================================
client = Client()

@client.on(events.NewMessage)
async def handler(event):
    """هندلر پیام‌های جدید"""
    try:
        msg = event.message
        
        # فقط گروه مشخص
        if msg.chat.peer_id != GROUP_ID:
            return
        
        text = msg.text or ""
        logger.info(f"📨 پیام جدید گروه: {text[:100]}")
        
        # بررسی وجود غذا
        if not is_food_available(text):
            logger.info("ℹ️ پیام رد شد")
            return
        
        user_id = msg.author.id
        logger.info(f"👤 کاربر: {user_id}")
        
        # ارسال پیام خصوصی
        private_peer = f"{user_id}|1"
        logger.info(f"📩 ارسال به: {private_peer}")
        
        await client.send_message(private_peer, MESSAGE_TO_SEND)
        logger.info("✅ ارسال موفق")
        
        # پخش صدای موفقیت
        play_success_sound()
        
    except Exception as e:
        logger.error(f"❌ خطا: {type(e).__name__}: {e}", exc_info=True)

async def run_bale_client():
    """اجرای کلاینت بله"""
    logger.info("🚀 FOOD ALERT فعال شد")
    logger.info(f"گروه: {GROUP_ID}")
    logger.info("منتظر پیام غذا...")
    await client.run()

def start_bale_client():
    """اجرای کلاینت در یک thread جداگانه"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(run_bale_client())
    except Exception as e:
        logger.error(f"❌ کلاینت بله متوقف شد: {e}")
    finally:
        loop.close()

# ==========================================
# وب سرور Flask (برای Render)
# ==========================================
app = Flask(__name__)

@app.route('/')
@app.route('/health')
def health_check():
    """Endpoint برای بیدار نگه داشتن سرویس"""
    return jsonify({
        "status": "alive",
        "service": "bale-food-alert",
        "group_id": GROUP_ID
    }), 200

# ==========================================
# راه‌اندازی اصلی
# ==========================================
if __name__ == "__main__":
    # ۱. راه‌اندازی کلاینت بله در thread جداگانه
    bale_thread = threading.Thread(
        target=start_bale_client,
        daemon=True,
        name="BaleClient"
    )
    bale_thread.start()
    logger.info("✅ Thread کلاینت بله شروع شد")
    
    # ۲. راه‌اندازی وب سرور Flask روی پورت Render
    port = int(os.environ.get("PORT", 10000))
    logger.info(f"🌐 وب سرور Flask روی پورت {port} شروع شد")
    
    app.run(
        host="0.0.0.0",
        port=port,
        debug=False,
        use_reloader=False  # حیاتی: جلوگیری از اجرای دوباره
    )
