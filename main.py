import os
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import httpx
import feedparser

from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
FOOTBALL_API_KEY = os.getenv("FOOTBALL_DATA_API_KEY")

API_BASE = "https://api.football-data.org/v4"
TIMEZONE = ZoneInfo(os.getenv("TIMEZONE", "Africa/Lagos"))

NEWS_FEEDS = [
    "https://feeds.bbci.co.uk/sport/football/rss.xml",
    "https://www.skysports.com/rss/12040",
]

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


# ---------------- API CONNECTION ----------------

async def football_api(endpoint, params=None):
    headers = {"X-Auth-Token": FOOTBALL_API_KEY}

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(
                f"{API_BASE}/{endpoint.lstrip('/')}",
                headers=headers,
                params=params,
            )

            response.raise_for_status()
            return response.json()

    except httpx.HTTPStatusError as error:
        logger.error("Football API error: %s", error.response.text)
        return None

    except Exception:
        logger.exception("Football API connection failed")
        return None


# ---------------- MAIN MENU ----------------

def main_menu():
    keyboard = [
        [
            InlineKeyboardButton("📰 Football News", callback_data="news"),
            InlineKeyboardButton("🔴 Live Scores", callback_data="live"),
        ],
        [
            InlineKeyboardButton("📅 Today's Fixtures", callback_data="fixtures"),
            InlineKeyboardButton("🏆 Standings", callback_data="standings"),
        ],
        [
            InlineKeyboardButton("⚽ Match Results", callback_data="results"),
        ],
        [
            InlineKeyboardButton("🔍 Search Team", callback_data="team_help"),
            InlineKeyboardButton("ℹ️ Help", callback_data="help"),
        ],
    ]

    return InlineKeyboardMarkup(keyboard)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = (
        "⚽ <b>WELCOME TO FOOTBALL CENTRAL!</b>\n\n"
        "Your home for football news, scores, fixtures and results.\n\n"
        "Choose an option below to get started."
    )

    await update.message.reply_text(
        message,
        parse_mode="HTML",
        reply_markup=main_menu(),
    )


# ---------------- FOOTBALL NEWS ----------------

async def get_news(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message

    await message.reply_text("📰 Fetching the latest football news...")

    articles = []

    for feed_url in NEWS_FEEDS:
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.get(feed_url)
                response.raise_for_status()

            feed = feedparser.parse(response.text)

            for entry in feed.entries[:5]:
                articles.append({
                    "title": entry.get("title", "Football News"),
                    "link": entry.get("link", ""),
                    "summary": entry.get("summary", ""),
                    "published": entry.get("published", ""),
                })

        except Exception:
            logger.exception("News feed error")

    if not articles:
        await message.reply_text(
            "Sorry, football news is temporarily unavailable."
        )
        return

    seen = set()
    count = 0

    for article in articles:
        title = article["title"]
        link = article["link"]

        if title in seen:
            continue

        seen.add(title)
        count += 1

        summary = article["summary"]
        summary = summary.replace("<p>", "").replace("</p>", "")
        summary = summary[:300]

        text = (
            f"📰 <b>{title}</b>\n\n"
            f"{summary}\n\n"
            f"📅 {article['published']}\n"
        )

        if link.startswith(("http://", "https://")):
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("Read Full Story ↗", url=link)]
            ])

            await message.reply_text(
                text,
                parse_mode="HTML",
                reply_markup=keyboard,
            )
        else:
            await message.reply_text(text, parse_mode="HTML")

        if count >= 10:
            break


# ---------------- MATCH FORMATTING ----------------

def format_match(match):
    home = match.get("homeTeam", {}).get("name", "Home")
    away = match.get("awayTeam", {}).get("name", "Away")

    score = match.get("score", {}).get("fullTime", {})

    home_score = score.get("home")
    away_score = score.get("away")

    if home_score is None or away_score is None:
        score_text = "vs"
    else:
        score_text = f"{home_score} - {away_score}"

    status = match.get("status", "UNKNOWN")
    competition = match.get("competition", {}).get("name", "Football")

    kickoff = match.get("utcDate", "")

    try:
        dt = datetime.fromisoformat(kickoff.replace("Z", "+00:00"))
        kickoff = dt.astimezone(TIMEZONE).strftime("%d %b, %H:%M")
    except Exception:
        pass

    minute = match.get("minute")

    if minute:
        status = f"{minute}'"

    return (
        f"⚽ <b>{home}</b> {score_text} <b>{away}</b>\n"
        f"🏆 {competition}\n"
        f"🕒 {kickoff}\n"
        f"📌 {status}\n"
    )


# ---------------- LIVE SCORES ----------------

async def live_scores(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message

    await message.reply_text("🔴 Checking live matches...")

    data = await football_api("matches", {
        "status": "LIVE,IN_PLAY,PAUSED"
    })

    matches = data.get("matches", []) if data else []

    if not matches:
        await message.reply_text("⚽ No live matches found right now.")
        return

    for match in matches[:20]:
        await message.reply_text(
            "🔴 <b>LIVE MATCH</b>\n\n" + format_match(match),
            parse_mode="HTML",
        )


# ---------------- TODAY'S FIXTURES ----------------

async def fixtures(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message

    today = datetime.now(TIMEZONE).date()

    data = await football_api("matches", {
        "dateFrom": today.isoformat(),
        "dateTo": today.isoformat(),
    })

    matches = data.get("matches", []) if data else []

    if not matches:
        await message.reply_text("📅 No fixtures available for today.")
        return

    await message.reply_text("📅 <b>TODAY'S FOOTBALL FIXTURES</b>",
                             parse_mode="HTML")

    for match in matches[:30]:
        await message.reply_text(
            format_match(match),
            parse_mode="HTML",
        )


# ---------------- MATCH RESULTS ----------------

async def results(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message

    today = datetime.now(TIMEZONE).date()

    data = await football_api("matches", {
        "dateFrom": (today - timedelta(days=1)).isoformat(),
        "dateTo": today.isoformat(),
        "status": "FINISHED",
    })

    matches = data.get("matches", []) if data else []

    if not matches:
        await message.reply_text("⚽ No recent completed matches found.")
        return

    await message.reply_text("🏁 <b>RECENT MATCH RESULTS</b>",
                             parse_mode="HTML")

    for match in matches[:30]:
        await message.reply_text(
            format_match(match),
            parse_mode="HTML",
        )


# ---------------- LEAGUE STANDINGS ----------------

async def standings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message

    keyboard = [
        [
            InlineKeyboardButton("Premier League", callback_data="league_PL"),
            InlineKeyboardButton("La Liga", callback_data="league_PD"),
        ],
        [
            InlineKeyboardButton("Bundesliga", callback_data="league_BL1"),
            InlineKeyboardButton("Serie A", callback_data="league_SA"),
        ],
        [
            InlineKeyboardButton("Ligue 1", callback_data="league_FL1"),
            InlineKeyboardButton("Champions League", callback_data="league_CL"),
        ],
    ]

    await message.reply_text(
        "🏆 Select a competition:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def show_standings(query, code):
    data = await football_api(f"competitions/{code}/standings")

    if not data:
        await query.message.reply_text(
            "Unable to retrieve standings. This competition may not be "
            "included in your API subscription."
        )
        return

    tables = data.get("standings", [])

    total_table = next(
        (table for table in tables if table.get("type") == "TOTAL"),
        None,
    )

    if not total_table:
        await query.message.reply_text("No standings available.")
        return

    competition = data.get("competition", {}).get("name", code)

    text = f"🏆 <b>{competition} TABLE</b>\n\n"

    for team in total_table.get("table", [])[:20]:
        name = team.get("team", {}).get("name", "Unknown")

        text += (
            f"{team.get('position')}. {name}\n"
            f"   P: {team.get('playedGames')} | "
            f"W: {team.get('won')} | "
            f"D: {team.get('draw')} | "
            f"L: {team.get('lost')} | "
            f"Pts: {team.get('points')}\n\n"
        )

    await query.message.reply_text(text, parse_mode="HTML")


# ---------------- TEAM SEARCH ----------------

async def search_team(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "Use this format:\n/team 57\n\n"
            "Replace 57 with a football-data.org team ID."
        )
        return

    team_id = context.args[0]

    if not team_id.isdigit():
        await update.message.reply_text("Please enter a valid numeric team ID.")
        return

    data = await football_api(f"teams/{team_id}")

    if not data:
        await update.message.reply_text(
            "Team not found or unavailable with your API plan."
        )
        return

    name = data.get("name", "Unknown")
    country = data.get("area", {}).get("name", "Unknown")
    venue = data.get("venue") or "Not available"

    await update.message.reply_text(
        f"⚽ <b>{name}</b>\n\n"
        f"🌍 Country: {country}\n"
        f"🏟 Stadium: {venue}\n"
        f"🌐 Website: {data.get('website') or 'Not available'}",
        parse_mode="HTML",
    )


# ---------------- BUTTON HANDLER ----------------

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    action = query.data

    if action == "news":
        await get_news(update, context)

    elif action == "live":
        await live_scores(update, context)

    elif action == "fixtures":
        await fixtures(update, context)

    elif action == "standings":
        await standings(update, context)

    elif action == "results":
        await results(update, context)

    elif action.startswith("league_"):
        code = action.replace("league_", "")
        await show_standings(query, code)

    elif action == "team_help":
        await query.message.reply_text(
            "🔍 Search for a team using its football-data.org ID.\n\n"
            "Example: /team 57"
        )

    elif action == "help":
        await query.message.reply_text(
            "⚽ FOOTBALL CENTRAL COMMANDS\n\n"
            "/start - Main menu\n"
            "/news - Latest football news\n"
            "/live - Live scores\n"
            "/fixtures - Today's fixtures\n"
            "/standings - League tables\n"
            "/results - Match results\n"
            "/team ID - Team information"
        )


# ---------------- APPLICATION ----------------

async def post_init(application):
    commands = [
        ("start", "Open the main menu"),
        ("news", "Latest football news"),
        ("live", "Live football scores"),
        ("fixtures", "Today's fixtures"),
        ("standings", "League standings"),
        ("results", "Recent match results"),
        ("team", "Search team by ID"),
    ]

    from telegram import BotCommand
    await application.bot.set_my_commands([
        BotCommand(command, description)
        for command, description in commands
    ])


def main():
    if not BOT_TOKEN or not FOOTBALL_API_KEY:
        raise ValueError(
            "Missing TELEGRAM_BOT_TOKEN or FOOTBALL_DATA_API_KEY."
        )

    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("news", get_news))
    application.add_handler(CommandHandler("live", live_scores))
    application.add_handler(CommandHandler("fixtures", fixtures))
    application.add_handler(CommandHandler("standings", standings))
    application.add_handler(CommandHandler("results", results))
    application.add_handler(CommandHandler("team", search_team))
    application.add_handler(CallbackQueryHandler(button_handler))

    logger.info("Football Central Bot is starting...")

    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
