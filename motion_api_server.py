from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
import psycopg2
import os
import hashlib
import requests

# ✅ FastAPI App starten
app = FastAPI()

# ✅ Webhook URLs für Digistore und Zapier
DIGISTORE_ABO_URL = "https://www.checkout-ds24.com/product/599133"
TRACKING_WEBHOOK_URL = "https://your-webhook-url.com"

# ✅ Admin-User-ID (Ersteller der Bots)
ADMIN_USER_ID = "DEINE_USER_ID"

# 🔧 Funktion zur Verbindung mit der Datenbank
def get_db_connection():
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        raise RuntimeError("❌ Fehler: 'DATABASE_URL' ist nicht gesetzt!")
    try:
        conn = psycopg2.connect(DATABASE_URL, sslmode="require")
        return conn
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"🚨 DB-Verbindungsfehler: {str(e)}")

# 🗂 JSON-Schemas
class UserRequest(BaseModel):
    email: str

# 🔒 Hashing der E-Mail-Adresse
def generate_user_id(email):
    return hashlib.sha256(email.encode()).hexdigest()

# 📌 API-Endpunkt für Nutzerprüfung & Freischaltung
@app.post("/check-user")
async def check_user(request: UserRequest):
    if not request.email:
        return {"error": "E-Mail erforderlich!"}
    
    conn = get_db_connection()
    email_hash = generate_user_id(request.email)

    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT user_id, max_credits, used_credits FROM user_limits WHERE email_hash = %s", (email_hash,))
            result = cursor.fetchone()

            if not result:
                return {
                    "error": "⚠️ Deine E-Mail ist nicht registriert! Bitte registriere dich oder kaufe ein Abo.",
                    "register_url": DIGISTORE_ABO_URL
                }

            user_id, max_credits, used_credits = result
            return {
                "message": "✅ Zugriff gewährt!",
                "user_id": user_id,
                "max_credits": max_credits,
                "used_credits": used_credits
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"🚨 Fehler in /check-user: {str(e)}")

    finally:
        conn.close()
