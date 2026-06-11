from fastapi import FastAPI, Request, Response
import logging
import httpx

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] GoldenSnacksEngine: %(message)s")
logger = logging.getLogger("GoldenSnacksEngine")

app = FastAPI(title="Golden Snacks BBQ WhatsApp Engine")

VERIFY_TOKEN = "GoldenSnacksSecureToken2026"

# 🔴 CRITICAL: Insert your Meta credentials here from your dashboard
ACCESS_TOKEN = "EAAcuJlexuR4BRjIAcummm8JvwCHOKlWtla0UxFDl2qxeOejWymHbN0zBXZBM8QZC8jh1dQZALTKHKDffJOM1txYHXy0bfI1rrkL4WLf9avRwfChlJEO3Et6dZAfYr2iJIlUAi2FnjaG1RUtV0OffhHPmaGFpZA3nYvBoVBmZBURlD9S694juDmfyKAluKbrAbkfPWSD6jlRipeqH3cXmIfGitvcBmpeGAH" # Your long permanent token
PHONE_NUMBER_ID = "1105147339354101" 
FLOW_ID = "1324144613240759" 

@app.get("/")
async def root_check():
    return {"status": "active", "message": "Golden Snacks Engine is fully online!"}

@app.get("/webhooks/whatsapp")
async def webhook_verification(request: Request):
    params = request.query_params
    if params.get("hub.mode") == "subscribe" and params.get("hub.verify_token") == VERIFY_TOKEN:
        logger.info("🚀 SUCCESS: Meta Webhook handshake verified and linked!")
        return Response(content=params.get("hub.challenge"), media_type="text/plain")
    return Response(content="Verification failed", status_code=403)

async def send_whatsapp_flow(recipient_phone: str):
    """Constructs and fires an official Meta Interactive Flow object back to the user's phone."""
    url = f"https://graph.facebook.com/v25.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # Payload architecture defining the interactive WhatsApp Flow button element
    # Upgraded, clean payload structure conforming to strict API routing keys
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": recipient_phone,
        "type": "interactive",
        "interactive": {
            "type": "flow",
            "header": {
                "type": "text",
                "text": "Golden Snacks Kitchen"
            },
            "body": {
                "text": "Tap the button below to view our interactive digitized menu layout!"
            },
            "footer": {
                "text": "Powered by Mutamdost Backend Engine"
            },
            "action": {
                "name": "flow",
                "parameters": {
                    "flow_message_version": "3.0",
                    "flow_token": "goldensnacks_session_001",
                    "flow_id": FLOW_ID,
                    "flow_cta": "View Food Menu",
                    "flow_action": "navigate"
                }
            }
        }
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload, headers=headers)
        logger.info(f"📤 Outbound Flow Status Code: {response.status_code} | Response: {response.text}")
        return response.json()

@app.post("/webhooks/whatsapp")
async def handle_whatsapp_traffic(request: Request):
    try:
        payload = await request.json()
        logger.info(f"📥 RAW PAYLOAD RECEIVED: {payload}")
        
        # 1. Handle user completions coming directly from the interactive Flow menu selection layout
        if "action" in payload and payload.get("action") == "request_routing":
            flow_data = payload.get("data", {})
            logger.info(f"🍔 INTERACTIVE FLOW SELECTION CAPTURED! Form Submission: {flow_data}")
            return {
                "version": "3.0",
                "screen": "CATEGORY_SELECTOR",
                "data": {"extension_message_response": {"params": {"current_screen": "CATEGORY_SELECTOR", "status": "success"}}}
            }
        
        # 2. Handle normal incoming chat messages from users
        if "entry" in payload and payload["entry"]:
            changes = payload["entry"][0].get("changes", [])
            if changes and "value" in changes[0]:
                value = changes[0]["value"]
                if "messages" in value and value["messages"]:
                    msg_obj = value["messages"][0]
                    sender_phone = msg_obj.get("from")
                    
                    if "text" in msg_obj and msg_obj["text"]:
                        user_text = msg_obj["text"].get("body", "").strip().lower()
                        logger.info(f"💬 Normal Chat Message Recognized from {sender_phone}: '{user_text}'")
                        
                        # Trigger the outward Flow object transmission if user says "menu"
                        if user_text == "menu":
                            logger.info(f"⚡ Trimming flow deployment command routing for {sender_phone}...")
                            await send_whatsapp_flow(sender_phone)
                            
        return {"status": "processed"}
    except Exception as e:
        logger.error(f"💥 CRITICAL ERROR: {str(e)}")
        return {"status": "error"}