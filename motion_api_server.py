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

# 🔧 Verbindung zur Datenbank herstellen
def get_db_connection():
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        raise RuntimeError("❌ Fehler: 'DATABASE_URL' ist nicht gesetzt!")
    try:
        conn = psycopg2.connect(DATABASE_URL, sslmode="require")
        return conn
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"🚨 Fehler bei der DB-Verbindung: {str(e)}")

# 🗂 JSON-Schemas
class UserRequest(BaseModel):
    user_id: str = None
    email: str = None
    ip_address: str = None
    openai_id: str = None
    new_plan: str = None

# 🔄 Abonnement in Credits umwandeln
def get_credit_limit(plan_name):
    credits_map = {
        "Basic": 50,
        "Pro": 200,
        "Business": 500,
        "Enterprise": 999999  # Unbegrenztes Abo
    }
    return credits_map.get(plan_name, 10)  # Standardwert für neue oder unbekannte Nutzer

# 🔒 Hashing-Funktionen für Datensicherheit
def anonymize_ip(ip_address):
    return hashlib.sha256(ip_address.encode()).hexdigest()

def generate_user_id(email):
    return hashlib.sha256(email.encode()).hexdigest()

# 🔥 Webhook für Tracking neuer Nutzer
def send_tracking_webhook(user_id, email, ip_address, subscription_tier):
    data = {
        "user_id": user_id,
        "email": email,
        "ip_address": ip_address,
        "subscription_tier": subscription_tier
    }
    try:
        requests.post(TRACKING_WEBHOOK_URL, json=data)
    except Exception as e:
        print(f"⚠️ Fehler beim Senden an Webhook: {str(e)}")

# 🛠️ Admin-Check
def is_admin(user_id):
    return user_id == ADMIN_USER_ID

# 📌 **Automatische Registrierung neuer Nutzer**
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
                return {"message": "User bereits registriert", "user_id": email_hash}

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

# 📌 **Digistore Webhook für Abo-Erkennung & Upgrade**
@app.post("/digistore-webhook")
async def digistore_webhook(request: Request):
    data = await request.json()
    print("📩 Webhook-Eingang:", data)  

    if "email" not in data or "product_name" not in data:
        return {"error": "Ungültige Webhook-Daten!"}
    
    conn = get_db_connection()
    email_hash = generate_user_id(data.get("email"))
    purchased_plan = data.get("product_name")
    new_credits = get_credit_limit(purchased_plan)  # Automatische Umwandlung!

    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT user_id FROM user_limits WHERE email_hash = %s", (email_hash,))
            result = cursor.fetchone()
            if not result:
                return {"error": "User nicht registriert!"}

            cursor.execute("""
                UPDATE user_limits 
                SET max_credits = %s, used_credits = 0, subscription_active = TRUE, subscription_tier = %s
                WHERE user_id = %s
            """, (new_credits, purchased_plan, email_hash))
            conn.commit()

        return {"message": "Abo erfolgreich aktiviert", "subscription_tier": purchased_plan, "max_credits": new_credits}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"🚨 Fehler im Digistore-Webhook: {str(e)}")

    finally:
        conn.close()

# 📌 **Limit-Check API für User**
@app.post("/check-limit")
async def check_limit(user: UserRequest):
    if not user.user_id and not user.email:
        return {"error": "User-ID oder E-Mail erforderlich!"}

    conn = get_db_connection()
    email_hash = generate_user_id(user.email) if user.email else user.user_id

    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT used_credits, max_credits, subscription_tier FROM user_limits WHERE user_id = %s", (email_hash,))
            result = cursor.fetchone()
            if not result:
                return {"error": "User nicht gefunden"}
            used_credits, max_credits, subscription_tier = result
            allowed = used_credits < max_credits
            if not allowed:
                return {
                    "allowed": False,
                    "remaining_images": 0,
                    "subscription_tier": subscription_tier,
                    "message": "Limit erreicht. Upgrade erforderlich.",
                    "upgrade_url": DIGISTORE_ABO_URL
                }
            return {
                "allowed": True,
                "remaining_images": max_credits - used_credits,
                "subscription_tier": subscription_tier,
                "message": "Limit nicht erreicht."
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"🚨 Fehler in /check-limit: {str(e)}")
    finally:
        conn.close()
