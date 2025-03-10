import psycopg2
import os

# Datenbank-URL abrufen (entweder aus Umgebungsvariablen oder direkt setzen)
DATABASE_URL = os.getenv("DATABASE_URL")  # Falls in Render gespeichert

# Falls du sie NICHT in Render gespeichert hast, setze sie HIER direkt:
if not DATABASE_URL:
    DATABASE_URL = "postgresql://motion_user:gJ1ZwSkaq2gP5hxH2N9ehZfGEIXsgmVC@dpg-cv793nij1k6c73ea8up0-a.oregon-postgres.render.com/motion_db_vwh4"

try:
    # Verbindung zur PostgreSQL-Datenbank herstellen
    conn = psycopg2.connect(DATABASE_URL, sslmode='require')
    cursor = conn.cursor()
    print("✅ Verbindung zur PostgreSQL-Datenbank erfolgreich!")

    # Tabelle erstellen, falls sie nicht existiert
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_limits (
        id SERIAL PRIMARY KEY,
        user_id TEXT UNIQUE NOT NULL,
        used_credits INT DEFAULT 0,
        max_credits INT DEFAULT 10,
        subscription_active BOOLEAN DEFAULT FALSE
    );
    """)
    conn.commit()
    print("✅ Tabelle 'user_limits' wurde erfolgreich erstellt oder existiert bereits!")

except Exception as e:
    print(f"❌ Fehler bei der Verbindung zur Datenbank: {e}")

finally:
    if 'cursor' in locals():
        cursor.close()
    if 'conn' in locals():
        conn.close()
