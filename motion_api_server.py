from fastapi import FastAPI, Request
from pydantic import BaseModel
import requests

app = FastAPI(
    title="Motion API",
    description="API für die Verwaltung von Bildgenerierungslimits und Abonnements in Motion.",
    version="1.0.0",
)

# 📌 Simulierte User-Datenbank für Limits und Abos
user_data = {
    "user_123": {"remaining_images": 10, "subscription_tier": "Basic 10 Bilder/Monat"}
}

subscription_limits = {
    "Basic 10 Bilder/Monat": 10,
    "Pro 50 Bilder/Monat": 50,
    "Ultimate 200 Bilder/Monat": 200
}

UPGRADE_URL = "https://www.checkout-ds24.com/product/599133"

# 📌 ✅ Pydantic-Modelle für Request & Response
class CheckLimitRequest(BaseModel):
    user_id: str

class CheckLimitResponse(BaseModel):
    allowed: bool
    remaining_images: int
    subscription_tier: str
    message: str

class UpgradeRequest(BaseModel):
    user_id: str
    new_plan: str
    payment_status: str

class UpgradeResponse(BaseModel):
    status: str
    new_plan: str

class GenerateImageRequest(BaseModel):
    user_id: str
    prompt: str

class GenerateImageResponse(BaseModel):
    image_url: str
    remaining_images: int
    subscription_tier: str

class ErrorResponse(BaseModel):
    error: str
    message: str
    upgrade_url: str

@app.get("/", summary="Home", description="Startseite der API")
def home():
    return {"message": "Server läuft perfekt!"}

@app.post("/check-limit", response_model=CheckLimitResponse, summary="Check Limit", description="Überprüft das Bildlimit eines Nutzers")
async def check_limit(request: CheckLimitRequest):
    """Überprüft das Bildlimit eines Nutzers"""
    user_id = request.user_id

    if user_id not in user_data:
        user_data[user_id] = {"remaining_images": 10, "subscription_tier": "Basic 10 Bilder/Monat"}

    user_info = user_data[user_id]

    return CheckLimitResponse(
        allowed=user_info["remaining_images"] > 0,
        remaining_images=user_info["remaining_images"],
        subscription_tier=user_info["subscription_tier"],
        message="Du kannst noch {} Bilder generieren.".format(user_info["remaining_images"])
        if user_info["remaining_images"] > 0 else "Dein Limit ist erreicht! Upgrade dein Abo für mehr Bilder."
    )

@app.post("/upgrade", response_model=UpgradeResponse, summary="Handle Upgrade", description="Empfängt das Upgrade von Digistore24 über Zapier")
async def handle_upgrade(request: UpgradeRequest):
    """Empfängt das Upgrade von Digistore24 über Zapier"""
    user_id = request.user_id
    new_plan = request.new_plan
    payment_status = request.payment_status

    if payment_status == "completed":
        user_data[user_id] = {"remaining_images": subscription_limits.get(new_plan, 0), "subscription_tier": new_plan}
        return UpgradeResponse(status="Upgrade successful", new_plan=new_plan)
    
    return UpgradeResponse(status="Payment not completed", new_plan="")

@app.post("/generate-image", response_model=GenerateImageResponse, summary="Generate Image", description="Generiert ein Bild für den Nutzer")
async def generate_image(request: GenerateImageRequest):
    """Generiert ein Bild für den Nutzer"""
    user_id = request.user_id
    prompt = request.prompt

    if user_id not in user_data:
        return ErrorResponse(
            error="User not found",
            message="Bitte registriere dich zuerst.",
            upgrade_url=UPGRADE_URL
        )

    if user_data[user_id]["remaining_images"] <= 0:
        return ErrorResponse(
            error="Limit erreicht",
            message="Dein Limit ist erreicht! Upgrade dein Abo für mehr Bilder.",
            upgrade_url=UPGRADE_URL
        )

    # 📌 Reduziere das Bildlimit um 1
    user_data[user_id]["remaining_images"] -= 1

    # 📌 Simulierte Bildgenerierung
    image_url = f"https://fakeimageapi.com/generate/{prompt.replace(' ', '_')}.png"

    return GenerateImageResponse(
        image_url=image_url,
        remaining_images=user_data[user_id]["remaining_images"],
        subscription_tier=user_data[user_id]["subscription_tier"]
    )
