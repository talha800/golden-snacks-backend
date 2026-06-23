import logging
import httpx
import uuid
from fastapi import FastAPI, Depends, Query, HTTPException, status, Request, Response
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
    version="2.6.0",
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

# =====================================================================
# META WHATSAPP WEBHOOK ROUTING GATEWAY (STATEFUL ROUTER)
# =====================================================================

@app.post("/webhooks/whatsapp")
@app.post("/webhook")
async def handle_whatsapp_traffic(request: Request, db: Session = Depends(get_db)):
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
                        
                    # Central Database Session Provisioning
                    session_id = ensure_active_cart_session(db, phone_number=sender_phone)
                    
                    # TRAFFIC ROUTE A: INBOUND TEXT COMMAND ENGINE
                    if msg_obj.get("type") == "text":
                        user_text = msg_obj["text"].get("body", "").strip().lower()
                        
                        if user_text in ["menu", "hi", "hello", "bhai", "add more items"]:
                            await send_interactive_menu(sender_phone)
                        elif user_text in ["view cart", "summary", "cart"]:
                            await send_order_summary(sender_phone, session_id, db)
                        elif user_text in ["reset", "start over", "clear"]:
                            clear_active_database_cart(db, session_id=session_id)
                            await send_main_options_menu(sender_phone, "🗑️ *Your cart has been completely reset!* Your old selections were deleted.")
                        elif user_text in ["checkout", "pay"]:
                            await execute_cart_checkout(sender_phone, session_id, db)
                            
                    # MAPPING TRAFFIC ROUTE B: LIST SELECTIONS / INTERACTIVE BUTTONS
                    elif msg_obj.get("type") == "interactive":
                        interactive_obj = msg_obj.get("interactive", {})
                        
                        # Handle Drop-Down Sub-Menus
                        if interactive_obj.get("type") == "list_reply":
                            chosen_id = interactive_obj.get("list_reply", {}).get("id")
                            
                            if chosen_id.startswith("cat_"):
                                await send_branch_skus(sender_phone, branch_code="JED_AZIZIYAH", category_id=chosen_id, db=db)
                            elif chosen_id.startswith("sku_"):
                                sku_uuid = chosen_id.replace("sku_", "")
                                logger.info(f"💾 STATE TRANSACTION: Writing SKU {sku_uuid} to Session {session_id}")
                                add_item_to_database_cart(db, session_id=session_id, sku_id=sku_uuid)
                                await send_post_item_options(sender_phone, sku_uuid, db)
                                
                        # Handle Quick-Reply Actions
                        elif interactive_obj.get("type") == "button_reply":
                            button_id = interactive_obj.get("button_reply", {}).get("id")
                            logger.info(f"🔘 BUTTON CLICK DETECTED: {button_id}")
                            
                            if button_id == "btn_browse_more":
                                await send_interactive_menu(sender_phone)
                            elif button_id == "btn_summary_view":
                                await send_order_summary(sender_phone, session_id, db)
                            elif button_id == "btn_reset_cart":
                                clear_active_database_cart(db, session_id=session_id)
                                await send_main_options_menu(sender_phone, "🗑️ Your active selections have been cleared.")
                            elif button_id == "btn_checkout_final":
                                await execute_cart_checkout(sender_phone, session_id, db)
                            elif button_id == "btn_main_menu":
                                await send_interactive_menu(sender_phone)
                            
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

def clear_active_database_cart(db: Session, session_id: str):
    delete_query = text("DELETE FROM cart_items WHERE session_id = :session_id")
    db.execute(delete_query, {"session_id": session_id})
    db.commit()

async def execute_cart_checkout(recipient_phone: str, session_id: str, db: Session):
    """Leverages relational native SQL aggregates directly on your Supabase tables."""
    checkout_query = text("""
        SELECT p.name_en, p.portion_size, c.quantity, p.price, (c.quantity * p.price) as line_total
        FROM cart_items c
        JOIN products p ON c.sku_id = p.id
        WHERE c.session_id = :session_id
    """)
    cart_rows = db.execute(checkout_query, {"session_id": session_id}).fetchall()
    
    if not cart_rows:
        await send_main_options_menu(recipient_phone, "🛒 Your cart is currently empty!")
        return

    card_lines = ["🏁 *ORDER CONFIRMED & SENT TO KITCHEN!*\n" + "═"*20]
    total_inclusive = 0.0
    
    for row in cart_rows:
        name, portion, qty, price, total = row
        card_lines.append(f"• *{name} ({portion})* x{qty} ➔ *{total:.2f} SAR*")
        total_inclusive += float(total)

    # Reverse VAT Algebra Calculations
    subtotal_exclusive = total_inclusive / 1.15
    vat_amount = total_inclusive - subtotal_exclusive
    
    card_lines.append("═"*20)
    card_lines.append(f"🧾 *Price (Excluding VAT):* {subtotal_exclusive:.2f} SAR")
    card_lines.append(f"💵 *VAT Amount (15%):* {vat_amount:.2f} SAR")
    card_lines.append(f"💰 *Final Price (Inc. VAT):* *{total_inclusive:.2f} SAR*")
    card_lines.append("\nThank you! Your order is printing at our terminal. Tap below if you want to start a brand new order sequence.")
    
    close_query = text("UPDATE whatsapp_sessions SET is_active = false WHERE id = :session_id")
    db.execute(close_query, {"session_id": session_id})
    db.commit()
    
    await send_post_checkout_options(recipient_phone, "\n".join(card_lines))

# =====================================================================
# INTERACTIVE OUTBOUND MESSAGING DISPATCHERS
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
                        {"id": "cat_fastfood", "title": "Fast Food & Fries", "description": "Zinger burgers, club sandwiches & crispy fries"},
                        {"id": "cat_bbq", "title": "BBQ Specials & Rolls", "description": "Chicken boti, tikka, & beef seekh rolls"}
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
    
    prefix_map = {
        "cat_biryani": ["RIC"],
        "cat_pizza": ["PZ"],
        "cat_fastfood": ["BGR", "FF", "ZNG", "SND"], 
        "cat_bbq": ["GRV", "BBQ", "ROL", "BOT"]       
    }
    
    target_prefixes = prefix_map.get(category_id, ["RIC"])
    filtered_items = [item for item in raw_menu if any(item["sku_code"].startswith(pref) for pref in target_prefixes)]
    
    if not filtered_items:
        await send_main_options_menu(recipient_phone, "⚠️ Our kitchen has run out of items in this category for this shift!")
        return

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
    # 🧼 HARDENED FIX: Dropped custom app trace header fields to ensure clean native message routing parameters
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}
    async with httpx.AsyncClient() as client:
        await client.post(url, json=text_payload, headers=headers)

async def send_post_item_options(recipient_phone: str, sku_id: str, db: Session):
    master_menu = MenuService.get_live_menu_for_whatsapp(db, branch_code="JED_AZIZIYAH")
    menu_dict = {str(item["sku_id"]): item for item in master_menu}
    
    sku_uuid_str = str(sku_id)
    item_desc = f"{menu_dict[sku_uuid_str]['name_en']} ({menu_dict[sku_uuid_str]['portion_size']})" if sku_uuid_str in menu_dict else "Item"

    url = f"https://graph.facebook.com/v25.0/{PHONE_NUMBER_ID}/messages"
    payload = {
        "messaging_product": "whatsapp", "recipient_type": "individual", "to": recipient_phone,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": f"✅ Added *{item_desc}* directly to your active cart selection card. What would you like to do next?"},
            "action": {
                "buttons": [
                    {"type": "reply", "reply": {"id": "btn_browse_more", "title": "➕ Add More Items"}},
                    {"type": "reply", "reply": {"id": "btn_summary_view", "title": "📋 View Summary"}},
                    {"type": "reply", "reply": {"id": "btn_reset_cart", "title": "🗑️ Start Over"}}
                ]
            }
        }
    }
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}
    async with httpx.AsyncClient() as client:
        await client.post(url, json=payload, headers=headers)

async def send_order_summary(recipient_phone: str, session_id: str, db: Session):
    cart_query = text("SELECT sku_id, quantity FROM cart_items WHERE session_id = :session_id")
    cart_rows = db.execute(cart_query, {"session_id": session_id}).fetchall()
    
    if not cart_rows:
        await send_main_options_menu(recipient_phone, "🛒 Your shopping basket is currently empty!")
        return

    master_menu = MenuService.get_live_menu_for_whatsapp(db, branch_code="JED_AZIZIYAH")
    menu_dict = {str(item["sku_id"]): item for item in master_menu}
    
    card_lines = ["🛒 *GOLDEN SNACKS ORDER SUMMARY*\n" + "─"*15]
    total_inclusive = 0.0
    
    for row in cart_rows:
        sku_uuid_str = str(row[0])
        qty = row[1]
        
        if sku_uuid_str in menu_dict:
            item_data = menu_dict[sku_uuid_str]
            name = f"{item_data['name_en']} ({item_data['portion_size']})"
            price = float(item_data["price"])
            total = qty * price
            
            card_lines.append(f"• *{name}*\n  `{qty} x {price:.2f} SAR` ➔ *{total:.2f} SAR*")
            total_inclusive += total
    
    # Reverse Tax Calculation Matrix
    subtotal_exclusive = total_inclusive / 1.15
    vat_amount = total_inclusive - subtotal_exclusive
    
    card_lines.append("─"*15)
    card_lines.append(f"🧾 *Subtotal (Excl. VAT):* {subtotal_exclusive:.2f} SAR")
    card_lines.append(f"💵 *VAT (15%):* {vat_amount:.2f} SAR")
    card_lines.append(f"💰 *Grand Total:* *{total_inclusive:.2f} SAR*")
    
    url = f"https://graph.facebook.com/v25.0/{PHONE_NUMBER_ID}/messages"
    payload = {
        "messaging_product": "whatsapp", "recipient_type": "individual", "to": recipient_phone,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": "\n".join(card_lines)},
            "action": {
                "buttons": [
                    {"type": "reply", "reply": {"id": "btn_checkout_final", "title": "🏁 Complete Order"}},
                    {"type": "reply", "reply": {"id": "btn_browse_more", "title": "➕ Add More Items"}},
                    {"type": "reply", "reply": {"id": "btn_reset_cart", "title": "🗑️ Reset Order"}}
                ]
            }
        }
    }
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}
    async with httpx.AsyncClient() as client:
        await client.post(url, json=payload, headers=headers)

async def send_main_options_menu(recipient_phone: str, message_header: str):
    url = f"https://graph.facebook.com/v25.0/{PHONE_NUMBER_ID}/messages"
    payload = {
        "messaging_product": "whatsapp", "recipient_type": "individual", "to": recipient_phone,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": f"{message_header}\n\nPlease click below to access the kitchen catalog:"},
            "action": {
                "buttons": [{"type": "reply", "reply": {"id": "btn_main_menu", "title": "🍔 Open Main Menu"}}]
            }
        }
    }
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}
    async with httpx.AsyncClient() as client:
        await client.post(url, json=payload, headers=headers)

async def send_post_checkout_options(recipient_phone: str, invoice_body: str):
    url = f"https://graph.facebook.com/v25.0/{PHONE_NUMBER_ID}/messages"
    payload = {
        "messaging_product": "whatsapp", "recipient_type": "individual", "to": recipient_phone,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": invoice_body},
            "action": {
                "buttons": [{"type": "reply", "reply": {"id": "btn_main_menu", "title": "🔄 Order Again"}}]
            }
        }
    }
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}
    async with httpx.AsyncClient() as client:
        await client.post(url, json=payload, headers=headers)