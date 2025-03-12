from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import psycopg2
import os
import requests

# ✅ FastAPI App starten
app = FastAPI()

# ✅ Webhook URL für Digistore/Zapier
ZAPIER_WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbzrMFkpG1TIp0QIq60LafXPKS_esJSRl--SvV8aAUjkU4DuBllqVWgI2Cwtv9XVptb0/exec"

# ✅ Digistore24 Abo-Link
DIGISTORE_ABO_URL = "https://www.checkout-ds24.com/product/599133"

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
    user_id: str

class ImageRequest(BaseModel):
    user_id: str
    prompt: str

class UpgradeRequest(BaseModel):
    user_id: str
    new_plan: str

# 📌 API-Endpunkt für Limit-Check
@app.post("/check-limit")
async def check_limit(user: UserRequest):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT used_credits, max_credits, subscription_tier FROM user_limits WHERE user_id = %s", (user.user_id,))
            result = cursor.fetchone()

            if not result:
                return {"error": "User nicht gefunden"}

            used_credits, max_credits, subscription_tier = result
            allowed = used_credits < max_credits

            if not allowed:
                webhook_data = {"user_id": user.user_id, "status": "LIMIT_REACHED"}
                try:
                    requests.post(ZAPIER_WEBHOOK_URL, json=webhook_data)
                except Exception as e:
                    print(f"⚠️ Fehler beim Webhook: {str(e)}")
                return {"allowed": False, "remaining_images": 0, "subscription_tier": subscription_tier, "message": "Limit erreicht. Upgrade erforderlich.", "upgrade_url": DIGISTORE_ABO_URL}
            
            return {"allowed": True, "remaining_images": max_credits - used_credits, "subscription_tier": subscription_tier, "message": "Limit nicht erreicht."}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"🚨 Fehler in /check-limit: {str(e)}")
    finally:
        if conn:
            conn.close()

# 🖼 API-Endpunkt für Bildgenerierung
@app.post("/generate-image")
async def generate_image(request: ImageRequest):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT used_credits, max_credits FROM user_limits WHERE user_id = %s", (request.user_id,))
            result = cursor.fetchone()
            if not result:
                return {"error": "User nicht gefunden"}
            
            used_credits, max_credits = result
            if used_credits >= max_credits:
                return {"error": "Limit erreicht", "upgrade_url": DIGISTORE_ABO_URL}
            
            new_credits = used_credits + 1
            cursor.execute("UPDATE user_limits SET used_credits = %s WHERE user_id = %s", (new_credits, request.user_id))
            conn.commit()

        image_url = f"https://motion-images.com/generated/{request.user_id}.jpg"  # Dummy-URL als Platzhalter
        return {"image_url": image_url, "remaining_images": max_credits - new_credits, "subscription_tier": "Pro"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"🚨 Fehler in /generate-image: {str(e)}")
    finally:
        if conn:
            conn.close()

# 🆙 API-Endpunkt für Upgrade
@app.post("/upgrade")
async def upgrade_subscription(user: UpgradeRequest):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("UPDATE user_limits SET max_credits = 100, subscription_tier = %s WHERE user_id = %s", (user.new_plan, user.user_id))
            conn.commit()

        return {"message": "Upgrade erfolgreich", "subscription_tier": user.new_plan}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"🚨 Fehler in /upgrade: {str(e)}")
    finally:
        if conn:
            conn.close()
