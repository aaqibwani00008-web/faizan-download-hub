import os
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

TOKEN = os.environ["BOT_TOKEN"]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome to Faizan Download Hub!\n\n"
        "📥 Apna/permission wala direct media link bhejo."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔗 Direct downloadable video/file URL bhejo."
    )

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()

    if not url.startswith(("http://", "https://")):
        await update.message.reply_text("❌ Valid link bhejo.")
        return

    msg = await update.message.reply_text("⏳ Processing...")
    filename = "faizan_download"

    try:
        r = requests.get(url, stream=True, timeout=30)
        r.raise_for_status()

        content_type = r.headers.get("content-type", "").lower()

        if "video" in content_type:
            filename += ".mp4"
        elif "image" in content_type:
            filename += ".jpg"
        else:
            filename += ".bin"

        with open(filename, "wb") as f:
            for chunk in r.iter_content(1024 * 1024):
                if chunk:
                    f.write(chunk)

        await msg.edit_text("📤 Sending...")

        with open(filename, "rb") as media:
            await update.message.reply_document(document=media)

        os.remove(filename)

    except Exception:
        await msg.edit_text(
            "❌ Download failed.\n"
            "Direct downloadable media link try karo."
        )

app = Application.builder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("help", help_command))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))

print("🤖 Faizan Download Hub is running!")
app.run_polling()
