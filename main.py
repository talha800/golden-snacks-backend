from fastapi import FastAPI, Request, Response
import logging
import httpx

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] GoldenSnacksEngine: %(message)s")
logger = logging.getLogger("GoldenSnacksEngine")

app = FastAPI(title="Golden Snacks BBQ WhatsApp Engine")

VERIFY_TOKEN = "GoldenSnacksSecureToken2026"

# 🟢 LIVE CONFIGURATION KEYS
ACCESS_TOKEN = "YOUR_PERMANENT_ACCESS_TOKEN"
PHONE_NUMBER_ID = "1191114327413754"

@app.get("/")
async def root_check():
    return {"status": "active", "message": "Golden Snacks Engine is online!"}

@app.get("/webhooks/whatsapp")
async def webhook_verification(request: Request):
    params = request.query_params
    if params.get("hub.mode") == "subscribe" and params.get("hub.verify_token") == VERIFY_TOKEN:
        return Response(content=params.get("hub.challenge"), media_type="text/plain")
    return Response(content="Verification failed", status_code=403)

async def send_interactive_menu(recipient_phone: str):
    """Sends a native, premium WhatsApp Interactive List Message to select food categories."""
    url = f"https://graph.facebook.com/v25.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": recipient_phone,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "header": {
                "type": "text",
                "text": "Golden Snacks & BBQ 🍔"
            },
            "body": {
                "text": "Welcome to our digital kitchen! Please tap the button below to browse our menu categories and start your order."
            },
            "footer": {
                "text": "Select an option to view items"
            },
            "action": {
                "button": "View Categories",
                "sections": [
                    {
                        "title": "Main Food Menu",
                        "rows": [
                            {"id": "cat_biryani", "title": "Biryani Specials", "description": "Authentic chicken & mutton biryani"},
                            {"id": "cat_pizza", "title": "Pizza Options", "description": "Freshly baked pan pizzas"},
                            {"id": "cat_fastfood", "title": "Fast Food Favorites", "description": "Zinger burgers & club sandwiches"},
                            {"id": "cat_bbq", "title": "BBQ Rolls", "description": "Chicken boti & beef seekh rolls"}
                        ]
                    }
                ]
            }
        }
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload, headers=headers)
        logger.info(f"📤 List Message Status Code: {response.status_code} | Response: {response.text}")
        return response.json()

@app.post("/webhooks/whatsapp")
async def handle_whatsapp_traffic(request: Request):
    try:
        payload = await request.json()
        logger.info(f"📥 RAW PAYLOAD RECEIVED: {payload}")
        
        if "entry" in payload and payload["entry"]:
            changes = payload["entry"][0].get("changes", [])
            if changes and "value" in changes[0]:
                value = changes[0]["value"]
                
                # 1. Capture interactive dropdown selection from the user's phone
                if "messages" in value and value["messages"]:
                    msg_obj = value["messages"][0]
                    sender_phone = msg_obj.get("from")
                    
                    if msg_obj.get("type") == "interactive":
                        interactive_obj = msg_obj.get("interactive", {})
                        if interactive_obj.get("type") == "list_reply":
                            selection_id = interactive_obj.get("list_reply", {}).get("id")
                            logger.info(f"🍔 SUCCESS! User selected menu category ID: {selection_id}")
                            # Here is where we will hook up Supabase to pull items matching this ID!
                            return {"status": "processed"}
                    
                    # 2. Capture normal text message "menu" trigger
                    if "text" in msg_obj and msg_obj["text"]:
                        user_text = msg_obj["text"].get("body", "").strip().lower()
                        if user_text == "menu":
                            logger.info(f"⚡ Sending active menu list layout to {sender_phone}...")
                            await send_interactive_menu(sender_phone)
                            
        return {"status": "processed"}
    except Exception as e:
        logger.error(f"💥 ERROR: {str(e)}")
        return {"status": "error"}