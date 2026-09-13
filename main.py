import os
import asyncio
import tempfile
import shutil
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import yt_dlp

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)


TOKEN = os.environ["BOT_TOKEN"]


# -------------------------
# Health server
# -------------------------

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


threading.Thread(
    target=run_health_server,
    daemon=True
).start()


# -------------------------
# Start
# -------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome to Faizan Download Hub!\n\n"
        "📥 Apna/permission wala YouTube video link bhejo."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔗 YouTube video/Shorts link bhejo."
    )


# -------------------------
# Check YouTube URL
# -------------------------

def is_youtube_url(url):
    return (
        "youtube.com/" in url
        or "youtu.be/" in url
    )


# -------------------------
# Get video information
# -------------------------

def get_video_info(url):
    options = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
    }

    with yt_dlp.YoutubeDL(options) as ydl:
        return ydl.extract_info(url, download=False)


# -------------------------
# Download video
# -------------------------

def download_media(url, quality):
    temp_dir = tempfile.mkdtemp(prefix="faizan_")

    try:
        if quality == "360":
            fmt = (
                "bestvideo[height<=360]+bestaudio/"
                "best[height<=360]"
            )

        elif quality == "480":
            fmt = (
                "bestvideo[height<=480]+bestaudio/"
                "best[height<=480]"
            )

        elif quality == "720":
            fmt = (
                "bestvideo[height<=720]+bestaudio/"
                "best[height<=720]"
            )

        elif quality == "audio":
            fmt = "bestaudio/best"

        else:
            raise ValueError("Invalid quality")

        options = {
            "format": fmt,
            "outtmpl": os.path.join(
                temp_dir,
                "%(title).80s.%(ext)s"
            ),
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "merge_output_format": "mp4",
        }

        if quality == "audio":
            options["postprocessors"] = [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ]

        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(
                url,
                download=True
            )

            filename = ydl.prepare_filename(info)

            if quality == "audio":
                base, _ = os.path.splitext(filename)
                filename = base + ".mp3"
            else:
                # yt-dlp may merge into mp4
                if not os.path.exists(filename):
                    base, _ = os.path.splitext(filename)
                    mp4 = base + ".mp4"

                    if os.path.exists(mp4):
                        filename = mp4
                    else:
                        files = os.listdir(temp_dir)

                        if not files:
                            raise FileNotFoundError(
                                "Downloaded file not found"
                            )

                        filename = os.path.join(
                            temp_dir,
                            files[0]
                        )

        return temp_dir, filename

    except Exception:
        shutil.rmtree(
            temp_dir,
            ignore_errors=True
        )
        raise


# -------------------------
# Receive YouTube link
# -------------------------

async def handle_link(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    url = update.message.text.strip()

    if not url.startswith(("http://", "https://")):
        await update.message.reply_text(
            "❌ Valid YouTube link bhejo."
        )
        return

    if not is_youtube_url(url):
        await update.message.reply_text(
            "❌ Filhaal YouTube links supported hain."
        )
        return

    msg = await update.message.reply_text(
        "🔎 Video information check ho rahi hai..."
    )

    try:
        info = await asyncio.to_thread(
            get_video_info,
            url
        )

        title = info.get(
            "title",
            "YouTube Video"
        )

        duration = info.get("duration")

        if duration:
            minutes = duration // 60
            seconds = duration % 60
            duration_text = f"{minutes}:{seconds:02d}"
        else:
            duration_text = "Unknown"

        # Save URL for this user
        context.user_data["youtube_url"] = url

        keyboard = [
            [
                InlineKeyboardButton(
                    "🎬 360p",
                    callback_data="dl:360"
                ),
                InlineKeyboardButton(
                    "🎬 480p",
                    callback_data="dl:480"
                ),
            ],
            [
                InlineKeyboardButton(
                    "🎬 720p",
                    callback_data="dl:720"
                ),
            ],
            [
                InlineKeyboardButton(
                    "🎵 Audio",
                    callback_data="dl:audio"
                ),
            ],
        ]

        await msg.edit_text(
            f"🎬 {title}\n\n"
            f"⏱ Duration: {duration_text}\n\n"
            f"👇 Quality select karo:",
            reply_markup=InlineKeyboardMarkup(
                keyboard
            )
        )

    except Exception as e:
        print("INFO ERROR:", repr(e))

        await msg.edit_text(
            "❌ Video information nahi mil saki.\n\n"
            "Link check karo aur dobara try karo."
        )


# -------------------------
# Button handler
# -------------------------

async def quality_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    url = context.user_data.get(
        "youtube_url"
    )

    if not url:
        await query.message.reply_text(
            "❌ Link expire ho gaya. Dobara link bhejo."
        )
        return

    quality = query.data.split(":")[1]

    quality_name = {
        "360": "360p",
        "480": "480p",
        "720": "720p",
        "audio": "Audio",
    }.get(quality, quality)

    status = await query.message.reply_text(
        f"⏳ {quality_name} download ho raha hai..."
    )

    temp_dir = None

    try:
        temp_dir, filename = await asyncio.to_thread(
            download_media,
            url,
            quality
        )

        await status.edit_text(
            "📤 Telegram par send ho raha hai..."
        )

        with open(filename, "rb") as media:

            if quality == "audio":
                await query.message.reply_audio(
                    audio=media,
                    title=os.path.basename(filename)
                )

            else:
                await query.message.reply_video(
                    video=media,
                    supports_streaming=True
                )

        await status.delete()

    except Exception as e:

        print("DOWNLOAD ERROR:", repr(e))

        await status.edit_text(
            "❌ Download/send failed.\n\n"
            "Video chhota ya doosra quality option try karo."
        )

    finally:

        if temp_dir:
            shutil.rmtree(
                temp_dir,
                ignore_errors=True
            )


# -------------------------
# Application
# -------------------------

app = (
    Application
    .builder()
    .token(TOKEN)
    .build()
)

app.add_handler(
    CommandHandler("start", start)
)

app.add_handler(
    CommandHandler("help", help_command)
)

app.add_handler(
    CallbackQueryHandler(
        quality_callback,
        pattern=r"^dl:"
    )
)

app.add_handler(
    MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_link
    )
)


print("🤖 Faizan Download Hub is running!")

app.run_polling()
