from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse
import logging
import httpx

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] GoldenSnacksEngine: %(message)s")
logger = logging.getLogger("GoldenSnacksEngine")

app = FastAPI(title="Golden Snacks BBQ Production Engine")

VERIFY_TOKEN = "GoldenSnacksSecureToken2026"

# 🟢 FINAL PRODUCTION ACCESS ROUTING (NEVER EXPIRES)
ACCESS_TOKEN = "EAAcuJlexuR4BRsNevJaEulZBX6BzrGifrBAxwUqgNPPI5zeB6woYvJCTDpl00DS0ShBwC5mUzCzlKMCqfcC2HVRyjuAzV9rkZAHtzoMFkoZAzscuWM8iyVvneeDxUcWlBiSvnhwKjCL47ckMvxOlBZA1pDZBzoqKdy9wHeSD2RHXdCcivD4ZBWmxkkZCHYoPfvFDQy3oPbb5lUOUax36wDqiZCbx3OQQBQRzk87W"
PHONE_NUMBER_ID = "1191114327413754"

@app.get("/")
async def root_check():
    return {"status": "active", "message": "Golden Snacks Engine is online!"}

@app.get("/privacy", response_class=HTMLResponse)
async def privacy_policy_page():
    """Keeps Meta's crawler happy with a valid legal page template."""
    return """
    <html>
        <head><title>Privacy Policy - Golden Snacks & BBQ</title></head>
        <body style="font-family: Arial, sans-serif; padding: 40px; line-height: 1.6;">
            <h2>Privacy Policy for Golden Snacks & BBQ Bot</h2>
            <p><strong>Last Updated: June 13, 2026</strong></p>
            <p>We process text selections solely to communicate with restaurant terminals and database logging engines.</p>
        </body>
    </html>
    """

@app.get("/webhooks/whatsapp")
async def webhook_verification(request: Request):
    params = request.query_params
    if params.get("hub.mode") == "subscribe" and params.get("hub.verify_token") == VERIFY_TOKEN:
        return Response(content=params.get("hub.challenge"), media_type="text/plain")
    return Response(content="Verification failed", status_code=403)

async def send_interactive_menu(recipient_phone: str):
    """Sends a robust, production-compliant interactive category selection list sheet."""
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
                "text": "Welcome to our digital kitchen! Please select a food category below to view our available items:"
              },
            "footer": {
                "text": "Powered by Haniya Global Network"
            },
            "action": {
                "button": "View Categories",
                "sections": [
                    {
                        "title": "Our Full Menu",
                        "rows": [
                            {
                                "id": "cat_biryani",
                                "title": "Biryani Specials",
                                "description": "Authentic chicken & mutton biryani"
                            },
                            {
                                "id": "cat_pizza",
                                "title": "Pizza Options",
                                "description": "Freshly baked pan pizzas"
                            },
                            {
                                "id": "cat_fastfood",
                                "title": "Fast Food Favorites",
                                "description": "Zinger burgers & club sandwiches"
                            },
                            {
                                "id": "cat_bbq",
                                "title": "BBQ Rolls",
                                "description": "Chicken boti & beef seekh rolls"
                            }
                        ]
                    }
                ]
            }
        }
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload, headers=headers)
        logger.info(f"📤 List Menu Send Status Code: {response.status_code} | Response: {response.text}")
        return response.json()

@app.post("/webhooks/whatsapp")
async def handle_whatsapp_traffic(request: Request):
    try:
        payload = await request.json()
        logger.info(f"📥 RAW PAYLOAD RECEIVED: {payload}")
        
        if "entry" in payload and payload["entry"]:
            entry_obj = payload["entry"][0]
            if "changes" in entry_obj and entry_obj["changes"]:
                value = entry_obj["changes"][0].get("value", {})
                
                # 1. Capture Inbound Messages (Triggers menu on text input)
                if "messages" in value and value["messages"]:
                    msg_obj = value["messages"][0]
                    sender_phone = msg_obj.get("from")
                    
                    if msg_obj.get("type") == "text":
                        user_text = msg_obj["text"].get("body", "").strip().lower()
                        if user_text == "menu":
                            logger.info(f"⚡ Dispatching interactive category matrix directly to {sender_phone}...")
                            await send_interactive_menu(sender_phone)
                            
                    # 2. Capture Menu Selections (Triggers when user clicks an option in the list)
                    elif msg_obj.get("type") == "interactive":
                        interactive_obj = msg_obj.get("interactive", {})
                        if interactive_obj.get("type") == "list_reply":
                            chosen_id = interactive_obj.get("list_reply", {}).get("id")
                            logger.info(f"🍔 SUCCESS! User selected menu category ID: {chosen_id}")
                            
        return {"status": "processed"}
    except Exception as e:
        logger.error(f"💥 WEBHOOK EXCEPTION: {str(e)}")
        return {"status": "error"}