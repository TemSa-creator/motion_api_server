from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import psycopg2
import os
import hashlib
import requests

# ✅ FastAPI App starten
app = FastAPI()

# ✅ Webhook URL für Digistore/Zapier
ZAPIIER_WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbzrMFkpG1TIp0QIq60LafXPKS_esJSRl--SvV8aAUjkU4DuBllqVWgI2Cwtv9XVptb0/exec"

# ✅ Digistore24 Abo-Link
DIGISTORE_ABO_URL = "https://www.checkout-ds24.com/product/599133"

# ✅ Webhook für Tracking (z. B. Zapier, Google Sheets)
TRACKING_WEBHOOK_URL = "https://your-webhook-url.com"  # Hier deine Webhook-URL einfügen!

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
        raise HTTPException(status_code=500, detail=f"🚨 Fehler bei DB-Verbindung: {str(e)}")

# 🗂 JSON-Schemas
class UserRequest(BaseModel):
    user_id: str = None
    email: str = None
    ip_address: str = None
    openai_id: str = None
    new_plan: str = None

# 🔒 Anonymisierung der IP-Adresse
def anonymize_ip(ip_address):
    return hashlib.sha256(ip_address.encode()).hexdigest()

# 🔒 Hashing der E-Mail-Adresse
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

# 🛠️ Funktion zur Erkennung des Admins
def is_admin(user_id):
    return user_id == ADMIN_USER_ID

# 📌 API-Endpunkt für Registrierung neuer User
@app.post("/register-user")
async def register_user(request: UserRequest):
    conn = get_db_connection()
    email_hash = generate_user_id(request.email)

    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT user_id FROM user_limits WHERE email_hash = %s", (email_hash,))
            result = cursor.fetchone()
            if result:
                return {"error": "Diese E-Mail ist bereits registriert!"}
            cursor.execute("INSERT INTO user_limits (user_id, email_hash, used_credits, max_credits, subscription_active, subscription_tier) VALUES (%s, %s, 0, 10, FALSE, 'Basic')", (email_hash, email_hash))
            conn.commit()
            send_tracking_webhook(email_hash, request.email, request.ip_address, "Basic")
            return {"message": "User erfolgreich registriert", "user_id": email_hash}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"🚨 Fehler in /register-user: {str(e)}")
    finally:
        conn.close()

# 📌 API-Endpunkt für User-Identifikation
@app.post("/identify-user")
async def identify_user(request: UserRequest):
    conn = get_db_connection()
    email_hash = generate_user_id(request.email) if request.email else None
    openai_id = request.openai_id if request.openai_id else None

    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT user_id FROM user_limits WHERE email_hash = %s OR openai_id = %s", (email_hash, openai_id))
            result = cursor.fetchone()
            if result:
                user_id = result[0]
                role = "admin" if is_admin(user_id) else "user"
                return {"user_id": user_id, "message": "User erkannt.", "role": role}
            return {"error": "Kein User gefunden, bitte registrieren."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"🚨 Fehler in /identify-user: {str(e)}")
    finally:
        conn.close()

# 📌 API-Endpunkt für Limit-Check
@app.post("/check-limit")
async def check_limit(user: UserRequest):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT used_credits, max_credits, subscription_tier FROM user_limits WHERE user_id = %s", (user.user_id,))
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

# 📌 API-Endpunkt für Upgrade
@app.post("/upgrade")
async def upgrade_subscription(user: UserRequest):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("UPDATE user_limits SET subscription_tier = %s WHERE user_id = %s", (user.new_plan, user.user_id))
            conn.commit()
        return {
            "message": "Upgrade erfolgreich",
            "subscription_tier": user.new_plan
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"🚨 Fehler in /upgrade: {str(e)}")
    finally:
        conn.close()
