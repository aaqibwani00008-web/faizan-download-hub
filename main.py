    import os
import re
import asyncio
import tempfile
import shutil
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread

import yt_dlp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

TOKEN = os.getenv("BOT_TOKEN")


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
        pass


def start_health_server():
    port = int(os.getenv("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    server.serve_forever()


def is_supported_url(url):
    return bool(re.search(
        r"(youtube\.com|youtu\.be|instagram\.com)",
        url,
        re.IGNORECASE
    ))


def get_video_info(url):
    options = {
        "quiet": False,
        "no_warnings": False,
        "skip_download": True,
        "noplaylist": True,
    }

    with yt_dlp.YoutubeDL(options) as ydl:
        return ydl.extract_info(url, download=False)


def download_video(url, folder):
    output = os.path.join(folder, "%(title).80s.%(ext)s")

    options = {
        "format": (
            "bestvideo[height<=1080]+bestaudio/"
            "best[height<=1080]/best"
        ),
        "outtmpl": output,
        "merge_output_format": "mp4",
        "noplaylist": True,
        "quiet": False,
        "no_warnings": False,
    }

    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)

        base = os.path.splitext(filename)[0]
        mp4_file = base + ".mp4"

        if os.path.exists(mp4_file):
            return mp4_file

        if os.path.exists(filename):
            return filename

    for file in os.listdir(folder):
        path = os.path.join(folder, file)
        if os.path.isfile(path):
            return path

    raise Exception("Video file nahi mili.")


def download_audio(url, folder):
    output = os.path.join(folder, "%(title).80s.%(ext)s")

    options = {
        "format": "bestaudio/best",
        "outtmpl": output,
        "noplaylist": True,
        "quiet": False,
        "no_warnings": False,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
    }

    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)

        base = os.path.splitext(filename)[0]
        mp3_file = base + ".mp3"

        if os.path.exists(mp3_file):
            return mp3_file

    for file in os.listdir(folder):
        path = os.path.join(folder, file)
        if os.path.isfile(path):
            return path

    raise Exception("Audio file nahi mili.")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Assalamualaikum Miya!\n\n"
        "🎬 YouTube ya Instagram ka public video link bhejo.\n\n"
        "Main tumhe:\n"
        "🎬 1080p Video\n"
        "🎵 Audio\n\n"
        "options dunga."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 <b>Video Downloader</b>\n\n"
        "Supported:\n"
        "▶️ YouTube\n"
        "📸 Instagram\n\n"
        "Public video link bhejo.",
        parse_mode="HTML"
    )


async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()

    if not is_supported_url(url):
        await update.message.reply_text(
            "❌ Ye supported link nahi hai.\n\n"
            "YouTube ya Instagram link bhejo."
        )
        return

    context.user_data["url"] = url

    status = await update.message.reply_text(
        "🔎 Video information check ho rahi hai..."
    )

    try:
        info = await asyncio.to_thread(get_video_info, url)

        title = info.get("title", "Video")
        thumbnail = info.get("thumbnail")
        duration = info.get("duration")

        if duration:
            minutes = duration // 60
            seconds = duration % 60
            duration_text = f"{minutes}:{seconds:02d}"
        else:
            duration_text = "Unknown"

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "🎬 1080p",
                    callback_data="video_1080"
                )
            ],
            [
                InlineKeyboardButton(
                    "🎵 Audio",
                    callback_data="audio"
                )
            ]
        ])

        caption = (
            f"🎬 <b>{title}</b>\n\n"
            f"⏱ Duration: {duration_text}\n\n"
            "👇 Download option choose karo:"
        )

        await status.delete()

        if thumbnail:
            try:
                await update.message.reply_photo(
                    photo=thumbnail,
                    caption=caption,
                    parse_mode="HTML",
                    reply_markup=keyboard
                )
                return
            except Exception as e:
                print("THUMBNAIL ERROR:", repr(e))

        await update.message.reply_text(
            caption,
            parse_mode="HTML",
            reply_markup=keyboard
        )

    except Exception as e:
        print("INFO ERROR:", repr(e))
        await status.edit_text(
            "❌ Video information nahi mil saki.\n\n"
            "Link public hona chahiye."
        )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    url = context.user_data.get("url")

    if not url:
        await query.message.reply_text(
            "❌ Link nahi mila.\n"
            "Video link dobara bhejo."
        )
        return

    if query.data == "video_1080":

        status = await query.message.reply_text(
            "⏳ 1080p video download ho rahi hai...\n\n"
            "Thoda wait karo."
        )

        folder = tempfile.mkdtemp(prefix="video_")

        try:
            file_path = await asyncio.to_thread(
                download_video,
                url,
                folder
            )

            await status.edit_text(
                "📤 Video Telegram par upload ho rahi hai..."
            )

            with open(file_path, "rb") as video:
                await query.message.reply_video(
                    video=video,
                    caption="🎬 1080p"
                )

            await status.delete()

        except Exception as e:
            print("VIDEO ERROR:", repr(e))
            await status.edit_text(
                "❌ 1080p download failed.\n\n"
                "Public link aur available quality check karo."
            )

        finally:
            shutil.rmtree(folder, ignore_errors=True)

    elif query.data == "audio":

        status = await query.message.reply_text(
            "⏳ Audio download ho rahi hai..."
        )

        folder = tempfile.mkdtemp(prefix="audio_")

        try:
            file_path = await asyncio.to_thread(
                download_audio,
                url,
                folder
            )

            await status.edit_text(
                "📤 Audio Telegram par upload ho rahi hai..."
            )

            with open(file_path, "rb") as audio:
                await query.message.reply_audio(audio=audio)

            await status.delete()

        except Exception as e:
            print("AUDIO ERROR:", repr(e))
            await status.edit_text(
                "❌ Audio download failed."
            )

        finally:
            shutil.rmtree(folder, ignore_errors=True)


def main():
    if not TOKEN:
        raise RuntimeError("BOT_TOKEN environment variable missing")

    Thread(
        target=start_health_server,
        daemon=True
    ).start()

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_url
        )
    )

    app.add_handler(
        CallbackQueryHandler(button_handler)
    )

    print("🤖 Bot started successfully!")

    app.run_polling()


if __name__ == "__main__":
    main()
