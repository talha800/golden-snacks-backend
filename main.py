from fastapi import FastAPI, Request, Response, status
import logging
import json

# Setup clear, beautiful terminal logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("GoldenSnacksEngine")

app = FastAPI(title="Golden Snacks & BBQ - Core Webhook Engine")

# This is our custom security handshake password
MY_SECRET_VERIFY_TOKEN = "GoldenSnacksSecureToken2026"

@app.get("/webhooks/whatsapp")
async def verify_meta_handshake(request: Request):
    """
    Meta hits this GET endpoint to verify your server is real.
    """
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")
    
    if mode == "subscribe" and token == MY_SECRET_VERIFY_TOKEN:
        logger.info("🚀 SUCCESS: Meta Webhook handshake verified and linked!")
        return Response(content=challenge, media_type="text/plain")
        
    logger.error("❌ ERROR: Handshake failed. The verification tokens do not match.")
    return Response(content="Verification Failed", status_code=status.HTTP_403_FORBIDDEN)


@app.post("/webhooks/whatsapp")
async def ingest_whatsapp_traffic(request: Request):
    """
    Ingests all incoming live text messages and layout data packets from your phone.
    """
    try:
        payload = await request.json()
        logger.info(f"📥 RAW PAYLOAD RECEIVED: {json.dumps(payload, indent=2)}")
        
        # Guard layer against empty system test pings from Meta
        if "entry" not in payload:
            return {"status": "ignored", "reason": "System verification ping"}
            
        return {"status": "success"}
        
    except Exception as e:
        logger.error(f"💥 CRITICAL API FAILURE: {str(e)}")
        return Response(content="Internal Server Error", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)