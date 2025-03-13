@app.post("/check-limit-before-generation")
async def check_limit_before_generation(request: UserRequest):
    """ Überprüft, ob der Nutzer noch Credits hat, bevor ein Bild generiert wird. """
    
    if not request.email:
        return {"error": "❌ E-Mail erforderlich!"}

    conn = get_db_connection()
    email_hash = generate_user_id(request.email)

    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT used_credits, max_credits, subscription_active 
                FROM user_limits 
                WHERE email_hash = %s
            """, (email_hash,))
            result = cursor.fetchone()

            if not result:
                return {"error": "⚠️ Du bist nicht registriert! Bitte kaufe ein Abo.", "register_url": DIGISTORE_ABO_URL}

            used_credits, max_credits, subscription_active = result

            if not subscription_active:
                return {"error": "🚫 Dein Abo ist inaktiv! Reaktiviere es, um fortzufahren.", "register_url": DIGISTORE_ABO_URL}

            if used_credits >= max_credits:
                return {"error": "🚫 Dein Limit ist erreicht! Upgrade erforderlich.", "upgrade_url": DIGISTORE_ABO_URL}

            return {
                "allowed": True,
                "remaining_images": max_credits - used_credits,
                "message": f"✅ Du kannst noch {max_credits - used_credits} Bilder erstellen."
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"🚨 Fehler in /check-limit-before-generation: {str(e)}")

    finally:
        conn.close()
