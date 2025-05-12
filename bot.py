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

def get_events():
    url = "https://au-coin-du-jeu.odoo.com/event"
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")

    events = []

    event_blocks = soup.find_all("div", class_="col-md-6 col-lg-4 col-xl-3")
    print(f"[DEBUG] Nombre total de blocs trouvés : {len(event_blocks)}")

    for block in event_blocks:
        try:
            # Vérifie qu'on est sur un événement Magic
            tags = block.find_all("span", class_="badge")
            tag_texts = [tag.get_text(strip=True) for tag in tags]
            if "Magic The Gathering" not in tag_texts:
                continue

            # Cherche un tag secondaire qui correspond à un de ceux qu'on suit
            tag_utilise = next((t for t in tag_texts if t in ROLE_IDS), None)
            if not tag_utilise:
                continue

            # Nom de l'événement
            name_tag = block.find("span", itemprop="name")
            title = name_tag.get_text(strip=True) if name_tag else "Sans titre"

            # Date
            day_tag = block.find("span", class_="o_wevent_event_day")
            month_tag = block.find("span", class_="o_wevent_event_month")
            day = day_tag.get_text(strip=True) if day_tag else "?"
            month = month_tag.get_text(strip=True) if month_tag else "?"

            # Image de couverture
            cover_div = block.find("div", class_="o_record_cover_image")
            style_attr = cover_div.get("style", "") if cover_div else ""
            image_url = None
            if "background-image" in style_attr:
                start = style_attr.find("url(") + 4
                end = style_attr.find(")", start)
                image_url = "https://au-coin-du-jeu.odoo.com" + style_attr[start:end]

            events.append({
                "title": title,
                "date": f"{day} {month}",
                "image": image_url,
                "role_id": ROLE_IDS[tag_utilise]
            })

            print(f"[DEBUG] Événement ajouté : {title} | {day} {month} | Tag : {tag_utilise}")

        except Exception as e:
            print(f"[ERREUR traitement bloc] {e}")

    print(f"[DEBUG] Nombre d'événements Magic trouvés : {len(events)}")
    return events

async def envoyer_evenements():
    channel = client.get_channel(CHANNEL_ID)
    print(f"[DEBUG] Channel récupéré : {channel}")

    if not channel:
        print("❌ Salon introuvable. Vérifiez le CHANNEL_ID.")
        return

    # Effacer les anciens messages
    async for message in channel.history(limit=100):  # 'limit=100' pour éviter de supprimer trop de messages
        await message.delete()
        
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

        await channel.send(
            content=f"<@&{ev['role_id']}>",
            embed=embed,
            allowed_mentions=discord.AllowedMentions(roles=True)
        )
        print(f"[DEBUG] Message envoyé pour : {ev['title']}")

@client.event
async def on_ready():
    print(f"✅ Connecté en tant que {client.user}")
    scheduler.add_job(envoyer_evenements, 'cron', day_of_week='mon', hour=12, minute=14)
    scheduler.start()

    # Envoi immédiat pour test
    #await envoyer_evenements()

client.run(TOKEN)

