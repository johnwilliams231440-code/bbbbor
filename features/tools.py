import asyncio
import io
import secrets
import string
from datetime import datetime
from zoneinfo import ZoneInfo, available_timezones

import qrcode
from deep_translator import GoogleTranslator
from telegram import Update
from telegram.ext import ContextTypes

from utils import safe, send


# ---------------------------------------------------------------- QR CODE
@safe
async def qr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = " ".join(context.args).strip()
    if not text:
        await send(update, "Usage: <code>/qr your text or link</code>")
        return
    img = qrcode.make(text)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    await update.effective_message.reply_photo(buf, caption="✅ Your QR code")


# --------------------------------------------------------------- PASSWORD
@safe
async def password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    length = 16
    if context.args:
        try:
            length = int(context.args[0])
        except ValueError:
            await send(update, "Usage: <code>/password 16</code> (length 8-64)")
            return
    length = max(8, min(length, 64))

    alphabet = string.ascii_letters + string.digits + "!@#$%^&*()-_=+?"
    while True:
        pwd = "".join(secrets.choice(alphabet) for _ in range(length))
        if (
            any(c.islower() for c in pwd)
            and any(c.isupper() for c in pwd)
            and any(c.isdigit() for c in pwd)
            and any(c in "!@#$%^&*()-_=+?" for c in pwd)
        ):
            break
    await send(update, f"🔐 Your secure password ({length} chars):\n\n<code>{pwd}</code>\n\nTap to copy. Don't reuse it anywhere else.")


# --------------------------------------------------------------- TIMEZONE
DEFAULT_ZONES = [
    ("Lagos", "Africa/Lagos"),
    ("London", "Europe/London"),
    ("New York", "America/New_York"),
    ("Dubai", "Asia/Dubai"),
    ("Mumbai", "Asia/Kolkata"),
    ("Tokyo", "Asia/Tokyo"),
    ("Sydney", "Australia/Sydney"),
]

ALIASES = {
    "nigeria": "Africa/Lagos",
    "uk": "Europe/London",
    "usa": "America/New_York",
    "india": "Asia/Kolkata",
    "china": "Asia/Shanghai",
    "japan": "Asia/Tokyo",
    "ghana": "Africa/Accra",
    "kenya": "Africa/Nairobi",
    "south africa": "Africa/Johannesburg",
    "egypt": "Africa/Cairo",
    "uae": "Asia/Dubai",
    "france": "Europe/Paris",
    "germany": "Europe/Berlin",
    "spain": "Europe/Madrid",
    "brazil": "America/Sao_Paulo",
    "canada": "America/Toronto",
    "australia": "Australia/Sydney",
}


def _find_zone(query: str):
    q = query.strip().lower()
    if q in ALIASES:
        return ALIASES[q]
    q = q.replace(" ", "_")
    zones = available_timezones()
    for z in zones:
        if z.lower() == q:
            return z
    for z in sorted(zones):
        if z.lower().endswith("/" + q):
            return z
    return None


def _fmt_zone(name: str, zone: str) -> str:
    now = datetime.now(ZoneInfo(zone))
    return f"🕒 <b>{name}</b>: {now.strftime('%a %d %b, %H:%M')} (UTC{now.strftime('%z')[:3]}:{now.strftime('%z')[3:]})"


@safe
async def time_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        lines = [_fmt_zone(n, z) for n, z in DEFAULT_ZONES]
        await send(update, "🌍 <b>World clock</b>\n\n" + "\n".join(lines) + "\n\nTry: <code>/time Tokyo</code>")
        return
    query = " ".join(context.args)
    zone = _find_zone(query)
    if not zone:
        await send(update, f"❌ I couldn't find <b>{query}</b>. Try a city like <code>/time Paris</code> or a zone like <code>/time Africa/Lagos</code>.")
        return
    await send(update, _fmt_zone(zone.split("/")[-1].replace("_", " "), zone))


# -------------------------------------------------------------- TRANSLATE
LANGS = {
    "english": "en", "french": "fr", "spanish": "es", "german": "de", "arabic": "ar",
    "yoruba": "yo", "hausa": "ha", "igbo": "ig", "portuguese": "pt", "chinese": "zh-CN",
    "hindi": "hi", "russian": "ru", "japanese": "ja", "swahili": "sw", "italian": "it",
    "turkish": "tr", "korean": "ko", "dutch": "nl", "zulu": "zu", "amharic": "am",
}


@safe
async def translate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await send(
            update,
            "Usage: <code>/translate fr Hello, how are you?</code>\n"
            "You can use a code (<code>fr</code>) or a name (<code>french</code>).\n"
            "Send /languages to see the list.",
        )
        return
    target = context.args[0].lower()
    target = LANGS.get(target, target)
    text = " ".join(context.args[1:])
    try:
        result = await asyncio.to_thread(
            lambda: GoogleTranslator(source="auto", target=target).translate(text)
        )
    except Exception:
        await send(update, "❌ Translation failed. Check the language code with /languages.")
        return
    await send(update, f"🌐 <b>Translation ({target})</b>\n\n{result}")


@safe
async def languages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lines = [f"<code>{code}</code> – {name.title()}" for name, code in sorted(LANGS.items())]
    await send(update, "🌐 <b>Popular languages</b>\n\n" + "\n".join(lines) + "\n\nOther standard codes also work.")
