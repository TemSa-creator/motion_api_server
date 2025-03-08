from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
import uvicorn

app = FastAPI()

# 🔥 Digistore24 Upgrade-Link
UPGRADE_URL = "https://www.checkout-ds24.com/product/599133"

# 🔥 Nutzer-Datenbank (später echte Datenbank)
user_data = {
    "testuser123": {"remaining_images": 10, "subscription_tier": "Basic 10 Bilder"},
}

# 🔥 Soft-Limit für Abo-Nutzer
subs = {"Enterprise Unbegrenzt": 1000}  # Begrenzung für Serverkosten


class UserRequest(BaseModel):
    user_id: str


@app.get("/")
def home():
    return {"message": "Server läuft perfekt!"}


@app.post("/check-limit")
def check_limit(request: UserRequest):
    user_id = request.user_id

    if user_id not in user_data:
        raise HTTPException(status_code=404, detail="Benutzer nicht gefunden!")

    user_info = user_data[user_id]
    return {
        "remaining_images": user_info["remaining_images"],
        "subscription_tier": user_info["subscription_tier"],
    }


@app.get("/upgrade")
def upgrade():
    return {"upgrade_link": UPGRADE_URL}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=10001)
