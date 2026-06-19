from datetime import datetime
import zoneinfo
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.models.schema import Branch

class MenuService:
    @staticmethod
    def get_live_menu_for_whatsapp(db: Session, branch_code: str, channel: str = "WHATSAPP") -> list:
        """
        Queries the database to fetch only the menu items that are active right now,
        based on the branch schedule and operational shifts.
        """
        # 1. Resolve target Branch UUID using the indexed business branch_code
        branch = db.query(Branch).filter(Branch.branch_code == branch_code, Branch.is_active == True).first()
        if not branch:
            return []

        # 2. Compute current timestamp adjusted explicitly for Saudi Arabia timezone
        ksa_tz = zoneinfo.ZoneInfo("Asia/Riyadh")
        now_ksa = datetime.now(ksa_tz)

        # 3. Call the optimized stored database function we created in Phase 2
        query = text("""
            SELECT sku_id, sku_code, product_name_en, product_name_ar, portion_size_en, current_price
            FROM get_available_menu(:branch_id, :channel, :target_timestamp);
        """)

        result = db.execute(query, {
            "branch_id": branch.id,
            "channel": channel,
            "target_timestamp": now_ksa
        }).fetchall()

        # 4. Map the results into a clean, structured list of dictionaries
        menu_items = []
        for row in result:
            menu_items.append({
                "sku_id": str(row.sku_id),
                "sku_code": row.sku_code,
                "name_en": row.product_name_en,
                "name_ar": row.product_name_ar,
                "portion_size": row.portion_size_en,
                "price": float(row.current_price)
            })

        return menu_items