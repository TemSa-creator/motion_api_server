from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests

app = FastAPI()

# Simulierte Datenbank für Nutzerlimits mit mehreren Abo-Stufen
user_data = {
    "testuser123": {"remaining_images": 10, "subscription_tier": "Basic 10 Bilder/Monat"}
}

subscription_limits = {
    "Basic 10 Bilder/Monat": 10,
    "Pro 50 Bilder/Monat": 50,
    "Ultimate 200 Bilder/Monat": 200
}

UPGRADE_URL = "https://www.checkout-ds24.com/product/599133"

class UserRequest(BaseModel):
    user_id: str

class ImageRequest(UserRequest):
    prompt: str

@app.get("/")
def home():
    return {"message": "Server läuft perfekt!"}

@app.post("/check-limit")
def check_limit(request: UserRequest):
    user_id = request.user_id
    user_info = user_data.get(user_id, {"remaining_images": 0, "subscription_tier": "Kein Abo"})

    return {
        "allowed": user_info["remaining_images"] > 0,
        "remaining_images": user_info["remaining_images"],
        "subscription_tier": user_info["subscription_tier"],
        "message": "Du kannst noch {} Bilder generieren.".format(user_info["remaining_images"])
        if user_info["remaining_images"] > 0 else "Dein Limit ist erreicht! Upgrade dein Abo für mehr Bilder."
    }

@app.post("/generate-image")
def generate_image(request: ImageRequest):
    user_id = request.user_id
    prompt = request.prompt

    if user_id not in user_data:
        raise HTTPException(status_code=404, detail="User nicht gefunden")

    user_info = user_data[user_id]
    
    if user_info["remaining_images"] <= 0:
        return {
            "error": "Limit erreicht",
            "message": "Dein Limit ist erreicht! Upgrade dein Abo für mehr Bilder.",
            "upgrade_url": UPGRADE_URL,
            "next_tier": "Pro 50 Bilder/Monat",
            "subscription_tier": user_info["subscription_tier"]
        }

    # Simulierte Bildgenerierung
    image_url = f"https://fakeimageapi.com/generate/{prompt.replace(' ', '_')}.png"

    # Nutzer-Limit reduzieren
    user_data[user_id]["remaining_images"] -= 1

    return {
        "image_url": image_url,
        "remaining_images": user_data[user_id]["remaining_images"],
        "subscription_tier": user_data[user_id]["subscription_tier"]
    }

@app.post("/upgrade")
def upgrade_subscription(request: UserRequest):
    user_id = request.user_id
    if user_id not in user_data:
        raise HTTPException(status_code=404, detail="User nicht gefunden")

    # Upgrade auf die nächste Stufe simulieren
    user_data[user_id]["remaining_images"] = subscription_limits["Pro 50 Bilder/Monat"]
    user_data[user_id]["subscription_tier"] = "Pro 50 Bilder/Monat"

    return {
        "message": "Upgrade erfolgreich!",
        "subscription_tier": user_data[user_id]["subscription_tier"]
    }