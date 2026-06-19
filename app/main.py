import logging
import httpx
from fastapi import FastAPI, Depends, Query, HTTPException, status, Request, Response
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.services.menu_service import MenuService

# =====================================================================
# SYSTEM CORE LOGGING & INITIALIZATION
# =====================================================================
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] GoldenSnacksEngine: %(message)s")
logger = logging.getLogger("GoldenSnacksEngine")

# Initialize the main FastAPI application core engine
app = FastAPI(
    title=settings.PROJECT_NAME,
    version="2.0.0",
    docs_url="/api/docs" if settings.ENV_MODE == "DEVELOPMENT" else None
)

# Meta API Cloud Config Tokens (Kept safe from your working setup)
ACCESS_TOKEN = "EAAcuJlexuR4BRsNevJaEulZBX6BzrGifrBAxwUqgNPPI5zeB6woYvJCTDpl00DS0ShBwC5mUzCzlKMCqfcC2HVRyjuAzV9rkZAHtzoMFkoZAzscuWM8iyVvneeDxUcWlBiSvnhwKjCL47ckMvxOlBZA1pDZBzoqKdy9wHeSD2RHXdCcivD4ZBWmxkkZCHYoPfvFDQy3oPbb5lUOUax36wDqiZCbx3OQQBQRzk87W"  # Your raw production token here
PHONE_NUMBER_ID = "1191114327413754"

# =====================================================================
# SYSTEM HEALTH & PRIVACY POLICY PAGES
# =====================================================================

@app.get("/", status_code=status.HTTP_200_OK)
async def root_check():
    return {"status": "active", "message": "Golden Snacks Production Engine is online!"}

@app.get("/health", status_code=status.HTTP_200_OK)
def system_health_check():
    """Lightweight health monitoring probe used by Render."""
    return {
        "status": "healthy",
        "engine": "Mutam Dost Core Backend",
        "environment": settings.ENV_MODE
    }

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

# =====================================================================
# META WHATSAPP WEBHOOK ROUTING GATEWAY (VERIFICATION & TRAFFIC)
# =====================================================================

@app.get("/webhooks/whatsapp")
@app.get("/webhook")  # Supports both your old and new routing aliases
async def whatsapp_webhook_verification(request: Request):
    """Handles the security handshake from Meta's servers."""
    params = request.query_params
    hub_mode = params.get("hub.mode")
    hub_verify_token = params.get("hub.verify_token")
    hub_challenge = params.get("hub.challenge")

    # Double checks against our centralized .env token
    if hub_mode == "subscribe" and hub_verify_token == settings.WHATSAPP_VERIFY_TOKEN:
        logger.info("🚀 [META WEBHOOK] Verification Challenge Passed Successfully!")
        return Response(content=hub_challenge, media_type="text/plain")
    
    logger.warning("❌ [META WEBHOOK] Verification Failed due to token mismatch.")
    return Response(content="Verification failed", status_code=403)


@app.post("/webhooks/whatsapp")
@app.post("/webhook")
async def handle_whatsapp_traffic(request: Request, db: Session = Depends(get_db)):
    """
    Processes inbound real-time WhatsApp message payloads and triggers menus 
    dynamically mapped straight out of our Supabase PostgreSQL architecture.
    """
    try:
        payload = await request.json()
        logger.info(f"📥 RAW PAYLOAD RECEIVED: {payload}")
        
        if "entry" in payload and payload["entry"]:
            entry_obj = payload["entry"][0]
            if "changes" in entry_obj and entry_obj["changes"]:
                value = entry_obj["changes"][0].get("value", {})
                
                # 1. Capture Inbound Text Triggers (e.g., user types "menu")
                if "messages" in value and value["messages"]:
                    msg_obj = value["messages"][0]
                    sender_phone = msg_obj.get("from")
                    
                    if msg_obj.get("type") == "text":
                        user_text = msg_obj["text"].get("body", "").strip().lower()
                        if user_text in ["menu", "hi", "hello", "bhai"]:
                            logger.info(f"⚡ Dispatching interactive category matrix directly to {sender_phone}...")
                            await send_interactive_menu(sender_phone)
                            
                    # 2. Capture List Replies (User clicked an option)
                    elif msg_obj.get("type") == "interactive":
                        interactive_obj = msg_obj.get("interactive", {})
                        if interactive_obj.get("type") == "list_reply":
                            chosen_id = interactive_obj.get("list_reply", {}).get("id")
                            chosen_title = interactive_obj.get("list_reply", {}).get("title")
                            chosen_desc = interactive_obj.get("list_reply", {}).get("description")
                            
                            # 🟢 ROUTE A: User picked a general menu category
                            if chosen_id.startswith("cat_"):
                                logger.info(f"🍔 Category Selection intercepted: {chosen_id}")
                                await send_branch_skus(sender_phone, branch_code="JED_AZIZIYAH", category_id=chosen_id, db=db)
                            
                            # 🟢 ROUTE B: User selected a specific size to order!
                            elif chosen_id.startswith("sku_"):
                                clean_sku_id = chosen_id.replace("sku_", "")
                                logger.info(f"🛒 Shopping Cart Item Captured! SKU UUID: {clean_sku_id}")
                                
                                # Send a success confirmation text message to stop the loop
                                await send_cart_confirmation(sender_phone, chosen_title, chosen_desc)
                            
        return {"status": "processed"}
    except Exception as e:
        logger.error(f"💥 WEBHOOK EXCEPTION: {str(e)}")
        return {"status": "error"}

# =====================================================================
# SHOPPING CART RECEIPT GENERATOR
# =====================================================================

async def send_cart_confirmation(recipient_phone: str, item_title: str, item_details: str):
    """Sends a clear confirmation receipt text once a specific SKU size is selected."""
    url = f"https://graph.facebook.com/v25.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # Extract only the price info out of the description string nicely
    price_info = item_details.split("➔")[-1].strip() if "➔" in item_details else item_details
    size_info = item_details.split("➔")[0].strip() if "➔" in item_details else "Standard"

    message_body = (
        f"🛒 *Added to Cart!* \n\n"
        f"🍽️ *Item:* {item_title}\n"
        f"⚖️ *Size:* {size_info}\n"
        f"💵 *Price:* {price_info}\n\n"
        f"Your digital order card has been updated. Type *'menu'* to add more items, or type *'checkout'* to complete your order!"
    )

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": recipient_phone,
        "type": "text",
        "text": {"body": message_body}
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload, headers=headers)
        logger.info(f"📤 Cart Confirmation Send Status Code: {response.status_code}")

# =====================================================================
# INTERACTIVE OUTBOUND MESSAGING PIPELINE
# =====================================================================

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
            "header": {"type": "text", "text": "Golden Snacks & BBQ 🍔"},
            "body": {"text": "Welcome to our digital kitchen! Please select a food category below to view our available items:"},
            "footer": {"text": "Powered by Haniya Global Network"},
            "action": {
                "button": "View Categories",
                "sections": [
                    {
                        "title": "Our Full Menu",
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
        logger.info(f"📤 List Menu Send Status Code: {response.status_code} | Response: {response.text}")
        return response.json()

# =====================================================================
# DYNAMIC DATABASE DATA DRIVEN MESSAGING ENGINE
# =====================================================================

async def send_branch_skus(recipient_phone: str, branch_code: str, category_id: str, db: Session):
    """
    Queries the database using our MenuService engine to fetch live items 
    matching the selected category, then structures a native WhatsApp message template.
    """
    # 1. Fetch current active menu from Supabase PostgreSQL
    raw_menu = MenuService.get_live_menu_for_whatsapp(db, branch_code=branch_code)
    
    # 2. Filter menu list items locally based on the selected category token
    # (Matches our codes: 'RIC' for Rice/Biryani, 'PZ' for Pizza, 'BGR' for Fast Food, etc.)
    prefix_map = {
        "cat_biryani": "RIC",
        "cat_pizza": "PZ",
        "cat_fastfood": "BGR",
        "cat_bbq": "GRV"  # Maps our Chicken Handi / Karahi items here
    }
    
    target_prefix = prefix_map.get(category_id, "RIC")
    filtered_items = [item for item in raw_menu if item["sku_code"].startswith(target_prefix)]
    
    if not filtered_items:
        text_payload = {
            "messaging_product": "whatsapp",
            "to": recipient_phone,
            "type": "text",
            "text": {"body": "Our kitchen has run out of items in this category for this shift! Please select another option."}
        }
    else:
        # 3. Compile structural list rows dynamically from live database fields
        rows = []
        for item in filtered_items:
            rows.append({
                "id": f"sku_{item['sku_id']}",
                "title": f"{item['name_en']}",
                "description": f"{item['portion_size']} ➔ {item['price']} SAR"
            })
            
        # Limit rows array length safely to comply with WhatsApp's maximum 10-row limit per list section
        rows = rows[:10]
        
        text_payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient_phone,
            "type": "interactive",
            "interactive": {
                "type": "list",
                "header": {"type": "text", "text": "Select Your Order 🍽️"},
                "body": {"text": "Tap below to view available sizes and add choices straight into your digital ordering card:"},
                "footer": {"text": "Prices include local VAT requirements"},
                "action": {
                    "button": "View Available Items",
                    "sections": [
                        {
                            "title": "Freshly Prepared Today",
                            "rows": rows
                        }
                    ]
                }
            }
        }

    # 4. Push out to Meta Graph API
    url = f"https://graph.facebook.com/v25.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=text_payload, headers=headers)
        logger.info(f"📤 Product List Send Status Code: {response.status_code}")

# =====================================================================
# LIVE MENU FETCHING PIPELINE DATA ENDPOINT
# =====================================================================

@app.get("/api/menu")
def fetch_live_branch_menu(
    branch_code: str = Query(..., description="The unique business code tracking token, e.g., JED_AZIZIYAH"),
    channel: str = Query("WHATSAPP", description="Target application channel format layout"),
    db: Session = Depends(get_db)
):
    """Fetches the active, real-time menu for a specific branch and channel from the database."""
    try:
        menu = MenuService.get_live_menu_for_whatsapp(db, branch_code=branch_code, channel=channel)
        return {
            "branch_code": branch_code,
            "channel": channel,
            "total_items": len(menu),
            "items": menu
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compile operational menu index framework: {str(e)}"
        )