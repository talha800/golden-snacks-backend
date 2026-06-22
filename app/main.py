import logging
import httpx
import uuid
from fastapi import FastAPI, Depends, Query, HTTPException, status, Request, Response
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.config import settings
from app.database import get_db
from app.services.menu_service import MenuService

# =====================================================================
# SYSTEM CORE LOGGING & INITIALIZATION
# =====================================================================
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] GoldenSnacksEngine: %(message)s")
logger = logging.getLogger("GoldenSnacksEngine")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="2.1.1",
    docs_url="/api/docs" if settings.ENV_MODE == "DEVELOPMENT" else None
)

ACCESS_TOKEN = settings.WHATSAPP_ACCESS_TOKEN
PHONE_NUMBER_ID = settings.WHATSAPP_PHONE_NUMBER_ID

# =====================================================================
# SYSTEM HEALTH PROBES
# =====================================================================

@app.get("/", status_code=status.HTTP_200_OK)
async def root_check():
    return {"status": "active", "message": "Golden Snacks Production Engine is online!"}

@app.get("/health", status_code=status.HTTP_200_OK)
def system_health_check():
    return {"status": "healthy", "engine": "Mutam Dost Stateful Core Backend"}

# =====================================================================
# META WHATSAPP WEBHOOK ROUTING GATEWAY (VERIFICATION & TRAFFIC)
# =====================================================================

@app.get("/webhooks/whatsapp")
@app.get("/webhook")
async def whatsapp_webhook_verification(request: Request):
    params = request.query_params
    if params.get("hub.mode") == "subscribe" and params.get("hub.verify_token") == settings.WHATSAPP_VERIFY_TOKEN:
        logger.info("🚀 [META WEBHOOK] Verification Challenge Passed Successfully!")
        return Response(content=params.get("hub.challenge"), media_type="text/plain")
    return Response(content="Verification failed", status_code=403)


@app.post("/webhooks/whatsapp")
@app.post("/webhook")
async def handle_whatsapp_traffic(request: Request, db: Session = Depends(get_db)):
    """
    Stateful Webhook Gateway: Tracks incoming customer phone numbers, provisions
    persistent order sessions, and dynamically updates Supabase carts.
    """
    try:
        payload = await request.json()
        logger.info(f"📥 RAW PAYLOAD RECEIVED: {payload}")
        
        if "entry" in payload and payload["entry"]:
            entry_obj = payload["entry"][0]
            if "changes" in entry_obj and entry_obj["changes"]:
                value = entry_obj["changes"][0].get("value", {})
                
                if "messages" in value and value["messages"]:
                    msg_obj = value["messages"][0]
                    sender_phone = msg_obj.get("from")
                    
                    if not sender_phone:
                        return {"status": "ignored"}
                        
                    # Provision session states instantly[cite: 1]
                    session_id = ensure_active_cart_session(db, phone_number=sender_phone)
                    
                    # MAPPING TRAFFIC ROUTE A: INBOUND TEXT TRIGGERS
                    if msg_obj.get("type") == "text":
                        user_text = msg_obj["text"].get("body", "").strip().lower()
                        
                        if user_text in ["menu", "hi", "hello", "bhai", "add more items"]:
                            await send_interactive_menu(sender_phone)
                        elif user_text in ["checkout", "view cart", "summary"]:
                            await send_order_summary(sender_phone, session_id, db)
                            
                    # MAPPING TRAFFIC ROUTE B: LIST SELECTIONS / INTERACTIVE BUTTONS
                    elif msg_obj.get("type") == "interactive":
                        interactive_obj = msg_obj.get("interactive", {})
                        
                        # Handle drop-down selection rows[cite: 1]
                        if interactive_obj.get("type") == "list_reply":
                            chosen_id = interactive_obj.get("list_reply", {}).get("id")
                            
                            if chosen_id.startswith("cat_"):
                                await send_branch_skus(sender_phone, branch_code="JED_AZIZIYAH", category_id=chosen_id, db=db)
                            elif chosen_id.startswith("sku_"):
                                sku_uuid = chosen_id.replace("sku_", "")
                                add_item_to_database_cart(db, session_id=session_id, sku_id=sku_uuid)
                                await send_post_item_options(sender_phone, sku_uuid, db)
                                
                        # Handle structural quick reply click responses[cite: 1]
                        elif interactive_obj.get("type") == "button_reply":
                            button_id = interactive_obj.get("button_reply", {}).get("id")
                            logger.info(f"🔘 BUTTON CLICK DETECTED: {button_id}")
                            
                            if button_id == "btn_browse_more":
                                await send_interactive_menu(sender_phone)
                            elif button_id == "btn_summary_view":
                                logger.info(f"📋 Triggering relational summary display for session: {session_id}")
                                await send_order_summary(sender_phone, session_id, db)
                            
        return {"status": "processed"}
    except Exception as e:
        logger.error(f"💥 WEBHOOK RUNTIME EXCEPTION: {str(e)}")
        return {"status": "error"}

# =====================================================================
# PERSISTENT DATABASE SESSION STATE ENGINES (SUPABASE TRANS-POOL)
# =====================================================================

def ensure_active_cart_session(db: Session, phone_number: str) -> str:
    session_query = text("SELECT id FROM whatsapp_sessions WHERE customer_phone = :phone AND is_active = true LIMIT 1")
    session_row = db.execute(session_query, {"phone": phone_number}).fetchone()
    if session_row:
        return str(session_row[0])
    
    new_id = str(uuid.uuid4())
    insert_query = text("INSERT INTO whatsapp_sessions (id, customer_phone, is_active) VALUES (:id, :phone, true)")
    db.execute(insert_query, {"id": new_id, "phone": phone_number})
    db.commit()
    return new_id

def add_item_to_database_cart(db: Session, session_id: str, sku_id: str):
    check_query = text("SELECT id, quantity FROM cart_items WHERE session_id = :session_id AND sku_id = :sku_id")
    row = db.execute(check_query, {"session_id": session_id, "sku_id": sku_id}).fetchone()
    if row:
        db.execute(text("UPDATE cart_items SET quantity = :qty WHERE id = :id"), {"qty": row[1] + 1, "id": row[0]})
    else:
        db.execute(text("INSERT INTO cart_items (id, session_id, sku_id, quantity) VALUES (:id, :session_id, :sku_id, 1)"),
                   {"id": str(uuid.uuid4()), "session_id": session_id, "sku_id": sku_id})
    db.commit()

# =====================================================================
# INTERACTIVE OUTBOUND MESSAGING PIPELINE & DISPATCHERS
# =====================================================================

async def send_interactive_menu(recipient_phone: str):
    url = f"https://graph.facebook.com/v25.0/{PHONE_NUMBER_ID}/messages"
    payload = {
        "messaging_product": "whatsapp", "recipient_type": "individual", "to": recipient_phone,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "header": {"type": "text", "text": "Golden Snacks & BBQ 🍔"},
            "body": {"text": "Welcome to our digital kitchen! Please select a food category below to view our available items:"},
            "footer": {"text": "Powered by Haniya Global Network"},
            "action": {
                "button": "View Categories",
                "sections": [{
                    "title": "Our Full Menu",
                    "rows": [
                        {"id": "cat_biryani", "title": "Biryani Specials", "description": "Authentic chicken & mutton biryani"},
                        {"id": "cat_pizza", "title": "Pizza Options", "description": "Freshly baked pan pizzas"},
                        {"id": "cat_fastfood", "title": "Fast Food Favorites", "description": "Zinger burgers & club sandwiches"},
                        {"id": "cat_bbq", "title": "BBQ Rolls", "description": "Chicken boti & beef seekh rolls"}
                    ]
                }]
            }
        }
    }
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}
    async with httpx.AsyncClient() as client:
        await client.post(url, json=payload, headers=headers)

async def send_branch_skus(recipient_phone: str, branch_code: str, category_id: str, db: Session):
    raw_menu = MenuService.get_live_menu_for_whatsapp(db, branch_code=branch_code)
    prefix_map = {"cat_biryani": "RIC", "cat_pizza": "PZ", "cat_fastfood": "BGR", "cat_bbq": "GRV"}
    target_prefix = prefix_map.get(category_id, "RIC")
    filtered_items = [item for item in raw_menu if item["sku_code"].startswith(target_prefix)]
    
    if not filtered_items:
        text_payload = {
            "messaging_product": "whatsapp", "to": recipient_phone, "type": "text",
            "text": {"body": "Our kitchen has run out of items in this category! Please select another option."}
        }
    else:
        rows = []
        for item in filtered_items:
            rows.append({
                "id": f"sku_{item['sku_id']}", "title": f"{item['name_en']}", "description": f"{item['portion_size']} ➔ {item['price']} SAR"
            })
        text_payload = {
            "messaging_product": "whatsapp", "recipient_type": "individual", "to": recipient_phone,
            "type": "interactive",
            "interactive": {
                "type": "list",
                "header": {"type": "text", "text": "Select Your Order 🍽️"},
                "body": {"text": "Tap below to view available sizes and add choices straight into your cart:"},
                "footer": {"text": "Prices include local VAT requirements"},
                "action": {"button": "View Available Items", "sections": [{"title": "Freshly Prepared Today", "rows": rows[:10]}]}
            }
        }
    url = f"https://graph.facebook.com/v25.0/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}
    async with httpx.AsyncClient() as client:
        await client.post(url, json=text_payload, headers=headers)

async def send_post_item_options(recipient_phone: str, sku_id: str, db: Session):
    item_query = text("SELECT name_en FROM products WHERE id = :sku_id LIMIT 1")
    item_row = db.execute(item_query, {"sku_id": sku_id}).fetchone()
    item_name = item_row[0] if item_row else "Item"

    url = f"https://graph.facebook.com/v25.0/{PHONE_NUMBER_ID}/messages"
    payload = {
        "messaging_product": "whatsapp", "recipient_type": "individual", "to": recipient_phone,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": f"✅ Added *{item_name}* directly to your active order selection card. What would you like to do next?"},
            "action": {
                "buttons": [
                    {"type": "reply", "reply": {"id": "btn_browse_more", "title": "➕ Add More Items"}},
                    {"type": "reply", "reply": {"id": "btn_summary_view", "title": "📋 View Summary & Pay"}}
                ]
            }
        }
    }
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}
    async with httpx.AsyncClient() as client:
        await client.post(url, json=payload, headers=headers)

async def send_order_summary(recipient_phone: str, session_id: str, db: Session):
    """Calculates active item aggregation rows using relational product snapshots."""
    summary_query = text("""
        SELECT p.name_en, c.quantity, p.price, (c.quantity * p.price) as line_total
        FROM cart_items c
        JOIN products p ON c.sku_id = p.id
        WHERE c.session_id = :session_id
    """)
    basket_rows = db.execute(summary_query, {"session_id": session_id}).fetchall()
    
    if not basket_rows:
        message_text = "🛒 *Your shopping basket is currently empty!* Type *'menu'* to explore our kitchen categories."
    else:
        card_lines = ["🛒 *GOLDEN SNACKS ORDER SUMMARY*\n" + "─"*15]
        subtotal = 0.0
        
        for row in basket_rows:
            name, qty, price, total = row
            card_lines.append(f"• *{name}*\n  `{qty} x {price:.2f} SAR` ➔ *{total:.2f} SAR*")
            subtotal += float(total)
            
        vat_amount = subtotal * 0.15
        grand_total = subtotal + vat_amount
        
        card_lines.append("─"*15)
        card_lines.append(f"🧾 *Subtotal:* {subtotal:.2f} SAR")
        card_lines.append(f"💵 *VAT (15%):* {vat_amount:.2f} SAR")
        card_lines.append(f"💰 *Grand Total:* *{grand_total:.2f} SAR*")
        card_lines.append("\nTo finalize this dispatch, type *'checkout'*, or type *'menu'* to add more items.")
        message_text = "\n".join(card_lines)

    url = f"https://graph.facebook.com/v25.0/{PHONE_NUMBER_ID}/messages"
    payload = {
        "messaging_product": "whatsapp", "to": recipient_phone, "type": "text", "text": {"body": message_text}
    }
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}
    async with httpx.AsyncClient() as client:
        await client.post(url, json=payload, headers=headers)

@app.get("/api/menu")
def fetch_live_branch_menu(branch_code: str = Query(...), channel: str = Query("WHATSAPP"), db: Session = Depends(get_db)):
    try:
        menu = MenuService.get_live_menu_for_whatsapp(db, branch_code=branch_code, channel=channel)
        return {"branch_code": branch_code, "channel": channel, "total_items": len(menu), "items": menu}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))