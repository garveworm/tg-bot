from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import Application, MessageHandler, ContextTypes, filters
import os

BOT_TOKEN = os.environ["BOT_TOKEN"]
WEBHOOK_SECRET = os.environ["WEBHOOK_SECRET"]

app = FastAPI()
tg_app = Application.builder().token(BOT_TOKEN).build()

# Handler to process messages
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("Received message from Telegram:", update.message.text)
    await update.message.reply_text(f"Got your message: {update.message.text}")

tg_app.add_handler(MessageHandler(filters.TEXT, handle_message))

@app.on_event("startup")
async def startup():
    await tg_app.initialize()

@app.post("/webhook")
async def telegram_webhook(request: Request):
    # Optional secret token check
    if request.headers.get("X-Telegram-Bot-Api-Secret-Token") != WEBHOOK_SECRET:
        return {"ok": False}

    data = await request.json()
    try:
        update = Update.de_json(data, tg_app.bot)
    except Exception as e:
        print("⚠️ Non-Telegram payload:", e)
        return {"ok": False}

    await tg_app.process_update(update)
    return {"ok": True}
