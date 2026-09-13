import os
import requests
from telegram import Update
from telegram.ext import Application, MessageHandler, ContextTypes, filters

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

async def ai_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text

    response = requests.post(
        "https://api.openai.com/v1/responses",
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "gpt-5.6-mini",
            "input": user_text
        }
    )

    data = response.json()
    answer = data["output"][0]["content"][0]["text"]

    await update.message.reply_text(answer)

app = Application.builder().token(BOT_TOKEN).build()

app.add_handler(
    MessageHandler(filters.TEXT & ~filters.COMMAND, ai_reply)
)

print("AI Bot is running...")
app.run_polling()
