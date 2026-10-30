import logging
from functools import wraps

import httpx
from telegram import LinkPreviewOptions, Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

HEADERS = {"User-Agent": "AllInOneTelegramBot/1.0"}


async def fetch(url, params=None, headers=None, as_text=False):
    """Simple async GET helper that returns JSON (default) or text."""
    h = {**HEADERS, **(headers or {})}
    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        r = await client.get(url, params=params, headers=h)
        r.raise_for_status()
        return r.text if as_text else r.json()


async def send(update: Update, text: str):
    """Reply with HTML formatting and no link previews."""
    await update.effective_message.reply_text(
        text,
        parse_mode=ParseMode.HTML,
        link_preview_options=LinkPreviewOptions(is_disabled=True),
    )


def safe(fn):
    """Wrap a handler so API failures give a friendly message instead of crashing."""

    @wraps(fn)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            await fn(update, context)
        except httpx.HTTPStatusError as e:
            logger.warning("HTTP error: %s", e)
            await update.effective_message.reply_text(
                f"⚠️ The service returned an error ({e.response.status_code}). Please try again later."
            )
        except httpx.RequestError as e:
            logger.warning("Network error: %s", e)
            await update.effective_message.reply_text("⚠️ Network problem. Please try again in a moment.")
        except Exception:
            logger.exception("Unhandled error in %s", fn.__name__)
            await update.effective_message.reply_text("⚠️ Something went wrong. Please try again.")

    return wrapper
