from flask import Flask, request, jsonify

app = Flask(__name__)

# Simulierte Datenbank für Nutzerlimits mit mehreren Abo-Stufen
user_data = {
    "user_123": {"remaining_images": 10, "subscription_tier": "Basic 10 Bilder/Monat"}
}

subscription_limits = {
    "Basic 10 Bilder/Monat": 10,
    "Pro 50 Bilder/Monat": 50,
    "Ultimate 200 Bilder/Monat": 200
}

NGROK_URL = "https://eaed-2001-4bc9-905-d70c-ac12-2dde-4da1-54fc.ngrok-free.app"
UPGRADE_URL = "https://www.checkout-ds24.com/product/599133"

def get_user_limit(user_id):
    user_info = user_data.get(user_id, {"remaining_images": 0, "subscription_tier": "Kein Abo"})
    return user_info

openapi_spec = {
    "openapi": "3.1.0",
    "info": {
        "title": "Motion API",
        "version": "1.0.0",
        "description": "API für die Verwaltung von Bildgenerierungslimits und Abonnements in Motion."
    },
    "servers": [
        {"url": NGROK_URL}
    ],
    "paths": {
        "/check-limit": {
            "post": {
                "summary": "Überprüft das Bildlimit eines Nutzers",
                "operationId": "checkLimit",
                "responses": {
                    "200": {
                        "description": "Erfolgreiche Antwort",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "allowed": {"type": "boolean"},
                                        "remaining_images": {"type": "integer"},
                                        "subscription_tier": {"type": "string"},
                                        "message": {"type": "string"}
                                    }
                                }
                            }
                        }
                    }
                }
            }
        },
        "/generate-image": {
            "post": {
                "summary": "Generiert ein Bild für den Nutzer",
                "operationId": "generateImage",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "user_id": {"type": "string"},
                                    "prompt": {"type": "string"}
                                },
                                "required": ["user_id", "prompt"]
                            }
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "Bild erfolgreich generiert",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "image_url": {"type": "string"},
                                        "remaining_images": {"type": "integer"},
                                        "subscription_tier": {"type": "string"}
                                    }
                                }
                            }
                        }
                    },
                    "403": {
                        "description": "Limit erreicht - Upgrade erforderlich",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "error": {"type": "string"},
                                        "message": {"type": "string", "default": "Dein Limit ist erreicht! Upgrade dein Abo für mehr Bilder."},
                                        "upgrade_url": {"type": "string", "default": UPGRADE_URL},
                                        "next_tier": {"type": "string"},
                                        "subscription_tier": {"type": "string"}
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

@app.route('/openapi.json', methods=['GET'])
def get_openapi_spec():
    response = jsonify(openapi_spec)
    response.headers['Content-Type'] = 'application/json; charset=utf-8'
    return response, 200

@app.route('/check-limit', methods=['POST'])
def check_limit():
    user_id = "user_123"  # Standardbenutzer für das Testen
    user_info = get_user_limit(user_id)
    return jsonify({
        "allowed": user_info["remaining_images"] > 0,
        "remaining_images": user_info["remaining_images"],
        "subscription_tier": user_info["subscription_tier"],
        "message": "Du kannst noch {} Bilder generieren.".format(user_info["remaining_images"]) if user_info["remaining_images"] > 0 else "Dein Limit ist erreicht! Upgrade dein Abo für mehr Bilder."
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
from fastapi import FastAPI, Request
import requests

app = FastAPI()

# Simulierte User-Datenbank
user_data = {}

@app.post("/upgrade")
async def handle_upgrade(request: Request):
    """Empfängt das Upgrade von Digistore24 über Zapier"""
    data = await request.json()
    
    user_id = data.get("user_id")
    new_plan = data.get("new_plan")
    payment_status = data.get("payment_status")

    if payment_status == "completed":
        user_data[user_id] = {"images_generated": 0, "plan": new_plan}  # Upgrade freischalten
        
        # Informiere Motion über das Upgrade
        motion_url = "http://localhost:8000/motion-upgrade"  # Falls Motion eine eigene API hat
        requests.post(motion_url, json={"user_id": user_id, "new_plan": new_plan})
        
        return {"status": "Upgrade successful", "new_plan": new_plan}
    
    return {"status": "Payment not completed"}
