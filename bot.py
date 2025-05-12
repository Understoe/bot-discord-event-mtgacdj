import discord
import requests
from bs4 import BeautifulSoup
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import os
import sys
import datetime
import locale

TOKEN = os.getenv("TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

if not TOKEN or not CHANNEL_ID:
    print("❌ TOKEN ou CHANNEL_ID manquant.")
    sys.exit(1)

CHANNEL_ID = int(CHANNEL_ID)

# Tags suivis et leurs rôles Discord (ID numériques à récupérer dans Discord)
ROLE_IDS = {
    "MTG : Commander Multi": 1067857193673699429,
    "MTG : Modern": 1067857029470896178,
    "MTG : Standard": 1067857092561608764,
    "MTG : Pioneer": 1067857419369205951,
    "MTG : Duel Commander": 1067857231288217681,
    "MTG : Pauper": 1067857461417099314,
    "MTG : Limité": 1067857130176118855,
}

intents = discord.Intents.default()
client = discord.Client(intents=intents)
scheduler = AsyncIOScheduler()

# Assure le format français pour les dates
try:
    locale.setlocale(locale.LC_TIME, 'fr_FR.utf8')
except locale.Error:
    print("⚠️ Impossible d'utiliser la locale 'fr_FR.utf8'. Le nom du mois pourrait ne pas être en français.")


def get_events():
    url = "https://au-coin-du-jeu.odoo.com/event"
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")

    events = []
    event_blocks = soup.find_all("div", class_="col-md-6 col-lg-4 col-xl-3")
    print(f"[DEBUG] Nombre total de blocs trouvés : {len(event_blocks)}")

    for block in event_blocks:
        try:
            tags = block.find_all("span", class_="badge")
            tag_texts = [tag.get_text(strip=True) for tag in tags]
            if "Magic The Gathering" not in tag_texts:
                continue

            name_tag = block.find("span", itemprop="name")
            title = name_tag.get_text(strip=True) if name_tag else "Sans titre"

            day_tag = block.find("span", class_="o_wevent_event_day")
            month_tag = block.find("span", class_="o_wevent_event_month")
            day = day_tag.get_text(strip=True) if day_tag else "?"
            month = month_tag.get_text(strip=True) if month_tag else "?"

            try:
                full_date_str = f"{day} {month} {datetime.datetime.now().year}"
                event_date = datetime.datetime.strptime(full_date_str, "%d %B %Y")
            except ValueError:
                print(f"[ERREUR] Date invalide : {full_date_str}")
                continue

            days_until = (event_date - datetime.datetime.now()).days
            if days_until < 0 and days_until > 20:
                print(f"[DEBUG] Événement ignoré (dans {days_until} jours) : {title}")
                continue

            # Trouve le tag Magic spécifique (autre que Magic The Gathering)
            specific_tag = next((t for t in tag_texts if t != "Magic The Gathering"), None)
            role = TAG_ROLES.get(specific_tag, "")

            cover_div = block.find("div", class_="o_record_cover_image")
            style_attr = cover_div.get("style", "") if cover_div else ""
            image_url = None
            if "background-image" in style_attr:
                start = style_attr.find("url(") + 4
                end = style_attr.find(")", start)
                image_url = "https://au-coin-du-jeu.odoo.com" + style_attr[start:end]

            events.append({
                "title": title,
                "date": event_date.strftime("%d %B"),
                "image": image_url,
                "role": role
            })

            print(f"[DEBUG] Événement ajouté : {title} | {event_date.strftime('%d %B')} | {image_url}")

        except Exception as e:
            print(f"[ERREUR traitement bloc] {e}")

    print(f"[DEBUG] Nombre d'événements Magic filtrés : {len(events)}")
    return events


async def envoyer_evenements():
    channel = client.get_channel(CHANNEL_ID)
    if not channel:
        print("❌ Salon introuvable. Vérifiez le CHANNEL_ID.")
        return

    events = get_events()
    if not events:
        print("ℹ️ Aucun événement Magic trouvé.")
        return

    for ev in events:
        embed = discord.Embed(
            title=ev["title"],
            description=f"📅 {ev['date']}",
            color=discord.Color.blue()
        )
        if ev["image"]:
            embed.set_image(url=ev["image"])

        await channel.send(content=ev["role"], embed=embed)


@client.event
async def on_ready():
    print(f"✅ Connecté en tant que {client.user}")
    scheduler.add_job(envoyer_evenements, 'cron', day_of_week='mon', hour=7, minute=0)
    scheduler.start()
    await envoyer_evenements()

client.run(TOKEN)

