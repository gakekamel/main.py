import os
import asyncio
import tempfile
import subprocess
from functools import partial
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ChatMemberHandler,
    ContextTypes,
    filters,
)

TOKEN = "7353891350:AAGbdWSGobqRSz1hAeD6l3bVswGDDjjwnks" 

# ======== دالة الترحيب بالأعضاء الجدد ========
async def welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.chat_member.new_chat_members:
        name = member.first_name
        await update.effective_chat.send_message(
            f"🎉 أهلاً وسهلاً {name} في المجموعة! نورتنا ❤️"
        )

# ======== رسالة البداية ========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 مرحباً بك!\nأرسل رابط فيديو من (يوتيوب / تيك توك / انستغرام ...)\nوسأقوم بتحميله لك."
    )

# ======== تنفيذ أمر yt-dlp ========
def run_yt_dlp(url: str, outpath: str, fmt: str):
    cmd = [
        "yt-dlp",
        "-f",
        fmt,
        "-o",
        outpath,
        url
    ]
    return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

# ======== استقبال الرابط ========
async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    context.user_data["url"] = url

    # إرسال أزرار الاختيار (فيديو أو صوت)
    keyboard = [
        [
            InlineKeyboardButton("🎬 فيديو", callback_data="video"),
            InlineKeyboardButton("🎵 صوت", callback_data="audio"),
        ]
    ]
    await update.message.reply_text("اختر نوع التحميل:", reply_markup=InlineKeyboardMarkup(keyboard))

# ======== عند اختيار فيديو أو صوت ========
async def type_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    choice = query.data
    context.user_data["type"] = choice
    await query.answer()

    # أزرار الجودة
    keyboard = [
        [
            InlineKeyboardButton("360p", callback_data="360p"),
            InlineKeyboardButton("720p", callback_data="720p"),
            InlineKeyboardButton("1080p", callback_data="1080p"),
        ]
    ]
    await query.edit_message_text("اختر الجودة:", reply_markup=InlineKeyboardMarkup(keyboard))

# ======== تحميل وإرسال الملف ========
async def quality_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    quality = query.data
    await query.answer()

    url = context.user_data.get("url")
    ftype = context.user_data.get("type")

    await query.edit_message_text("⏳ جاري التحميل، انتظر قليلاً...")

    # تنسيق yt-dlp
    fmt = "b[height<=?" + quality.replace("p", "") + "]"
    if ftype == "audio":
        fmt = "bestaudio/best"

    with tempfile.TemporaryDirectory() as td:
        out_template = os.path.join(td, "%(title).80s.%(ext)s")

        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, partial(run_yt_dlp, url, out_template, fmt))

        if result.returncode != 0:
            await query.edit_message_text("❌ حدث خطأ أثناء التحميل.")
            return

        files = os.listdir(td)
        if not files:
            await query.edit_message_text("⚠️ لم يتم العثور على ملف.")
            return

        file_path = os.path.join(td, files[0])
        size = os.path.getsize(file_path)

        if size > 1900 * 1024 * 1024:
            await query.edit_message_text("⚠️ الملف أكبر من 2 جيجابايت ولا يمكن إرساله.")
            return

        if ftype == "audio":
            await query.edit_message_text("🎵 جاري الإرسال...")
            await query.message.reply_audio(audio=open(file_path, "rb"))
        else:
            await query.edit_message_text("🎬 جاري الإرسال...")
            await query.message.reply_video(video=open(file_path, "rb"))

        await query.message.reply_text("✅ تم التحميل والإرسال بنجاح!")

# ======== تشغيل البوت ========
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))
    app.add_handler(CallbackQueryHandler(type_choice, pattern="^(video|audio)$"))
    app.add_handler(CallbackQueryHandler(quality_choice, pattern="^(360p|720p|1080p)$"))
    app.add_handler(ChatMemberHandler(welcome, ChatMemberHandler.CHAT_MEMBER))

    print("🚀 البوت يعمل الآن...")
    app.run_polling()

if __name__ == "__main__":
    main()
