import os

BOT_TOKEN = os.environ["BOT_TOKEN"]
FOOTBALL_API_KEY = os.getenv("FOOTBALL_API_KEY", "")
PORT = int(os.getenv("PORT", "10000"))

# Render sets RENDER_EXTERNAL_URL automatically for Web Services.
# If it's missing (e.g. running locally) the bot falls back to polling.
WEBHOOK_URL = (os.getenv("RENDER_EXTERNAL_URL") or os.getenv("WEBHOOK_URL", "")).rstrip("/")
