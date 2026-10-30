import logging

from telegram import BotCommand, Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes

import config
from features import football, info, tools

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

HELP_TEXT = """🤖 <b>All-in-One Assistant</b>

⚽ <b>Football</b>
/scores – today's matches &amp; scores
/live – matches in play right now
/fixtures [league] – upcoming games
/results [league] – latest results
/table [league] – league standings
<i>Leagues: pl, laliga, seriea, bundesliga, ligue1, ucl</i>

📰 <b>News &amp; Answers</b>
/news [topic] – top, world, africa, business, tech, sport, football
/ask &lt;question&gt; – instant answers

🌍 <b>Info</b>
/weather &lt;city&gt; – forecast
/crypto [btc eth ...] – prices (USD &amp; NGN)
/convert &lt;amount&gt; &lt;from&gt; &lt;to&gt; – currency converter
/time [city] – world time zones
/translate &lt;lang&gt; &lt;text&gt; – translate text
/languages – supported languages

🛠 <b>Tools</b>
/qr &lt;text&gt; – generate a QR code
/password [length] – secure password
"""


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.effective_user.first_name if update.effective_user else "there"
    await update.effective_message.reply_text(
        f"👋 Hi {name}!\n\n" + HELP_TEXT, parse_mode=ParseMode.HTML
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(HELP_TEXT, parse_mode=ParseMode.HTML)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error("Unhandled exception", exc_info=context.error)


async def post_init(app: Application):
    await app.bot.set_my_commands(
        [
            BotCommand("start", "Start the bot"),
            BotCommand("help", "Show all features"),
            BotCommand("scores", "Today's football scores"),
            BotCommand("live", "Live matches"),
            BotCommand("fixtures", "Upcoming fixtures"),
            BotCommand("results", "Latest results"),
            BotCommand("table", "League table"),
            BotCommand("news", "Breaking news"),
            BotCommand("ask", "Instant answers"),
            BotCommand("weather", "Weather forecast"),
            BotCommand("crypto", "Crypto prices"),
            BotCommand("convert", "Currency converter"),
            BotCommand("time", "World time zones"),
            BotCommand("translate", "Translate text"),
            BotCommand("languages", "Supported languages"),
            BotCommand("qr", "Generate a QR code"),
            BotCommand("password", "Generate a secure password"),
        ]
    )


def main():
    app = Application.builder().token(config.BOT_TOKEN).post_init(post_init).build()

    handlers = {
        "start": start,
        "help": help_cmd,
        # football
        "scores": football.scores,
        "live": football.live,
        "fixtures": football.fixtures,
        "results": football.results,
        "table": football.table,
        # info
        "news": info.news,
        "ask": info.ask,
        "weather": info.weather,
        "crypto": info.crypto,
        "convert": info.convert,
        # tools
        "time": tools.time_cmd,
        "translate": tools.translate,
        "languages": tools.languages,
        "qr": tools.qr,
        "password": tools.password,
    }
    for command, fn in handlers.items():
        app.add_handler(CommandHandler(command, fn))
    app.add_error_handler(error_handler)

    if config.WEBHOOK_URL:
        logger.info("Starting in WEBHOOK mode on port %s", config.PORT)
        app.run_webhook(
            listen="0.0.0.0",
            port=config.PORT,
            url_path=config.BOT_TOKEN,
            webhook_url=f"{config.WEBHOOK_URL}/{config.BOT_TOKEN}",
            drop_pending_updates=True,
        )
    else:
        logger.info("Starting in POLLING mode (local)")
        app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
