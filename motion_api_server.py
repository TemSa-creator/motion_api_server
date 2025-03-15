from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
import psycopg2
import os
import hashlib
import requests

# ✅ FastAPI App starten
app = FastAPI()

# ✅ Webhook URLs für Digistore und Tracking
DIGISTORE_ABO_URL = "https://www.checkout-ds24.com/product/599133"
TRACKING_WEBHOOK_URL = "https://your-webhook-url.com"

# ✅ Admin-User-ID (Ersteller der Bots)
ADMIN_USER_ID = "DEINE_USER_ID"

# 🔧 Verbindung zur Datenbank mit Fehlerbehandlung & Passwort-Sicherheit
def get_db_connection():
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        print("❌ Fehler: 'DATABASE_URL' ist nicht gesetzt!")
        raise RuntimeError("Datenbank-URL fehlt!")
    try:
        password = os.getenv("DB_PASSWORD", "").strip().encode("utf-8")
        conn = psycopg2.connect(DATABASE_URL, password=password, sslmode="require")
        print("✅ Datenbankverbindung erfolgreich!")
        return conn
    except Exception as e:
        print(f"🚨 DB-Verbindungsfehler: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Fehler bei der DB-Verbindung: {str(e)}")

# 🗂 JSON-Schemas für Anfragen
class UserRequest(BaseModel):
    user_id: str = None
    email: str = None
    ip_address: str = None
    openai_id: str = None
    new_plan: str = None

# 🔄 Funktion zur Umwandlung des Abos in Credits
def get_credit_limit(plan_name):
    credits_map = {
        "Basic": 50,
        "Pro": 200,
        "Business": 500,
        "Enterprise": 999999  # Unbegrenztes Abo
    }
    return credits_map.get(plan_name, 10)

# 🔒 Hashing der E-Mail-Adresse
def generate_user_id(email):
    return hashlib.sha256(email.strip().encode()).hexdigest()

# 🔥 Tracking-Webhook senden
def send_tracking_webhook(user_id, email, ip_address, subscription_tier):
    data = {
        "user_id": user_id,
        "email": email.strip(),
        "ip_address": ip_address,
        "subscription_tier": subscription_tier
    }
    try:
        requests.post(TRACKING_WEBHOOK_URL, json=data)
        print(f"📡 Webhook gesendet für {email}")
    except Exception as e:
        print(f"⚠️ Fehler beim Senden an Webhook: {str(e)}")

# 📌 **Limit-Check API mit erweiterter Logging-Funktion**
@app.post("/check-limit-before-generation")
async def check_limit_before_generation(request: UserRequest):
    print(f"📥 Eingehende Anfrage: {request.dict()}")
    
    if not request.email:
        print("❌ Fehler: Keine E-Mail übermittelt!")
        raise HTTPException(status_code=400, detail="E-Mail erforderlich! Bitte registriere dich mit der E-Mail, die du für dein Abo nutzt.")

    conn = get_db_connection()
    email_hash = generate_user_id(request.email)

    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT used_credits, max_credits FROM user_limits WHERE email_hash = %s", (email_hash,))
            result = cursor.fetchone()
            
            if not result:
                print(f"ℹ️ Nutzer {request.email} nicht in DB gefunden – wird registriert.")
                cursor.execute("""
                    INSERT INTO user_limits (user_id, email_hash, used_credits, max_credits, subscription_active, subscription_tier)
                    VALUES (%s, %s, 0, 10, FALSE, 'Free')
                """, (email_hash, email_hash))
                conn.commit()
                send_tracking_webhook(email_hash, request.email, request.ip_address, "Free")
                print("✅ Neuer User registriert!")
                return {
                    "allowed": True,
                    "remaining_images": 10,
                    "message": "User wurde automatisch registriert und kann Bilder generieren.",
                    "subscription_tier": "Free"
                }
            
            used_credits, max_credits = result
            print(f"ℹ️ Nutzer gefunden: {request.email} hat {used_credits}/{max_credits} Credits genutzt.")
            
            if used_credits >= max_credits:
                print("❌ Limit erreicht! Zeige Upgrade-Option an.")
                return {
                    "allowed": False,
                    "message": "Limit erreicht! Bitte upgrade dein Abo, um weiter Bilder zu generieren.",
                    "upgrade_url": DIGISTORE_ABO_URL
                }
            
            print("✅ Limit nicht erreicht. Generierung erlaubt.")
            return {
                "allowed": True,
                "remaining_images": max_credits - used_credits,
                "subscription_tier": "Free",
                "message": "Limit nicht erreicht. Du kannst weiterhin Bilder generieren."
            }
    except Exception as e:
        print(f"🚨 Fehler in /check-limit-before-generation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Fehler in /check-limit-before-generation: {str(e)}")
    finally:
        conn.close()
