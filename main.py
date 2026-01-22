import os
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

from download import download_reel
DEFAULT_DIR = "default"

TOKEN = os.environ["BOT_TOKEN"]
WEBHOOK_SECRET = os.environ["WEBHOOK_SECRET"]
app = FastAPI()
bot_app = Application.builder().token(TOKEN).build()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Webhook bot is live!")


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(update.message.text)

bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))


# @app.on_event("startup")
async def on_startup():
    await bot_app.initialize()
    # Replace with your real public URL:
    # url = os.environ["PUBLIC_URL"] + "/webhook"
    url = "https://t.me/yt_uplolad_bot" + "/webhook"
    await bot_app.bot.set_webhook(url, secret_token=WEBHOOK_SECRET)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await on_startup()
    yield


@app.post("/webhook")
async def webhook(request: Request):
    if request.headers.get("X-Telegram-Bot-Api-Secret-Token") != WEBHOOK_SECRET:
        return {"ok": False}
    data = await request.json()
    update = Update.de_json(data, bot_app.bot)
    url = data.get('insta_link')
    outdir = outdir = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_DIR
    download_reel(url, outdir)
    await bot_app.process_update(update)
    return {"ok": True}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
