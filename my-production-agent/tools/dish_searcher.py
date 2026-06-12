import json
from tools.db_utils import load_meals

def search_dish_nutrition(dish_name: str) -> str:
    """
    Searches the nutrition database for matching dishes.
    """
    try:
        meals = load_meals()
        query = dish_name.strip().lower()
        
        matches = []
        for m in meals:
            if query in m["name"].lower():
                matches.append(m)
                
        if not matches:
            return json.dumps({"message": f"Không tìm thấy thông tin dinh dưỡng cho món '{dish_name}' in database."}, ensure_ascii=False)
            
        return json.dumps(matches, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"Lỗi tra cứu món ăn: {str(e)}"}, ensure_ascii=False)
