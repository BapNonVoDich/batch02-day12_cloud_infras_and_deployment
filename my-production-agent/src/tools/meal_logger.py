import json
from datetime import datetime
from tools.db_utils import load_users, save_users, load_meals

def log_meal(user_id: str, meal_type: str, dish_name: str, portion_size: float = 1.0) -> str:
    """
    Logs a meal with portion size for a user. Updates MockUser.json.
    """
    try:
        users = load_users()
        user = next((u for u in users if u["id"] == user_id), None)
        if not user:
            return json.dumps({"error": f"Không tìm thấy người dùng có ID '{user_id}'"}, ensure_ascii=False)

        meals = load_meals()
        dish = next((m for m in meals if m["name"].lower() == dish_name.strip().lower()), None)
        
        if not dish:
            matches = [m for m in meals if dish_name.strip().lower() in m["name"].lower()]
            if matches:
                dish = matches[0]
                
        if not dish:
            return json.dumps({"error": f"Không thể ghi nhận: Không tìm thấy món ăn '{dish_name}' trong cơ sở dữ liệu."}, ensure_ascii=False)

        logged_meal = {
            "meal_type": meal_type,
            "dish_name": dish["name"],
            "portion_size": portion_size,
            "calories_kcal": int(dish["calories_kcal"] * portion_size),
            "protein_g": int(dish["protein_g"] * portion_size),
            "carbohydrates_g": int(dish["carbohydrates_g"] * portion_size),
            "fat_g": int(dish["fat_g"] * portion_size),
            "timestamp": datetime.now().isoformat()
        }

        if "logged_meals" not in user:
            user["logged_meals"] = []
        user["logged_meals"].append(logged_meal)
        
        save_users(users)
        
        return json.dumps({
            "success": True,
            "logged_meal": logged_meal,
            "message": f"Ghi nhận thành công: {meal_type} - {dish['name']} (Portion: {portion_size}) nạp {logged_meal['calories_kcal']} kcal."
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"Lỗi ghi nhận bữa ăn: {str(e)}"}, ensure_ascii=False)
