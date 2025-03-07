from fastapi import FastAPI, Request
import requests

app = FastAPI(
    title="Motion API",
    description="API für die Verwaltung von Bildgenerierungslimits und Abonnements in Motion.",
    version="1.0.0",
)

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

@app.post("/check-limit")
async def check_limit(request: Request):
    """Überprüft das Bildlimit eines Nutzers"""
    data = await request.json()
    user_id = data.get("user_id")

    if user_id not in user_data:
        user_data[user_id] = {"remaining_images": 10, "subscription_tier": "Basic 10 Bilder/Monat"}

    user_info = user_data[user_id]

    return {
        "allowed": user_info["remaining_images"] > 0,
        "remaining_images": user_info["remaining_images"],
        "subscription_tier": user_info["subscription_tier"],
        "message": "Du kannst noch {} Bilder generieren.".format(user_info["remaining_images"])
        if user_info["remaining_images"] > 0 else "Dein Limit ist erreicht! Upgrade dein Abo für mehr Bilder."
    }

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

@app.post("/generate-image")
async def generate_image(request: Request):
    """Generiert ein Bild für den Nutzer"""
    data = await request.json()
    user_id = data.get("user_id")
    prompt = data.get("prompt")

    if user_id not in user_data:
        return {"error": "User not found"}

    if user_data[user_id]["remaining_images"] <= 0:
        return {
            "error": "Limit erreicht",
            "message": "Dein Limit ist erreicht! Upgrade dein Abo für mehr Bilder.",
            "upgrade_url": UPGRADE_URL
        }

    # Reduziere das Bildlimit um 1
    user_data[user_id]["remaining_images"] -= 1

    # Simulierte Bildgenerierung
    image_url = f"https://fakeimageapi.com/generate/{prompt.replace(' ', '_')}.png"

    return {
        "image_url": image_url,
        "remaining_images": user_data[user_id]["remaining_images"],
        "subscription_tier": user_data[user_id]["subscription_tier"]
    }
