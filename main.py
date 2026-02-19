import asyncio
import logging
import os
import random
import shutil
import tempfile
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

from download import download_reel
from upload_video import get_authenticated_service, upload_video

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Required environment variable {name!r} is not set")
    return value


# Fail fast at startup if any required config is missing
BOT_TOKEN = _require_env("BOT_TOKEN")
WEBHOOK_URL = _require_env("WEBHOOK_URL")        # e.g. https://tg-webhook-bot.onrender.com/webhook
WEBHOOK_SECRET = _require_env("WEBHOOK_SECRET")  # any random secret string

tg_app = Application.builder().token(BOT_TOKEN).build()


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello, send me an Instagram reel link")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text: str = update.message.text
    user = update.message.chat.username
    logger.info("User %s sent: %s", user, text)

    # Use a unique temp dir per request to avoid race conditions between concurrent users
    tmpdir = tempfile.mkdtemp()
    try:
        await asyncio.to_thread(download_reel, text, tmpdir)

        files = os.listdir(tmpdir)
        if not files:
            await update.message.reply_text("Download failed: no file found.")
            return

        downloaded_file = os.path.join(tmpdir, files[0])
        youtube = get_authenticated_service()
        n = random.randint(1, 1000)

        result = await asyncio.to_thread(
            upload_video,
            youtube,
            downloaded_file,
            f"default-test{n}",
            f"default-description{n}",
            23,
            f"defaultkeyword{n}",
            "private",
        )

        await update.message.reply_text(result)
        logger.info("Upload complete for user %s", user)

    except Exception:
        logger.exception("Error processing message from user %s", user)
        await update.message.reply_text("Something went wrong, please try again.")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error("Update %s caused error", update, exc_info=context.error)


tg_app.add_handler(CommandHandler("start", start_command))
tg_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
tg_app.add_error_handler(error_handler)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await tg_app.initialize()
    await tg_app.start()
    await tg_app.bot.set_webhook(WEBHOOK_URL, secret_token=WEBHOOK_SECRET)
    logger.info("Webhook set to %s", WEBHOOK_URL)
    yield
    await tg_app.stop()
    await tg_app.shutdown()


app = FastAPI(lifespan=lifespan)


@app.post("/webhook")
async def telegram_webhook(request: Request):
    if request.headers.get("X-Telegram-Bot-Api-Secret-Token") != WEBHOOK_SECRET:
        return Response(status_code=403)

    data = await request.json()
    update = Update.de_json(data, tg_app.bot)
    await tg_app.update_queue.put(update)
    return {"ok": True}


@app.get("/")
async def health():
    return {"status": "ok"}
