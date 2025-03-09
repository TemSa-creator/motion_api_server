from fastapi import FastAPI, Request
import os
import json
import logging
from fastapi import FastAPI, HTTPException
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Logging einrichten
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# API-Server starten
app = FastAPI()

# Google Service Account Credentials über Umgebungsvariable laden
try:
    service_account_info = json.loads(os.environ["GOOGLE_APPLICATION_CREDENTIALS_JSON"])
    credentials = service_account.Credentials.from_service_account_info(service_account_info)
    logger.info("Google Service Account erfolgreich geladen.")
except KeyError:
    logger.error("Fehler: GOOGLE_APPLICATION_CREDENTIALS_JSON ist nicht gesetzt.")
    raise HTTPException(status_code=500, detail="Service Account Credentials fehlen")
except Exception as e:
    logger.error(f"Fehler beim Laden der Google Credentials: {e}")
    raise HTTPException(status_code=500, detail="Fehler beim Laden der Google API Credentials")

# Google Sheets API Verbindung
def connect_to_google_sheets():
    try:
        service = build("sheets", "v4", credentials=credentials)
        logger.info("Erfolgreich mit Google Sheets API verbunden.")
        return service
    except Exception as e:
        logger.error(f"Google Sheets Verbindung fehlgeschlagen: {e}")
        raise HTTPException(status_code=500, detail="Google Sheets API Fehler")

@app.get("/")
def home():
    return {"message": "Motion API Server ist aktiv 🚀"}

from fastapi import Body

@app.post("/check-limit")
def check_limit(data: dict = Body(...)):
    user_id = data.get("user_id")
    if not user_id:
        return {"error": "user_id ist erforderlich"}
    
    # Hier muss dein Code für die Limit-Überprüfung rein
    return {"remaining_images": 10, "subscription_tier": "Basic 10 Bilder"}
    try:
        service = connect_to_google_sheets()
        spreadsheet_id = "DEINE_SPREADSHEET_ID"
        range_name = "Limits!A:B"

        sheet = service.spreadsheets().values().get(spreadsheetId=spreadsheet_id, range=range_name).execute()
        values = sheet.get("values", [])

        for row in values:
            if row[0] == user_id:
                remaining_images = int(row[1])
                return {"remaining_images": remaining_images}
        
        return {"error": "Benutzer nicht gefunden"}
    
    except Exception as e:
        logger.error(f"Fehler bei /check-limit: {e}")
        raise HTTPException(status_code=500, detail="Interner Serverfehler")
@app.post("/generate-image")
async def generate_image(request: Request):
    data = await request.json()
    user_id = data.get("user_id")
    prompt = data.get("prompt")

    if not user_id or not prompt:
        return JSONResponse(status_code=400, content={"error": "Missing user_id or prompt"})

    # Hier sollte deine Bildgenerierungslogik sein
    image_url = f"https://fake-image-api.com/generate?prompt={prompt}"

    return {"image_url": image_url}

@app.post("/update-limit")
def update_limit(user_id: str):
    try:
        service = connect_to_google_sheets()
        spreadsheet_id = "https://docs.google.com/spreadsheets/d/1t6_KQJaRAFN1Xyy4lXO5CgOYAls3U5Ldd_guzyO22uY/edit?usp=sharing"
        range_name = "Limits!A:B"

        sheet = service.spreadsheets().values().get(spreadsheetId=spreadsheet_id, range=range_name).execute()
        values = sheet.get("values", [])

        updated = False
        for i, row in enumerate(values):
            if row[0] == user_id:
                new_limit = max(int(row[1]) - 1, 0)
                values[i][1] = str(new_limit)
                updated = True
                break

        if updated:
            body = {"values": values}
            service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption="RAW",
                body=body
            ).execute()
            return {"message": "Limit aktualisiert", "new_limit": new_limit}
        else:
            return {"error": "Benutzer nicht gefunden"}
            
@app.post("/upgrade")
async def upgrade_subscription(request: Request):
    data = await request.json()
    user_id = data.get("user_id")

    if not user_id:
        raise HTTPException(status_code=400, detail="User ID is required")

    # Hier muss dein Digistore-Link rein!
    digistore_link = "https://www.checkout-ds24.com/product/599133"

    return {"message": "Hier kannst du dein Abo upgraden:", "upgrade_link": digistore_link}

    except Exception as e:
        logger.error(f"Fehler bei /update-limit: {e}")
        raise HTTPException(status_code=500, detail="Interner Serverfehler")
