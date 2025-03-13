from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
import psycopg2
import os
import hashlib
import requests

# ✅ FastAPI App starten
app = FastAPI()

# ✅ Webhook URLs für Digistore & Zapier
DIGISTORE_ABO_URL = "https://www.checkout-ds24.com/product/599133"
TRACKING_WEBHOOK_URL = "https://your-webhook-url.com"

# ✅ Admin-User-ID (Ersteller der Bots)
ADMIN_USER_ID = "DEINE_USER_ID"

# 🔧 Datenbankverbindung
def get_db_connection():
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        raise RuntimeError("❌ Fehler: 'DATABASE_URL' ist nicht gesetzt!")
    try:
        conn = psycopg2.connect(DATABASE_URL, sslmode="require")
        return conn
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"🚨 DB-Verbindungsfehler: {str(e)}")

# 🗂 JSON-Schema für Requests
class UserRequest(BaseModel):
    email: str = None
    user_id: str = None
    ip_address: str = None
    openai_id: str = None
    new_plan: str = None

# 🔄 Funktion zur Umwandlung des Abos in Credits
def get_credit_limit(plan_name):
    credits_map = {
        "Basic": 50,
        "Pro": 200,
        "Business": 500,
        "Enterprise": 999999
    }
    return credits_map.get(plan_name, 10)

# 🔒 Hashing der E-Mail-Adresse
def generate_user_id(email):
    return hashlib.sha256(email.encode()).hexdigest()

# 📌 **Erzwingt die E-Mail-Adresse für Nutzung**
@app.post("/identify-user")
async def identify_user(request: UserRequest):
    if not request.email:
        return {"error": "⚠️ E-Mail-Adresse erforderlich, um Motion zu nutzen!"}

    conn = get_db_connection()
    email_hash = generate_user_id(request.email)

    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT user_id, subscription_tier FROM user_limits WHERE email_hash = %s", (email_hash,))
            result = cursor.fetchone()

            if result:
                user_id, subscription_tier = result
                return {"user_id": user_id, "subscription_tier": subscription_tier, "message": "✅ Zugriff erlaubt!"}

            return {"error": "❌ Kein Nutzer gefunden – Bitte registrieren!"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"🚨 Fehler in /identify-user: {str(e)}")

    finally:
        conn.close()

# 📌 **Automatische Registrierung beim Kauf**
@app.post("/digistore-webhook")
async def digistore_webhook(request: Request):
    data = await request.json()
    
    if "email" not in data or "product_name" not in data:
        return {"error": "❌ Ungültige Webhook-Daten!"}
    
    conn = get_db_connection()
    email_hash = generate_user_id(data.get("email"))
    purchased_plan = data.get("product_name")
    new_credits = get_credit_limit(purchased_plan)

    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT user_id FROM user_limits WHERE email_hash = %s", (email_hash,))
            result = cursor.fetchone()

            if not result:
                cursor.execute("""
                    INSERT INTO user_limits (user_id, email_hash, used_credits, max_credits, subscription_active, subscription_tier)
                    VALUES (%s, %s, 0, %s, TRUE, %s)
                """, (email_hash, email_hash, new_credits, purchased_plan))
            else:
                cursor.execute("""
                    UPDATE user_limits SET max_credits = %s, subscription_active = TRUE, subscription_tier = %s WHERE email_hash = %s
                """, (new_credits, purchased_plan, email_hash))
            
            conn.commit()

        return {"message": "✅ Abo aktiviert!", "subscription_tier": purchased_plan, "max_credits": new_credits}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"🚨 Fehler im Digistore-Webhook: {str(e)}")

    finally:
        conn.close()

# 📌 **Limit-Check – Blockiert Nutzer ohne Registrierung**
@app.post("/check-limit")
async def check_limit(user: UserRequest):
    if not user.email:
        return {"error": "⚠️ E-Mail-Adresse erforderlich!"}

    conn = get_db_connection()
    email_hash = generate_user_id(user.email)

    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT used_credits, max_credits, subscription_tier FROM user_limits WHERE email_hash = %s", (email_hash,))
            result = cursor.fetchone()

            if not result:
                return {"error": "❌ Kein Nutzer gefunden – Bitte registrieren!"}

            used_credits, max_credits, subscription_tier = result
            if used_credits >= max_credits:
                return {
                    "allowed": False,
                    "remaining_images": 0,
                    "subscription_tier": subscription_tier,
                    "message": "⚠️ Limit erreicht – Upgrade erforderlich!",
                    "upgrade_url": DIGISTORE_ABO_URL
                }

            return {
                "allowed": True,
                "remaining_images": max_credits - used_credits,
                "subscription_tier": subscription_tier,
                "message": "✅ Limit nicht erreicht!"
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"🚨 Fehler in /check-limit: {str(e)}")

    finally:
        conn.close()
