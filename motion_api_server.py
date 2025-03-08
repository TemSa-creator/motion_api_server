from fastapi import FastAPI, HTTPException
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# FastAPI-App erstellen
app = FastAPI()

# Google Sheets API Setup
SERVICE_ACCOUNT_FILE = "service_account.json"  # Stelle sicher, dass diese Datei im Projektverzeichnis ist
SPREADSHEET_NAME = "Motion_Bildlimits"  # Name der Google Sheets Datei

# Verbindung zu Google Sheets herstellen
def get_google_sheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/spreadsheets",
             "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(SERVICE_ACCOUNT_FILE, scope)
    client = gspread.authorize(creds)
    return client.open(SPREADSHEET_NAME).sheet1  # Erste Tabelle abrufen

# Standard-Limits für Abonnements
subscription_limits = {
    "Basic 10 Bilder/Monat": 10,
    "Pro 50 Bilder/Monat": 50,
    "Business 200 Bilder/Monat": 200,
    "Enterprise Unbegrenzt": 9999  # Soft-Limit, damit du nicht draufzahlst
}

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

    # Falls Nutzer nicht existiert, neuen Eintrag anlegen (10 kostenlose Bilder)
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
    
    for i, row in enumerate(data, start=2):  # Startet bei 2, da Zeile 1 die Header sind
        if row["user_id"] == user_id:
            sheet.update(f"B{i}", remaining_images)  # Zelle mit verbleibenden Bildern aktualisieren
            sheet.update(f"C{i}", subscription_tier)  # Abo-Stufe aktualisieren
            return

# **Bildlimit überprüfen**
@app.post("/check-limit")
def check_limit(user_id: str):
    user_info = get_user_limit(user_id)
    return {
        "allowed": user_info["remaining_images"] > 0,
        "remaining_images": user_info["remaining_images"],
        "subscription_tier": user_info["subscription_tier"],
        "message": f"Du kannst noch {user_info['remaining_images']} Bilder generieren."
                   if user_info["remaining_images"] > 0 else "Dein Limit ist erreicht! Upgrade dein Abo für mehr Bilder."
    }

# **Bild generieren**
@app.post("/generate-image")
def generate_image(user_id: str, prompt: str):
    user_info = get_user_limit(user_id)
    
    if user_info["remaining_images"] <= 0:
        return {
            "error": "Limit erreicht",
            "message": "Dein Limit ist erreicht! Upgrade dein Abo für mehr Bilder.",
            "upgrade_url": "https://www.checkout-ds24.com/product/599133",
            "next_tier": "Pro 50 Bilder/Monat",
            "subscription_tier": user_info["subscription_tier"]
        }
    
    new_remaining = user_info["remaining_images"] - 1
    update_user_limit(user_id, new_remaining, user_info["subscription_tier"])
    
    return {
        "image_url": f"https://fakeimageapi.com/generate/{prompt.replace(' ', '_')}.png",
        "remaining_images": new_remaining,
        "subscription_tier": user_info["subscription_tier"]
    }

# **Abo-Upgrade**
@app.post("/upgrade")
def upgrade_subscription(user_id: str, new_plan: str):
    if new_plan not in subscription_limits:
        raise HTTPException(status_code=400, detail="Ungültiges Abo-Modell")
    
    update_user_limit(user_id, subscription_limits[new_plan], new_plan)
    
    return {
        "message": "Upgrade erfolgreich!",
        "subscription_tier": new_plan
    }

# **Google Sheets Verbindung testen**
@app.get("/test-sheets")
def test_sheets():
    try:
        sheet = get_google_sheet()
        data = sheet.get_all_records()
        return {"message": "Google Sheets Verbindung erfolgreich!", "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# **Startseite**
@app.get("/")
def home():
    return {"message": "Motion API läuft perfekt!"}


import gspread
from oauth2client.service_account import ServiceAccountCredentials
from fastapi import FastAPI

app = FastAPI()

# **1. Google Sheets Zugriff einrichten**
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("service_account.json", scope)
client = gspread.authorize(creds)

# **2. Test-Endpunkt für Google Sheets**
@app.get("/test-sheets")
async def test_sheets():
    try:
        sheet = client.open("DEIN_TABELLENNAME").sheet1  # Ersetze mit deinem echten Google Sheets Namen
        test_data = sheet.get_all_records()
        return {"message": "Google Sheets API Verbindung erfolgreich!", "data": test_data}
    except Exception as e:
        return {"error": str(e)}
