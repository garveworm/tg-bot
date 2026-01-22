import os
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import (
    Application,
    MessageHandler,
    ContextTypes,
    filters,
)

BOT_TOKEN = os.environ["BOT_TOKEN"]
WEBHOOK_SECRET = os.environ["WEBHOOK_SECRET"]

app = FastAPI()
tg_app = Application.builder().token(BOT_TOKEN).build()


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"✅ Deployed bot works!\nYou sent:\n{update.message.text}")


tg_app.add_handler(MessageHandler(filters.TEXT & filters.COMMAND, handle_message))


@app.on_event("startup")
async def startup():
    await tg_app.initialize()


@app.get("/")
async def health():
    return "OK"


@app.post("/webhook")
async def telegram_webhook(request: Request):
    if request.headers.get("X-Telegram-Bot-Api-Secret-Token") != WEBHOOK_SECRET:
        return {"ok": False}

    data = await request.json()
    update = Update.de_json(data, tg_app.bot)
    await tg_app.process_update(update)
    return {"ok": True}
