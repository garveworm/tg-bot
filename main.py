import asyncio
import logging
import os
import re
import shutil
import tempfile
from contextlib import asynccontextmanager

import requests
from bs4 import BeautifulSoup
from fastapi import FastAPI, Request, Response
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

from download import download_reel
from upload_video import get_authenticated_service, upload_video

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s: %(message)s',
)
logger = logging.getLogger(__name__)


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f'Required environment variable {name!r} is not set')
    return value


# Always required
BOT_TOKEN = _require_env('BOT_TOKEN')

# Only required in webhook/deployed mode
WEBHOOK_URL = os.environ.get('WEBHOOK_URL', '')        # e.g. https://tg-webhook-bot.onrender.com/webhook
WEBHOOK_SECRET = os.environ.get('WEBHOOK_SECRET', '')  # any random secret string

POPULAR_TAGS = '#Shorts#YouTubeShorts#ViralShorts#Viral#ShortsVideo'

tg_app = Application.builder().token(BOT_TOKEN).build()


def _fetch_title(url: str) -> str:
    resp = requests.get(url, timeout=10)
    if resp.status_code != 200:
        return ''
    soup = BeautifulSoup(resp.text, 'html.parser')
    meta = soup.find('meta', property='og:description')
    if not meta:
        return ''
    content = meta.get('content', '')
    # Description format is "username: caption" — take the caption part
    parts = content.split(':', 1)
    return parts[1].strip() if len(parts) > 1 else content.strip()


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Hello, send me an Instagram reel link')


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text: str = update.message.text
    user = update.message.chat.username
    logger.info('User %s sent: %s', user, text)

    tmpdir = tempfile.mkdtemp()
    try:
        title = await asyncio.to_thread(_fetch_title, text)
        await asyncio.to_thread(download_reel, text, tmpdir)

        files = os.listdir(tmpdir)
        if not files:
            await update.message.reply_text('Download failed: no file found.')
            return

        downloaded_file = os.path.join(tmpdir, files[0])

        author = 'by unknown'
        match = re.search(r'Video by (\S+)', downloaded_file)
        if match:
            author = f'by {match.group(1)}'

        youtube = get_authenticated_service()
        result = await asyncio.to_thread(
            upload_video,
            youtube,
            downloaded_file,
            title,
            author,
            23,
            POPULAR_TAGS,
            'private',
        )

        await update.message.reply_text(result)
        logger.info('Upload complete for user %s', user)

    except Exception:
        logger.exception('Error processing message from user %s', user)
        await update.message.reply_text('Something went wrong, please try again.')
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error('Update %s caused error', update, exc_info=context.error)


tg_app.add_handler(CommandHandler('start', start_command))
tg_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
tg_app.add_error_handler(error_handler)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not WEBHOOK_URL or not WEBHOOK_SECRET:
        raise RuntimeError('WEBHOOK_URL and WEBHOOK_SECRET must be set in webhook mode')
    await tg_app.initialize()
    await tg_app.start()
    await tg_app.bot.set_webhook(WEBHOOK_URL, secret_token=WEBHOOK_SECRET)
    logger.info('Webhook set to %s', WEBHOOK_URL)
    yield
    await tg_app.stop()
    await tg_app.shutdown()


app = FastAPI(lifespan=lifespan)


@app.post('/webhook')
async def telegram_webhook(request: Request):
    if request.headers.get('X-Telegram-Bot-Api-Secret-Token') != WEBHOOK_SECRET:
        return Response(status_code=403)

    data = await request.json()
    update = Update.de_json(data, tg_app.bot)
    await tg_app.update_queue.put(update)
    return {'ok': True}


@app.get('/')
async def health():
    return {'status': 'ok'}


if __name__ == '__main__':
    # Local polling mode — no WEBHOOK_URL or WEBHOOK_SECRET needed
    logger.info('Starting in polling mode...')
    tg_app.run_polling(poll_interval=3)
