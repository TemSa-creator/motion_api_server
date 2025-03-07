from fastapi import FastAPI, Request
import requests

app = FastAPI()

# Simulierte User-Datenbank für Limits und Abos
user_data = {
    "user_123": {"remaining_images": 10, "subscription_tier": "Basic 10 Bilder/Monat"}
}

subscription_limits = {
    "Basic 10 Bilder/Monat": 10,
    "Pro 50 Bilder/Monat": 50,
    "Ultimate 200 Bilder/Monat": 200
}

UPGRADE_URL = "https://www.checkout-ds24.com/product/599133"

@app.get("/")
def home():
    """Startseite der API"""
    return {"message": "Server läuft perfekt!"}

@app.post("/upgrade")
async def handle_upgrade(request: Request):
    """Empfängt das Upgrade von Digistore24 über Zapier"""
    data = await request.json()
    
    user_id = data.get("user_id")
    new_plan = data.get("new_plan")
    payment_status = data.get("payment_status")

    if payment_status == "completed":
        user_data[user_id] = {"remaining_images": subscription_limits.get(new_plan, 0), "subscription_tier": new_plan}
        return {"status": "Upgrade successful", "new_plan": new_plan}
    
    return {"status": "Payment not completed"}

@app.post("/check-limit")
async def check_limit():
    """Überprüft das Bildlimit eines Nutzers"""
    user_id = "user_123"
    user_info = user_data.get(user_id, {"remaining_images": 0, "subscription_tier": "Kein Abo"})

    return {
        "allowed": user_info["remaining_images"] > 0,
        "remaining_images": user_info["remaining_images"],
        "subscription_tier": user_info["subscription_tier"],
        "message": "Du kannst noch {} Bilder generieren.".format(user_info["remaining_images"])
        if user_info["remaining_images"] > 0 else "Dein Limit ist erreicht! Upgrade dein Abo für mehr Bilder."
    }
