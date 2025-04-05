# flask_annonces_app/app.py

from flask import Flask, render_template, request
import sqlite3

app = Flask(__name__)

DB_PATH = "annonces.db"


def get_annonces(search=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    if search:
        query = f"""
            SELECT titre, entreprise, lieu, date_pub, url
            FROM annonces
            WHERE titre LIKE ? OR entreprise LIKE ? OR lieu LIKE ?
            ORDER BY last_seen DESC
        """
        like_search = f"%{search}%"
        c.execute(query, (like_search, like_search, like_search))
    else:
        c.execute("""
            SELECT titre, entreprise, lieu, date_pub, url
            FROM annonces
            ORDER BY last_seen DESC
        """)

    rows = c.fetchall()
    conn.close()
    return rows


@app.route("/")
def index():
    search_query = request.args.get("q")
    annonces = get_annonces(search_query)
    return render_template("index.html", annonces=annonces, search_query=search_query)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
