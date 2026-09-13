import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

TOKEN = os.environ["BOT_TOKEN"]


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/healthz":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        return


def run_health_server():
    port = int(os.environ.get("PORT", "10000"))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    server.serve_forever()


threading.Thread(target=run_health_server, daemon=True).start()


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
            if filename.endswith(".mp4"):
                await update.message.reply_video(
                    video=media,
                    supports_streaming=True
                )
            else:
                await update.message.reply_document(
                    document=media
                )

        os.remove(filename)

    except Exception:
        await msg.edit_text(
            "❌ Download failed.\n"
            "Direct downloadable media link try karo."
        )


app = Application.builder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("help", help_command))
app.add_handler(
    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link)
)

print("🤖 Faizan Download Hub is running!")
app.run_polling()        
