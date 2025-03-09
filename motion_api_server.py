from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests

app = FastAPI()

# Upgrade-URL für Digistore24
UPGRADE_URL = "https://www.checkout-ds24.com/product/599133"

# Nutzer-Datenbank (Wird in Zukunft in einer echten Datenbank gespeichert)
user_data = {
    "testuser123": {
        "remaining_images": 10,
        "subscription_tier": "Basic 10 Bilder"
    }
}

# Soft-Limit für "Enterprise Unbegrenzt", um hohe Serverkosten zu vermeiden
subs = {
    "Enterprise Unbegrenzt": 1000
}

class UserRequest(BaseModel):
    user_id: str

@app.post("/check-limit")
def check_limit(request: UserRequest):
    """Prüft, ob der Nutzer sein Limit erreicht hat."""
    user_id = request.user_id
    if user_id in user_data:
        return user_data[user_id]
    else:
        raise HTTPException(status_code=404, detail="Benutzer wurde nicht gefunden.")

@app.post("/generate-image")
def generate_image(request: UserRequest):
    """Reduziert das Limit des Nutzers, wenn ein Bild generiert wird."""
    user_id = request.user_id
    if user_id in user_data:
        if user_data[user_id]["remaining_images"] > 0:
            user_data[user_id]["remaining_images"] -= 1
            return {"message": "Bild erfolgreich generiert!", "remaining_images": user_data[user_id]["remaining_images"]}
        else:
            return {"message": "Limit erreicht! Bitte ein Upgrade durchführen.", "upgrade_url": UPGRADE_URL}
    else:
        raise HTTPException(status_code=404, detail="Benutzer wurde nicht gefunden.")

@app.post("/upgrade")
def upgrade_subscription(request: UserRequest):
    """Erhöht das Limit für den Nutzer."""
    user_id = request.user_id
    if user_id in user_data:
        tier = user_data[user_id]["subscription_tier"]
        if tier in subs:
            user_data[user_id]["remaining_images"] = subs[tier]
            return {"message": "Upgrade erfolgreich!", "new_limit": subs[tier]}
        else:
            return {"message": "Kein passendes Upgrade verfügbar."}
    else:
        raise HTTPException(status_code=404, detail="Benutzer wurde nicht gefunden.")
