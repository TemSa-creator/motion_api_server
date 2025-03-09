from fastapi import FastAPI, Request, HTTPException
from google.oauth2 import service_account
from googleapiclient.discovery import build
import os

app = FastAPI()

# Google Sheets API Setup
SERVICE_ACCOUNT_FILE = "service_account.json"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES
)
service = build("sheets", "v4", credentials=credentials)

SPREADSHEET_ID = "1t6_KQJaRAFN1Xyy4lXO5CgOYAls3U5Ldd_guzyO22uY"
RANGE_NAME = "Limits!A2:B100"

@app.post("/check-limit")
async def check_limit(request: Request):
    data = await request.json()
    user_id = data.get("user_id")

    if not user_id:
        raise HTTPException(status_code=400, detail="User ID is required")

    sheet = service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID, range=RANGE_NAME).execute()
    values = sheet.get("values", [])

    for row in values:
        if row[0] == user_id:
            remaining_images = int(row[1])
            return {"remaining_images": remaining_images, "subscription_tier": "Basic 10 Bilder"}
    
    return {"error": "User not found"}

@app.post("/generate-image")
async def generate_image(request: Request):
    data = await request.json()
    user_id = data.get("user_id")
    prompt = data.get("prompt")

    if not user_id or not prompt:
        raise HTTPException(status_code=400, detail="User ID and prompt are required")

    # Hier könnte später die KI-Generierung integriert werden
    return {"message": "Image generation started", "prompt": prompt}

@app.post("/upgrade")
async def upgrade_subscription(request: Request):
    data = await request.json()
    user_id = data.get("user_id")

    if not user_id:
        raise HTTPException(status_code=400, detail="User ID is required")

    return {"message": "Upgrade your plan here", "upgrade_link": "https://www.checkout-ds24.com/product/599133"}
