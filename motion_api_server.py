from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import psycopg2
import os

# FastAPI App starten
app = FastAPI()

# 🔧 Funktion zur Verbindung mit der Datenbank
def get_db_connection():
    DATABASE_URL = os.getenv("DATABASE_URL")
    
    if not DATABASE_URL:
        raise RuntimeError("❌ Fehler: Die Umgebungsvariable 'DATABASE_URL' ist nicht gesetzt!")

    try:
        conn = psycopg2.connect(DATABASE_URL, sslmode="require")
        return conn
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"🚨 Fehler bei der Verbindung zur Datenbank: {str(e)}")

# 🗂 JSON-Schema für Anfragen
class UserRequest(BaseModel):
    user_id: str

class AddUserRequest(BaseModel):
    user_id: str
    max_credits: int = 10

class UpgradeRequest(BaseModel):
    user_id: str
    new_max_credits: int

# 📌 API-Endpunkt für Limit-Check
@app.post("/check-limit")
async def check_limit(user: UserRequest):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT used_credits, max_credits FROM user_limits WHERE user_id = %s", (user.user_id,))
            result = cursor.fetchone()

            if not result:
                return {"error": "User nicht gefunden"}

            used_credits, max_credits = result
            limit_reached = used_credits >= max_credits

            # 🔥 Falls das Limit erreicht ist, Upgrade-Link zurückgeben!
            if limit_reached:
                upgrade_link = "https://www.checkout-ds24.com/product/599133"  # 
                return {
                    "limit_reached": True,
                    "used_credits": used_credits,
                    "max_credits": max_credits,
                    "message": "⚠️ Limit erreicht! Bitte upgraden, um weiterzumachen.",
                    "upgrade_url": upgrade_link
                }

            return {
                "limit_reached": False,
                "used_credits": used_credits,
                "max_credits": max_credits
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"🚨 Fehler in /check-limit: {str(e)}")

    finally:
        if conn:
            conn.close()

# ➕ Neuen User hinzufügen
@app.post("/add-user")
async def add_user(user: AddUserRequest):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO user_limits (user_id, used_credits, max_credits, subscription_active)
                VALUES (%s, 0, %s, FALSE)
                ON CONFLICT (user_id) DO NOTHING;
            """, (user.user_id, user.max_credits))
            conn.commit()

        return {"message": "User erfolgreich hinzugefügt", "user_id": user.user_id}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"🚨 Fehler in /add-user: {str(e)}")

    finally:
        if conn:
            conn.close()

# 🆙 Upgrade Subscription
@app.post("/upgrade")
async def upgrade_subscription(user: UpgradeRequest):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("""
                UPDATE user_limits 
                SET max_credits = %s, subscription_active = TRUE 
                WHERE user_id = %s
            """, (user.new_max_credits, user.user_id))
            conn.commit()

        return {
            "message": "Abo erfolgreich aktualisiert",
            "user_id": user.user_id,
            "new_max_credits": user.new_max_credits
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"🚨 Fehler in /upgrade: {str(e)}")

    finally:
        if conn:
            conn.close()
