from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests

app = FastAPI()

# Upgrade-URL für Digistore24
UPGRADE_URL = "https://www.checkout-ds24.com/product/599133"

# Nutzer-Datenbank (Wird in Zukunft in einer echten Datenbank gespeichert)
user_data = {
    "testuser123": {"remaining_images": 10, "subscription_tier": "Basic 10 Bilder/Monat"}
}

# Abonnement-Stufen & Limits
subscription_limits = {
    "Basic 10 Bilder/Monat": 10,
    "Pro 50 Bilder/Monat": 50,
    "Business 200 Bilder/Monat": 200,
    "Enterprise Unbegrenzt": 1000  # Soft-Limit, um hohe Serverkosten zu vermeiden
}

# Anfragen für die API definieren
class ImageRequest(BaseModel):
    user_id: str
    prompt: str

class UpgradeRequest(BaseModel):
    user_id: str
    new_plan: str

@app.get("/")
def home():
    return {"message": "Server läuft perfekt!"}

# API: Limit-Check für Nutzer
@app.post("/check-limit")
def check_limit(user_id: str):
    """Prüft, ob der Nutzer sein Limit erreicht hat."""
    if user_id not in user_data:
        user_data[user_id] = {"remaining_images": 10, "subscription_tier": "Basic 10 Bilder/Monat"}  # Standard

    user_info = user_data[user_id]
    return {
        "allowed": user_info["remaining_images"] > 0,
        "remaining_images": user_info["remaining_images"],
        "subscription_tier": user_info["subscription_tier"],
        "message": "Du kannst noch {} Bilder generieren.".format(user_info["remaining_images"]) if user_info["remaining_images"] > 0 else "Dein Limit ist erreicht! Upgrade dein Abo für mehr Bilder."
    }

# API: Bildgenerierung mit Limit-Kontrolle
@app.post("/generate-image")
def generate_image(request: ImageRequest):
    user_id = request.user_id
    prompt = request.prompt

    if user_id not in user_data:
        raise HTTPException(status_code=404, detail="User nicht gefunden")

    user_info = user_data[user_id]

    # **LIMIT PRÜFEN**
    if user_info["remaining_images"] <= 0:
        return {
            "error": "Limit erreicht",
            "message": "Dein Limit ist erreicht! Upgrade dein Abo für mehr Bilder.",
            "upgrade_url": UPGRADE_URL,
            "next_tier": "Pro 50 Bilder/Monat",
            "subscription_tier": user_info["subscription_tier"]
        }

    # **FAKE-BILDGENERIERUNG**
    image_url = f"https://fakeimageapi.com/generate/{prompt.replace(' ', '_')}.png"

    # **LIMIT VERRINGERN**
    user_data[user_id]["remaining_images"] -= 1

    return {
        "image_url": image_url,
        "remaining_images": user_data[user_id]["remaining_images"],
        "subscription_tier": user_data[user_id]["subscription_tier"]
    }

# API: Upgrade-Prozess
@app.post("/upgrade")
def upgrade_subscription(request: UpgradeRequest):
    user_id = request.user_id
    new_plan = request.new_plan

    if user_id not in user_data:
        raise HTTPException(status_code=404, detail="User nicht gefunden")

    # **Upgrade durchführen**
    if new_plan in subscription_limits:
        user_data[user_id]["subscription_tier"] = new_plan
        user_data[user_id]["remaining_images"] = subscription_limits[new_plan]

        return {
            "message": "Upgrade erfolgreich!",
            "subscription_tier": new_plan,
            "remaining_images": subscription_limits[new_plan]
        }
    else:
        raise HTTPException(status_code=400, detail="Ungültiger Plan")

# Starte die API
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)