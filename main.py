from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse
import logging
import httpx

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] GoldenSnacksEngine: %(message)s")
logger = logging.getLogger("GoldenSnacksEngine")

app = FastAPI(title="Golden Snacks BBQ Production Engine")

VERIFY_TOKEN = "GoldenSnacksSecureToken2026"

# 🟢 TRUE PRODUCTION IDENTIFIERS
ACCESS_TOKEN = "EAAcuJlexuR4BRjT2UFRyTyUgpQZCUqSVigCoFY4jtIS7FZCGoTZCPpIouktJzKoM7I1QkF4WZB5NRwHrIBNE6QnsuDZBH1cBfZAsZAS2LCxSeTlJkztDt29qIsPRzphgPHiABG4xvLfgnLrbqD553dKz71cZBp7oZAyw6yahLaPdPWzC7Y3c67GinfApKZAiS2PQNV4FxmUtqJZCuu9ClmBubzdkWH8h8DeJ2z0ZBZA85"
PHONE_NUMBER_ID = "1191114327413754"
FLOW_ID = "26769930609374582"

@app.get("/")
async def root_check():
    return {"status": "active", "message": "Golden Snacks Engine is online!"}

@app.get("/privacy", response_class=HTMLResponse)
async def privacy_policy_page():
    """Keeps Meta's crawler happy by serving a valid HTML page."""
    return """
    <html>
        <head><title>Privacy Policy - Golden Snacks & BBQ</title></head>
        <body style="font-family: Arial, sans-serif; padding: 40px; line-height: 1.6;">
            <h2>Privacy Policy for Golden Snacks & BBQ Bot</h2>
            <p><strong>Last Updated: June 13, 2026</strong></p>
            <p>We process selections solely to communicate with restaurant terminals and database logging engines.</p>
        </body>
    </html>
    """

@app.get("/webhooks/whatsapp")
async def webhook_verification(request: Request):
    params = request.query_params
    if params.get("hub.mode") == "subscribe" and params.get("hub.verify_token") == VERIFY_TOKEN:
        return Response(content=params.get("hub.challenge"), media_type="text/plain")
    return Response(content="Verification failed", status_code=403)

async def send_whatsapp_flow(recipient_phone: str):
    """Sends the official dynamic WhatsApp Flow layout menu card."""
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
            "type": "flow",
            "header": {
                "type": "text",
                "text": "Golden Snacks & BBQ 🍔"
            },
            "body": {
                "text": "Welcome to our digital kitchen! Tap the button below to browse categories, select items, and place your order directly."
            },
            "footer": {
                "text": "Powered by Haniya Global Network"
            },
            "action": {
                "name": "flow",
                "parameters": {
                    "flow_message_version": "3",
                    "flow_token": "token_snacks_001",
                    "flow_id": FLOW_ID,
                    "flow_cta": "View Food Menu",
                    "action": "navigate",
                    "flow_action_handler_version": "yes",
                    "flow_input_data": {
                        "initial_screen": "CATEGORY_SELECTOR",
                        "data": {}
                    }
                }
            }
        }
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload, headers=headers)
        logger.info(f"📤 Flow Send Status Code: {response.status_code} | Response: {response.text}")
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
                
                # 1. Capture text triggers from customer devices
                if "messages" in value and value["messages"]:
                    msg_obj = value["messages"][0]
                    sender_phone = msg_obj.get("from")
                    
                    if msg_obj.get("type") == "text":
                        user_text = msg_obj["text"].get("body", "").strip().lower()
                        if user_text == "menu":
                            logger.info(f"⚡ Dispatching interactive menu Flow directly to {sender_phone}...")
                            await send_whatsapp_flow(sender_phone)
                            
                # 2. Capture structural responses returned from the WhatsApp Flow UI
                elif "flow_reply" in value:
                    # Form data payload submissions will be processed here
                    logger.info("📥 Flow form submitted successfully by user!")
                    
        return {"status": "processed"}
    except Exception as e:
        logger.error(f"💥 WEBHOOK EXCEPTION: {str(e)}")
        return {"status": "error"}