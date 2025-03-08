from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
import uvicorn
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# FastAPI-App erstellen
app = FastAPI()

# Digistore24 Upgrade-Link
UPGRADE_URL = "https://www.checkout-ds24.com/product/599133"

# Google Sheets API Setup
SERVICE_ACCOUNT_FILE = "service_account.json"
SPREADSHEET_NAME = "Motion_Bildlimits"

# Verbindung zu Google Sheets herstellen
def get_google_sheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(SERVICE_ACCOUNT_FILE, scope)
    client = gspread.authorize(creds)
    return client.open(SPREADSHEET_NAME).sheet1

# Standard-Limits für Abonnements
subscription_limits = {
    "Basic 10 Bilder/Monat": 10,
    "Pro 50 Bilder/Monat": 50,
    "Business 200 Bilder/Monat": 200,
    "Enterprise Unbegrenzt": 9999
}

class UserRequest(BaseModel):
    user_id: str

# Nutzerlimit aus Google Sheets abrufen oder erstellen
def get_user_limit(user_id):
    sheet = get_google_sheet()
    data = sheet.get_all_records()
    
    for row in data:
        if row["user_id"] == user_id:
            return {
                "remaining_images": row["remaining_images"],
                "subscription_tier": row["subscription_tier"]
            }
    
    new_user = [user_id, 10, "Basic 10 Bilder/Monat"]
    sheet.append_row(new_user)
    
    return {
        "remaining_images": 10,
        "subscription_tier": "Basic 10 Bilder/Monat"
    }

# Nutzerlimit aktualisieren
def update_user_limit(user_id, remaining_images, subscription_tier):
    sheet = get_google_sheet()
    data = sheet.get_all_records()
    
    for i, row in enumerate(data, start=2):
        if row["user_id"] == user_id:
            sheet.update(f"B{i}", remaining_images)
            sheet.update(f"C{i}", subscription_tier)
            return

# API: Bildlimit prüfen
@app.post("/check-limit")
def check_limit(request: UserRequest):
    user_id = request.user_id
    user_info = get_user_limit(user_id)
    return {
        "remaining_images": user_info["remaining_images"],
        "subscription_tier": user_info["subscription_tier"]
    }

# API: Bildlimit reduzieren nach Generierung
@app.post("/generate-image")
def generate_image(request: UserRequest, prompt: str):
    user_id = request.user_id
    user_info = get_user_limit(user_id)
    
    if user_info["remaining_images"] <= 0:
        raise HTTPException(status_code=403, detail="Limit erreicht! Upgrade erforderlich.")
    
    new_remaining = user_info["remaining_images"] - 1
    update_user_limit(user_id, new_remaining, user_info["subscription_tier"])
    
    return {
        "image_url": f"https://fakeimageapi.com/generate/{prompt.replace(' ', '_')}.png",
        "remaining_images": new_remaining,
        "subscription_tier": user_info["subscription_tier"]
    }

# API: Abo-Upgrade durchführen
@app.post("/upgrade")
def upgrade_subscription(request: UserRequest, new_plan: str):
    user_id = request.user_id
    
    if new_plan not in subscription_limits:
        raise HTTPException(status_code=400, detail="Ungültiges Abo-Modell")
    
    update_user_limit(user_id, subscription_limits[new_plan], new_plan)
    
    return {
        "message": "Upgrade erfolgreich!",
        "subscription_tier": new_plan
    }

# Google Sheets Verbindung testen
@app.get("/test-sheets")
def test_sheets():
    try:
        sheet = get_google_sheet()
        data = sheet.get_all_records()
        return {"message": "Google Sheets Verbindung erfolgreich!", "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# API Startseite
@app.get("/")
def home():
    return {"message": "Motion API läuft perfekt!"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=10001)
