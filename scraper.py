import requests
from bs4 import BeautifulSoup
import sqlite3
import datetime
import time
from urllib.parse import quote_plus
import re
import os
import smtplib
from dotenv import load_dotenv
import logging

# Chargement des variables d'environnement
load_dotenv()

# Configuration logs
logging.basicConfig(
    filename="logs_scraper.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Paramètres de scraping
QUERY = "developpeur web"
LOCATION = "France"
BASE_URL = f"https://fr.indeed.com/jobs?q={quote_plus(QUERY)}&l={quote_plus(LOCATION)}"
DB_PATH = "annonces.db"
HTML_OUTPUT_PATH = "templates/index.html"

# Création du dossier templates
os.makedirs("templates", exist_ok=True)

# Connexion globale à SQLite
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# Création de la table si elle n'existe pas
c.execute('''
CREATE TABLE IF NOT EXISTS annonces (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    titre TEXT,
    entreprise TEXT,
    lieu TEXT,
    date_pub TEXT,
    url TEXT UNIQUE,
    last_seen TEXT
)
''')
conn.commit()

def convertir_date_relative(texte):
    maintenant = datetime.datetime.now()

    if "aujourd" in texte.lower():
        return maintenant.date().isoformat()
    if "hier" in texte.lower():
        return (maintenant - datetime.timedelta(days=1)).date().isoformat()

    match = re.search(r"il y a (\d+) (\w+)", texte.lower())
    if match:
        valeur = int(match.group(1))
        unite = match.group(2)
        if "jour" in unite:
            return (maintenant - datetime.timedelta(days=valeur)).date().isoformat()
        elif "heure" in unite:
            return (maintenant - datetime.timedelta(hours=valeur)).date().isoformat()
        elif "minute" in unite:
            return (maintenant - datetime.timedelta(minutes=valeur)).date().isoformat()

    return texte  # fallback

def get_annonces():
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        r = requests.get(BASE_URL, headers=headers)
        r.raise_for_status()
    except requests.RequestException as e:
        logging.error(f"Erreur réseau : {e}")
        return []

    soup = BeautifulSoup(r.text, 'html.parser')
    annonces = []

    for card in soup.select('.resultContent'):
        try:
            titre = card.select_one('h2.jobTitle').text.strip()
            entreprise = card.select_one('.companyName').text.strip()
            lieu = card.select_one('.companyLocation').text.strip()
            url = 'https://fr.indeed.com' + card.find_parent('a')['href']
            span = card.find_next('span', string=lambda x: x and 'il y a' in x.lower())
            date_pub = convertir_date_relative(span.text.strip()) if span else "inconnue"

            annonces.append({
                'titre': titre,
                'entreprise': entreprise,
                'lieu': lieu,
                'url': url,
                'date_pub': date_pub,
                'last_seen': datetime.datetime.now().isoformat()
            })
        except Exception as e:
            logging.warning(f"Erreur parsing carte : {e}")
            continue

    return annonces

def save_annonces(annonces):
    nouvelles = []
    for a in annonces:
        try:
            c.execute('''
                INSERT INTO annonces (titre, entreprise, lieu, date_pub, url, last_seen)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (a['titre'], a['entreprise'], a['lieu'], a['date_pub'], a['url'], a['last_seen']))
            nouvelles.append(a)
        except sqlite3.IntegrityError:
            c.execute('''
                UPDATE annonces SET last_seen=? WHERE url=?
            ''', (a['last_seen'], a['url']))
    conn.commit()
    return nouvelles

def export_html():
    c.execute("SELECT titre, entreprise, lieu, date_pub, url FROM annonces ORDER BY last_seen DESC")
    rows = c.fetchall()

    html = "<html><head><meta charset='utf-8'><title>Annonces Développeur Web</title></head><body><h1>Dernières annonces</h1><ul>"
    for row in rows:
        titre, entreprise, lieu, date_pub, url = row
        html += f"<li><a href='{url}' target='_blank'>{titre}</a> - {entreprise} - {lieu} - Publiée le {date_pub}</li>"
    html += "</ul></body></html>"

    with open(HTML_OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(html)

def envoyer_email(nouvelles_annonces):
    if not nouvelles_annonces:
        return

    corps = "\n\n".join([f"{a['titre']} - {a['entreprise']} - {a['lieu']}\n{a['url']}" for a in nouvelles_annonces])
    sujet = "🆕 Nouvelles annonces développeur web"
    message = f"Subject: {sujet}\n\n{corps}"

    try:
        with smtplib.SMTP(os.getenv("SMTP_SERVER"), int(os.getenv("SMTP_PORT"))) as server:
            server.starttls()
            server.login(os.getenv("EMAIL"), os.getenv("PASSWORD"))
            server.sendmail(
                os.getenv("EMAIL"),
                os.getenv("DESTINATAIRE"),
                message.encode("utf-8")
            )
        logging.info("✅ Email envoyé avec succès.")
    except Exception as e:
        logging.error(f"Erreur lors de l'envoi de l'email : {e}")

# Boucle principale
if __name__ == "__main__":
    while True:
        logging.info("🔍 Scraping en cours...")
        annonces = get_annonces()
        nouvelles = save_annonces(annonces)
        export_html()
        envoyer_email(nouvelles)
        logging.info(f"✅ {len(annonces)} annonces récupérées à {datetime.datetime.now()}")
        time.sleep(3600)
