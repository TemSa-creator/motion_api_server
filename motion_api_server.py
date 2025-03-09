from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
import gspread
from google.oauth2.service_account import Credentials

app = FastAPI()

# Digistore24 Upgrade-URL
UPGRADE_URL = "https://www.checkout-ds24.com/product/599133"

# Google Sheets API Setup
SERVICE_ACCOUNT_FILE = "service_account.json"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

credentials = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
gc = gspread.authorize(credentials)

SPREADSHEET_ID = "DEIN_SPREADSHEET_ID"
SHEET_NAME = "Webhooks"
sheet = gc.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME)

# Nutzer-Datenbank (wird später durch Google Sheets ersetzt)
user_data = {
    "testuser123": {"remaining_images": 10, "subscription_tier": "Basic 10 Bilder"}
}

class UserRequest(BaseModel):
    user_id: str

@app.post("/check-limit")
async def check_limit(request: UserRequest):
    user_id = request.user_id
    if user_id in user_data:
        return user_data[user_id]
    else:
        raise HTTPException(status_code=404, detail="Benutzer nicht gefunden")

@app.post("/update-limit")
async def update_limit(request: UserRequest):
    user_id = request.user_id
    if user_id in user_data:
        if user_data[user_id]["remaining_images"] > 0:
            user_data[user_id]["remaining_images"] -= 1
            return {"remaining_images": user_data[user_id]["remaining_images"]}
        else:
            return {"message": "Limit erreicht! Upgrade erforderlich", "upgrade_url": UPGRADE_URL}
    else:
        raise HTTPException(status_code=404, detail="Benutzer nicht gefunden")

@app.post("/upgrade")
async def upgrade_subscription(request: UserRequest):
    user_id = request.user_id
    user_data[user_id] = {"remaining_images": 100, "subscription_tier": "Enterprise Unbegrenzt"}
    return {"message": "Upgrade erfolgreich!", "new_limit": 100}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)