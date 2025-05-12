import discord
import requests
from bs4 import BeautifulSoup
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import os
import sys

TOKEN = os.getenv("TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

if not TOKEN or not CHANNEL_ID:
    print("❌ TOKEN ou CHANNEL_ID manquant.")
    sys.exit(1)

CHANNEL_ID = int(CHANNEL_ID)

TAG_ROLES = {
    "MTG : Commander Multi": "@Commander EDH",
    "MTG : Modern": "@Modern",
    "MTG : Standard": "@Standard",
    "MTG : Pioneer": "@Pioneer",
    "MTG : Duel Commander": "@Duel Commander",
    "MTG : Pauper": "@Pauper",
    "MTG : Limité": "@Limité"
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
            tags = block.find_all("span", class_="badge")
            tag_texts = [tag.get_text(strip=True) for tag in tags]

            if "Magic The Gathering" not in tag_texts:
                continue

            role = None
            for tag in tag_texts:
                if tag in TAG_ROLES:
                    role = TAG_ROLES[tag]
                    break

            if not role:
                continue

            name_tag = block.find("span", itemprop="name")
            title = name_tag.get_text(strip=True) if name_tag else "Sans titre"

            day_tag = block.find("span", class_="o_wevent_event_day")
            month_tag = block.find("span", class_="o_wevent_event_month")
            day = day_tag.get_text(strip=True) if day_tag else "?"
            month = month_tag.get_text(strip=True) if month_tag else "?"

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
                "role": role
            })

            print(f"[DEBUG] Événement ajouté : {title} | {day} {month} | {role}")

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

        print(f"[DEBUG] Envoi de l'événement : {ev['title']} | Rôle : {ev['role']}")
        await channel.send(content=ev["role"], embed=embed)


@client.event
async def on_ready():
    print(f"✅ Connecté en tant que {client.user}")
    scheduler.add_job(envoyer_evenements, 'cron', day_of_week='mon', hour=9, minute=0)
    scheduler.start()

    await envoyer_evenements()


client.run(TOKEN)

