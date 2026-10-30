import html
from collections import defaultdict
from datetime import datetime

from telegram import Update
from telegram.ext import ContextTypes

from config import FOOTBALL_API_KEY
from utils import fetch, safe, send

BASE = "https://api.football-data.org/v4"

LEAGUES = {
    "pl": "PL", "epl": "PL", "premier": "PL",
    "laliga": "PD", "liga": "PD",
    "seriea": "SA", "serie": "SA",
    "bundesliga": "BL1",
    "ligue1": "FL1",
    "ucl": "CL", "cl": "CL",
    "championship": "ELC",
    "eredivisie": "DED",
    "primeira": "PPL",
    "wc": "WC",
}
LEAGUE_HELP = "pl, laliga, seriea, bundesliga, ligue1, ucl, championship, eredivisie, primeira"


async def _api(path: str, params=None):
    return await fetch(f"{BASE}{path}", params=params, headers={"X-Auth-Token": FOOTBALL_API_KEY})


def _league(context) -> str:
    key = context.args[0].lower() if context.args else "pl"
    return LEAGUES.get(key, key.upper())


def _name(team: dict) -> str:
    return html.escape(team.get("shortName") or team.get("name") or "TBD")


def _fmt_match(m: dict) -> str:
    status = m["status"]
    ft = m["score"]["fullTime"]
    home, away = _name(m["homeTeam"]), _name(m["awayTeam"])

    if status in ("IN_PLAY", "PAUSED", "FINISHED") and ft["home"] is not None:
        tag = {"IN_PLAY": "🔴 LIVE", "PAUSED": "⏸ HT", "FINISHED": "✅ FT"}[status]
        return f"{tag}  {home} <b>{ft['home']} - {ft['away']}</b> {away}"

    if status in ("POSTPONED", "SUSPENDED", "CANCELLED"):
        return f"⚠️ {status.title()}  {home} vs {away}"

    kickoff = datetime.fromisoformat(m["utcDate"].replace("Z", "+00:00"))
    return f"⏰ {kickoff.strftime('%d %b %H:%M')} UTC  {home} vs {away}"


@safe
async def scores(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not FOOTBALL_API_KEY:
        await send(update, "⚠️ Football is not configured (missing FOOTBALL_API_KEY).")
        return
    data = await _api("/matches")
    matches = data.get("matches", [])
    if not matches:
        await send(update, "😴 No matches today in the covered competitions. Try /fixtures.")
        return
    grouped = defaultdict(list)
    for m in matches:
        grouped[m["competition"]["name"]].append(m)
    lines = ["⚽ <b>Today's matches</b>"]
    for comp, ms in grouped.items():
        lines.append(f"\n🏆 <b>{html.escape(comp)}</b>")
        lines.extend(_fmt_match(m) for m in ms)
    await send(update, "\n".join(lines))


@safe
async def live(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not FOOTBALL_API_KEY:
        await send(update, "⚠️ Football is not configured (missing FOOTBALL_API_KEY).")
        return
    data = await _api("/matches")
    ms = [m for m in data.get("matches", []) if m["status"] in ("IN_PLAY", "PAUSED")]
    if not ms:
        await send(update, "😴 No live matches right now. Use /scores to see today's games.")
        return
    lines = ["🔴 <b>Live now</b>\n"]
    lines.extend(f"{_fmt_match(m)}  <i>({html.escape(m['competition']['name'])})</i>" for m in ms)
    await send(update, "\n".join(lines))


@safe
async def fixtures(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not FOOTBALL_API_KEY:
        await send(update, "⚠️ Football is not configured (missing FOOTBALL_API_KEY).")
        return
    code = _league(context)
    data = await _api(f"/competitions/{code}/matches", {"status": "SCHEDULED,TIMED"})
    ms = data.get("matches", [])[:10]
    if not ms:
        await send(update, f"No upcoming fixtures found for <b>{code}</b>.\nLeagues: {LEAGUE_HELP}")
        return
    await send(update, f"📅 <b>Upcoming fixtures – {code}</b>\n\n" + "\n".join(_fmt_match(m) for m in ms))


@safe
async def results(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not FOOTBALL_API_KEY:
        await send(update, "⚠️ Football is not configured (missing FOOTBALL_API_KEY).")
        return
    code = _league(context)
    data = await _api(f"/competitions/{code}/matches", {"status": "FINISHED"})
    ms = data.get("matches", [])[-10:]
    if not ms:
        await send(update, f"No results found for <b>{code}</b>.\nLeagues: {LEAGUE_HELP}")
        return
    ms.reverse()
    await send(update, f"📊 <b>Latest results – {code}</b>\n\n" + "\n".join(_fmt_match(m) for m in ms))


@safe
async def table(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not FOOTBALL_API_KEY:
        await send(update, "⚠️ Football is not configured (missing FOOTBALL_API_KEY).")
        return
    code = _league(context)
    data = await _api(f"/competitions/{code}/standings")
    standings = data.get("standings", [])
    if not standings:
        await send(update, f"No table found for <b>{code}</b>.\nLeagues: {LEAGUE_HELP}")
        return
    rows = standings[0]["table"][:20]
    lines = [f"{'#':>2} {'Team':<14}{'P':>3}{'GD':>4}{'Pts':>4}"]
    for r in rows:
        team = (r["team"].get("shortName") or r["team"]["name"])[:13]
        lines.append(f"{r['position']:>2} {team:<14}{r['playedGames']:>3}{r['goalDifference']:>4}{r['points']:>4}")
    comp = html.escape(data.get("competition", {}).get("name", code))
    await send(update, f"🏆 <b>{comp} table</b>\n<pre>" + "\n".join(lines) + "</pre>")
