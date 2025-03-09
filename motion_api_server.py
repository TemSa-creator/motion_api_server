from fastapi import FastAPI, HTTPException, Request
import os
import json
from google.oauth2.service_account import Credentials
import gspread

# Google Service Account Credentials laden
key_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "service_account.json")
creds = Credentials.from_service_account_file(key_path, scopes=["https://www.googleapis.com/auth/spreadsheets"])
client = gspread.authorize(creds)

# Google Sheets Setup (1t6_KQJaRAFN1Xyy4lXO5CgOYAls3U5Ldd_guzyO22uY)
SPREADSHEET_ID = "1t6_KQJaRAFN1Xyy4lXO5CgOYAls3U5Ldd_guzyO22uY"
sheet = client.open_by_key(SPREADSHEET_ID).sheet1

app = FastAPI()

# Limits für Nutzer abrufen
@app.post("/check-limit")
async def check_limit(request: Request):
    data = await request.json()
    user_id = data.get("user_id")

    if not user_id:
        raise HTTPException(status_code=400, detail="User ID is required")

    records = sheet.get_all_records()
    for record in records:
        if record["User_ID"] == user_id:
            used_credits = record["Used_Credits"]
            max_credits = record["Max_Credits"]
            subscription_active = record.get("Subscription_Active", "Nein")

            remaining_images = max_credits - used_credits

            if remaining_images <= 0 and subscription_active.lower() != "ja":
                return {
                    "message": "Limit erreicht. Bitte Upgrade durchführen.",
                    "upgrade_url": "DEIN_DIGISTORE_UPGRADE_LINK"
                }

            return {
                "remaining_images": remaining_images,
                "subscription_tier": "Basic 10 Bilder" if subscription_active.lower() != "ja" else "Premium Unlimited"
            }

    return {"error": "Benutzer nicht gefunden"}

# Upgrade-Link zurückgeben
@app.post("/upgrade")
async def upgrade_subscription(request: Request):
    data = await request.json()
    user_id = data.get("user_id")

    if not user_id:
        raise HTTPException(status_code=400, detail="User ID is required")

    return {
        "message": "Upgrade erforderlich für mehr Bilder!",
        "upgrade_url": "https://www.checkout-ds24.com/product/599133"
    }

