from fastapi import FastAPI, Request, Response
import logging

# Configure Clean Console Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] GoldenSnacksEngine: %(message)s")
logger = logging.getLogger("GoldenSnacksEngine")

app = FastAPI(title="Golden Snacks BBQ WhatsApp Engine")

# Secret Verification Token
VERIFY_TOKEN = "GoldenSnacksSecureToken2026"

@app.get("/")
async def root_check():
    return {"status": "active", "message": "Golden Snacks Engine is fully online!"}

@app.get("/webhooks/whatsapp")
async def webhook_verification(request: Request):
    """Handles the secure handshake verification with Meta Developer Portal."""
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")
    
    if mode == "subscribe" and token == VERIFY_TOKEN:
        logger.info("🚀 SUCCESS: Meta Webhook handshake verified and linked!")
        return Response(content=challenge, media_type="text/plain")
    
    logger.warning("❌ ERROR: Handshake failed. Invalid verify token provided.")
    return Response(content="Verification failed", status_code=403)

@app.post("/webhooks/whatsapp")
async def handle_whatsapp_traffic(request: Request):
    """Processes incoming live chat messages and interactive WhatsApp Flow forms."""
    try:
        payload = await request.json()
        logger.info(f"📥 RAW PAYLOAD RECEIVED: {payload}")
        
        # Check if the data block contains an interactive WhatsApp Flow submission
        if "action" in payload and payload.get("action") == "request_routing":
            flow_data = payload.get("data", {})
            logger.info(f"🍔 INTERACTIVE FLOW RECEIVED! User chose category: {flow_data}")
            
            # Respond to Meta with a mandatory layout success acknowledgment wrapper
            response_payload = {
                "version": "3.0",
                "screen": "CATEGORY_SELECTOR",
                "data": {
                    "extension_message_response": {
                        "params": {
                            "current_screen": "CATEGORY_SELECTOR",
                            "status": "success"
                        }
                    }
                }
            }
            return response_payload

        # Keep handling fallback text messages safely
        return {"status": "processed", "message": "Standard payload handled successfully"}

    except Exception as e:
        logger.error(f"💥 CRITICAL PROCESSING ERROR: {str(e)}")
        return {"status": "error", "message": "Internal processing exception"}