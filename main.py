import asyncio
import os
import random
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import Application, MessageHandler, ContextTypes, filters, CommandHandler

from download import download_reel
from upload_video import get_authenticated_service, upload_video

BOT_TOKEN = os.environ["BOT_TOKEN"]
WEBHOOK_URL = os.environ["WEBHOOK_URL"]  # e.g. https://tg-webhook-bot.onrender.com/webhook
DEFAULT_DIR = "default"

tg_app = Application.builder().token(BOT_TOKEN).build()


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Hello, send me an insta link')


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text: str = update.message.text
    print(f'User {update.message.chat.username} sent: {text}')

    os.makedirs(DEFAULT_DIR, exist_ok=True)

    # Run blocking operations in a thread so the event loop isn't frozen
    await asyncio.to_thread(download_reel, text, DEFAULT_DIR)

    youtube = await asyncio.to_thread(get_authenticated_service)

    contents = os.listdir(DEFAULT_DIR)
    downloaded_file = os.path.join(DEFAULT_DIR, contents[0])
    n = random.randint(1, 1000)

    result = await asyncio.to_thread(
        upload_video,
        youtube,
        downloaded_file,
        f'default-test{n}',
        f'default-description{n}',
        23,
        f'defaultkeyword{n}',
        'private',
    )

    # Clean up downloaded file after upload
    os.remove(downloaded_file)

    await update.message.reply_text(result)


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f'Update {update} caused error: {context.error}')


tg_app.add_handler(CommandHandler('start', start_command))
tg_app.add_handler(MessageHandler(filters.TEXT, handle_message))
tg_app.add_error_handler(error_handler)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await tg_app.initialize()
    await tg_app.start()  # starts the update queue processor
    await tg_app.bot.set_webhook(WEBHOOK_URL)
    print(f"Webhook set to {WEBHOOK_URL}")
    yield
    await tg_app.stop()
    await tg_app.shutdown()


app = FastAPI(lifespan=lifespan)


@app.post("/webhook")
async def telegram_webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, tg_app.bot)
    # Put update in the queue and return 200 immediately.
    # Telegram requires a fast response or it will retry.
    await tg_app.update_queue.put(update)
    return {"ok": True}


@app.get("/")
async def health():
    return {"status": "ok"}
