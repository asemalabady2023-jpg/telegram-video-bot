import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# التوكن من متغير البيئة
TOKEN = os.getenv('BOT_TOKEN')

# تفعيل التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """رد على /start"""
    await update.message.reply_text(
        "👋 مرحباً!\n\n"
        "أرسل لي رابط فيديو من:\n"
        "• YouTube\n"
        "• TikTok\n"
        "• Instagram\n"
        "• Twitter/X\n"
        "• Facebook\n\n"
        "📥 وسأحاول تحميله لك!"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """رد على /help"""
    await update.message.reply_text(
        "📖 طريقة الاستخدام:\n\n"
        "1️⃣ أرسل /start\n"
        "2️⃣ أرسل رابط الفيديو\n"
        "3️⃣ انتظر التحميل\n\n"
        "⚠️ ملاحظة: بعض المواقع قد لا تعمل"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الرسائل العادية"""
    text = update.message.text
    
    # التحقق من الرابط
    if not text.startswith(('http://', 'https://')):
        await update.message.reply_text("❌ أرسل رابط صحيح يبدأ بـ http:// أو https://")
        return
    
    # رسالة انتظار
    wait_msg = await update.message.reply_text("⏳ جاري معالجة الرابط...")
    
    try:
        # هنا نضيف كود التحميل لاحقاً
        await wait_msg.edit_text(
            f"✅ استلمت الرابط:\n{text}\n\n"
            "🚧 ميزة التحميل قيد التطوير...\n"
            "سيتم إضافتها قريباً!"
        )
    except Exception as e:
        logger.error(f"Error: {e}")
        await wait_msg.edit_text(f"❌ حدث خطأ: {str(e)}")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الأخطاء"""
    logger.error(f"Update {update} caused error {context.error}")
    if update and update.effective_message:
        await update.effective_message.reply_text("❌ حدث خطأ غير متوقع")

def main():
    """الدالة الرئيسية"""
    if not TOKEN:
        logger.error("❌ BOT_TOKEN not found!")
        return
    
    logger.info("🚀 Starting bot...")
    
    # إنشاء التطبيق
    app = Application.builder().token(TOKEN).build()
    
    # إضافة المعالجات
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # معالجة الأخطاء
    app.add_error_handler(error_handler)
    
    # تشغيل البوت
    logger.info("✅ Bot is running!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
