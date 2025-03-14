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
        raise RuntimeError("❌ Fehler: 'DATABASE_URL' ist nicht gesetzt!")
    try:
        password = os.getenv("DB_PASSWORD", "").strip().encode("utf-8")  # Sicherstellen, dass keine Leerzeichen oder Sonderzeichen Probleme machen
        conn = psycopg2.connect(DATABASE_URL, password=password, sslmode="require")
        return conn
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"🚨 DB-Verbindungsfehler: {str(e)}")

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
    return credits_map.get(plan_name, 10)  # Standardwert für unbekannte Produkte

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
    except Exception as e:
        print(f"⚠️ Fehler beim Senden an Webhook: {str(e)}")

# 📌 **Limit-Check API mit Upgrade-Option**
@app.post("/check-limit-before-generation")
async def check_limit_before_generation(request: UserRequest):
    if not request.email:
        return {"error": "E-Mail erforderlich!"}

    conn = get_db_connection()
    email_hash = generate_user_id(request.email)

    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT used_credits, max_credits FROM user_limits WHERE email_hash = %s", (email_hash,))
            result = cursor.fetchone()
            if not result:
                return {
                    "error": "Kein registrierter Nutzer!",
                    "register_url": "https://motion-api-server.onrender.com/register-user"
                }
            used_credits, max_credits = result
            if used_credits >= max_credits:
                return {
                    "allowed": False,
                    "message": "Limit erreicht! Upgrade erforderlich.",
                    "upgrade_url": DIGISTORE_ABO_URL
                }
            return {"allowed": True, "remaining_images": max_credits - used_credits}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"🚨 Fehler in /check-limit-before-generation: {str(e)}")
    finally:
        conn.close()

# 📌 **Automatische Nutzerregistrierung**
@app.post("/register-user")
async def register_user(request: UserRequest):
    if not request.email:
        return {"error": "E-Mail-Adresse erforderlich!"}

    conn = get_db_connection()
    email_hash = generate_user_id(request.email)

    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT user_id FROM user_limits WHERE email_hash = %s", (email_hash,))
            result = cursor.fetchone()
            if result:
                return {"message": "User bereits registriert.", "user_id": email_hash}

            cursor.execute("""
                INSERT INTO user_limits (user_id, email_hash, used_credits, max_credits, subscription_active, subscription_tier)
                VALUES (%s, %s, 0, 10, FALSE, 'Free')
            """, (email_hash, email_hash))
            conn.commit()
            send_tracking_webhook(email_hash, request.email, request.ip_address, "Free")
            return {"message": "User erfolgreich registriert", "user_id": email_hash, "subscription_tier": "Free"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"🚨 Fehler in /register-user: {str(e)}")
    finally:
        conn.close()

# 📌 **Nutzung aktualisieren**
@app.post("/update-usage")
async def update_usage(request: UserRequest):
    if not request.email:
        return {"error": "E-Mail erforderlich!"}

    conn = get_db_connection()
    email_hash = generate_user_id(request.email)

    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT used_credits, max_credits FROM user_limits WHERE email_hash = %s", (email_hash,))
            result = cursor.fetchone()
            if not result:
                return {"error": "User nicht registriert!"}

            used_credits, max_credits = result
            if used_credits >= max_credits:
                return {"error": "Limit erreicht! Upgrade erforderlich."}

            cursor.execute("""
                UPDATE user_limits
                SET used_credits = used_credits + 1
                WHERE email_hash = %s
            """, (email_hash,))
            conn.commit()

        return {"message": "Nutzung erfolgreich aktualisiert."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"🚨 Fehler in /update-usage: {str(e)}")
    finally:
        conn.close()
