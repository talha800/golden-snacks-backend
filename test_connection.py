import sys
from app.database import SessionLocal
from app.services.menu_service import MenuService

def test_menu_engine():
    print("Testing Menu Service engine integration...")
    db = SessionLocal()
    try:
        # Simulate an incoming query from the Al-Aziziyah branch in Jeddah
        menu = MenuService.get_live_menu_for_whatsapp(db, branch_code="JED_AZIZIYAH")
        
        print("\n🚀 [SUCCESS] Menu Engine Service Executed Cleanly!")
        print(f"Total Available Items Found: {len(menu)}")
        
        for item in menu:
            print(f" - [{item['sku_code']}] {item['name_en']} ({item['portion_size']}) ➔ {item['price']} SAR")
            
        sys.exit(0)
    except Exception as e:
        print("\n❌ [FAILURE] Menu Engine broken or mapping misaligned.")
        print(f"Error Log: {str(e)}")
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    test_menu_engine()