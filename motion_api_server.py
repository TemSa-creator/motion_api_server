from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import psycopg2
import os

app = FastAPI()  # ✅ Muss GANZ OBEN im Code stehen!

# Datenbankverbindung
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    DATABASE_URL = "DATABASE_URL"
def get_db_connection():
    return psycopg2.connect(DATABASE_URL, sslmode='require')

@app.post("/check-limit")
async def check_limit(user_id: str):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Nutzer in der Datenbank nachschauen
        cursor.execute("SELECT used_credits, max_credits FROM user_limits WHERE user_id = %s", (user_id,))
        result = cursor.fetchone()

        if not result:
            return {"error": "User nicht gefunden"}

        used_credits, max_credits = result

        # Prüfen, ob Limit erreicht wurde
        if used_credits >= max_credits:
            return {"limit_reached": True, "message": "Dein Limit ist erreicht. Upgrade erforderlich!"}
        
        return {"limit_reached": False, "used_credits": used_credits, "max_credits": max_credits}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        cursor.close()
        conn.close()

@app.post("/add-user")
async def add_user(user_id: str, max_credits: int = 10):
    """Fügt einen neuen Nutzer hinzu oder aktualisiert ihn."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO user_limits (user_id, used_credits, max_credits, subscription_active)
            VALUES (%s, 0, %s, FALSE)
            ON CONFLICT (user_id) DO NOTHING;
        """, (user_id, max_credits))

        conn.commit()
        return {"message": "User erfolgreich hinzugefügt", "user_id": user_id}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        cursor.close()
        conn.close()
