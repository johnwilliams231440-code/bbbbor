import html
from urllib.parse import quote

import feedparser
from telegram import Update
from telegram.ext import ContextTypes

from utils import fetch, safe, send

# ---------------------------------------------------------------- WEATHER
WMO = {
    0: "☀️ Clear sky", 1: "🌤️ Mostly clear", 2: "⛅ Partly cloudy", 3: "☁️ Overcast",
    45: "🌫️ Fog", 48: "🌫️ Fog", 51: "🌦️ Light drizzle", 53: "🌦️ Drizzle", 55: "🌦️ Heavy drizzle",
    61: "🌧️ Light rain", 63: "🌧️ Rain", 65: "🌧️ Heavy rain", 71: "🌨️ Light snow", 73: "🌨️ Snow",
    75: "❄️ Heavy snow", 80: "🌦️ Rain showers", 81: "🌧️ Rain showers", 82: "⛈️ Violent showers",
    95: "⛈️ Thunderstorm", 96: "⛈️ Thunderstorm + hail", 99: "⛈️ Thunderstorm + hail",
}


@safe
async def weather(update: Update, context: ContextTypes.DEFAULT_TYPE):
    city = " ".join(context.args).strip()
    if not city:
        await send(update, "Usage: <code>/weather Lagos</code>")
        return

    geo = await fetch(
        "https://geocoding-api.open-meteo.com/v1/search",
        params={"name": city, "count": 1},
    )
    if not geo.get("results"):
        await send(update, f"❌ I couldn't find <b>{html.escape(city)}</b>.")
        return
    place = geo["results"][0]

    data = await fetch(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": place["latitude"],
            "longitude": place["longitude"],
            "current": "temperature_2m,apparent_temperature,relative_humidity_2m,wind_speed_10m,weather_code",
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
            "timezone": "auto",
            "forecast_days": 3,
        },
    )
    cur = data["current"]
    daily = data["daily"]
    name = f"{place['name']}, {place.get('country', '')}"

    text = (
        f"🌍 <b>Weather in {html.escape(name)}</b>\n\n"
        f"{WMO.get(cur['weather_code'], '🌡️')}\n"
        f"🌡️ {cur['temperature_2m']}°C (feels like {cur['apparent_temperature']}°C)\n"
        f"💧 Humidity: {cur['relative_humidity_2m']}%\n"
        f"💨 Wind: {cur['wind_speed_10m']} km/h\n\n"
        f"📅 <b>3-day forecast</b>\n"
    )
    for i in range(len(daily["time"])):
        text += (
            f"{daily['time'][i]}: {WMO.get(daily['weather_code'][i], '')} "
            f"{daily['temperature_2m_min'][i]}° / {daily['temperature_2m_max'][i]}° "
            f"☔ {daily['precipitation_probability_max'][i]}%\n"
        )
    await send(update, text)


# ----------------------------------------------------------------- CRYPTO
COINS = {
    "btc": "bitcoin", "eth": "ethereum", "usdt": "tether", "bnb": "binancecoin",
    "sol": "solana", "xrp": "ripple", "ada": "cardano", "doge": "dogecoin",
    "ton": "the-open-network", "trx": "tron", "dot": "polkadot", "ltc": "litecoin",
    "matic": "matic-network", "shib": "shiba-inu", "usdc": "usd-coin",
}


@safe
async def crypto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    symbols = [a.lower() for a in context.args] or ["btc", "eth", "bnb", "sol", "xrp"]
    symbols = symbols[:8]
    ids = [COINS.get(s, s) for s in symbols]

    data = await fetch(
        "https://api.coingecko.com/api/v3/simple/price",
        params={
            "ids": ",".join(ids),
            "vs_currencies": "usd,ngn",
            "include_24hr_change": "true",
        },
    )
    if not data:
        await send(update, "❌ No coins found. Try <code>/crypto btc eth</code>")
        return

    lines = ["💰 <b>Crypto prices</b>\n"]
    for sym, cid in zip(symbols, ids):
        info = data.get(cid)
        if not info:
            lines.append(f"• {html.escape(sym.upper())}: not found")
            continue
        change = info.get("usd_24h_change") or 0
        arrow = "🟢" if change >= 0 else "🔴"
        lines.append(
            f"{arrow} <b>{html.escape(sym.upper())}</b>: ${info['usd']:,} "
            f"(₦{info.get('ngn', 0):,.0f}) {change:+.2f}% 24h"
        )
    await send(update, "\n".join(lines))


# --------------------------------------------------------------- CURRENCY
@safe
async def convert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 3:
        await send(update, "Usage: <code>/convert 100 USD NGN</code>")
        return
    try:
        amount = float(context.args[0].replace(",", ""))
    except ValueError:
        await send(update, "❌ The amount must be a number. Example: <code>/convert 100 USD NGN</code>")
        return
    src = context.args[1].upper()
    dst = context.args[2].upper()

    data = await fetch(f"https://open.er-api.com/v6/latest/{src}")
    if data.get("result") != "success" or dst not in data.get("rates", {}):
        await send(update, "❌ Unknown currency code. Use codes like USD, EUR, GBP, NGN.")
        return
    rate = data["rates"][dst]
    await send(
        update,
        f"💱 <b>{amount:,.2f} {src} = {amount * rate:,.2f} {dst}</b>\n"
        f"Rate: 1 {src} = {rate:,.4f} {dst}",
    )


# ------------------------------------------------------------------- NEWS
FEEDS = {
    "top": "https://feeds.bbci.co.uk/news/rss.xml",
    "world": "https://feeds.bbci.co.uk/news/world/rss.xml",
    "africa": "https://feeds.bbci.co.uk/news/world/africa/rss.xml",
    "business": "https://feeds.bbci.co.uk/news/business/rss.xml",
    "tech": "https://feeds.bbci.co.uk/news/technology/rss.xml",
    "sport": "https://feeds.bbci.co.uk/sport/rss.xml",
    "football": "https://feeds.bbci.co.uk/sport/football/rss.xml",
}


@safe
async def news(update: Update, context: ContextTypes.DEFAULT_TYPE):
    topic = context.args[0].lower() if context.args else "top"
    if topic not in FEEDS:
        await send(update, "Topics: " + ", ".join(f"<code>{t}</code>" for t in FEEDS) + "\nExample: <code>/news tech</code>")
        return
    raw = await fetch(FEEDS[topic], as_text=True)
    feed = feedparser.parse(raw)
    if not feed.entries:
        await send(update, "❌ No news available right now.")
        return
    lines = [f"📰 <b>{topic.title()} news</b>\n"]
    for e in feed.entries[:7]:
        lines.append(f"• <a href=\"{html.escape(e.link)}\">{html.escape(e.title)}</a>")
    await send(update, "\n".join(lines))


# ---------------------------------------------------------- INSTANT ANSWER
@safe
async def ask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = " ".join(context.args).strip()
    if not query:
        await send(update, "Usage: <code>/ask who is Chinua Achebe</code>")
        return

    search = await fetch(
        "https://en.wikipedia.org/w/api.php",
        params={"action": "opensearch", "search": query, "limit": 1, "format": "json"},
    )
    titles = search[1] if len(search) > 1 else []
    if not titles:
        await send(update, "❌ I couldn't find an answer for that. Try rephrasing.")
        return

    summary = await fetch(
        f"https://en.wikipedia.org/api/rest_v1/page/summary/{quote(titles[0].replace(' ', '_'))}"
    )
    extract = summary.get("extract", "No summary available.")
    if len(extract) > 900:
        extract = extract[:900].rsplit(" ", 1)[0] + "…"
    url = summary.get("content_urls", {}).get("desktop", {}).get("page", "")
    text = f"📚 <b>{html.escape(summary.get('title', titles[0]))}</b>\n\n{html.escape(extract)}"
    if url:
        text += f"\n\n<a href=\"{html.escape(url)}\">Read more</a>"
    await send(update, text)
