import psycopg2
import os

# Verbindung zur PostgreSQL-Datenbank herstellen
DATABASE_URL = "dbname=motion_db_vwh4 user=postgres password=Archan1! host=localhost port=5432"

try:
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    print("✅ Verbindung zur PostgreSQL-Datenbank erfolgreich!")

    # Test: Tabelle anzeigen
    cursor.execute("SELECT * FROM user_limits;")
    users = cursor.fetchall()
    print("📊 Nutzer in der Datenbank:", users)

except Exception as e:
    print("❌ Fehler bei der Verbindung zur Datenbank:", e)

finally:
    if 'cursor' in locals():
        cursor.close()
    if 'conn' in locals():
        conn.close()
