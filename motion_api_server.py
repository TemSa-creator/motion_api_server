from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import psycopg2
import os
import hashlib
import requests

# ✅ FastAPI App starten
app = FastAPI()

# ✅ Webhook URL für Digistore/Zapier
ZAPIER_WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbzrMFkpG1TIp0QIq60LafXPKS_esJSRl--SvV8aAUjkU4DuBllqVWgI2Cwtv9XVptb0/exec"

# ✅ Digistore24 Abo-Link
DIGISTORE_ABO_URL = "https://www.checkout-ds24.com/product/599133"

# ✅ Webhook für Tracking (z. B. Zapier, Google Sheets)
TRACKING_WEBHOOK_URL = "https://your-webhook-url.com"  # Hier deine Webhook-URL einfügen!

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

# 📌 API-Endpunkt für bestehende User (manuelle Eingabe)
@app.post("/add-existing-user")
async def add_existing_user(request: UserRequest):
    conn = get_db_connection()
    hashed_ip = anonymize_ip(request.ip_address)
    email_hash = generate_user_id(request.email)

    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT user_id FROM user_limits WHERE email_hash = %s OR ip_hash = %s", (email_hash, hashed_ip))
            result = cursor.fetchone()
            if result:
                return {"message": "User existiert bereits."}
            cursor.execute("INSERT INTO user_limits (user_id, email_hash, ip_hash, used_credits, max_credits, subscription_active, subscription_tier) VALUES (%s, %s, %s, 0, 10, FALSE, 'Basic')", (email_hash, email_hash, hashed_ip))
            conn.commit()
            return {"message": "Bestehender User erfolgreich gespeichert."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"🚨 Fehler in /add-existing-user: {str(e)}")
    finally:
        conn.close()

# 📌 API-Endpunkt für automatische User-Erkennung
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
                return {"user_id": result[0], "message": "User erkannt."}
            return {"error": "Kein User gefunden, bitte registrieren."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"🚨 Fehler in /identify-user: {str(e)}")
    finally:
        conn.close()
