import json
from tools.db_utils import load_users

def get_daily_summary(user_id: str) -> str:
    """
    Returns the user's logged calories/macros vs daily targets.
    """
    try:
        users = load_users()
        user = next((u for u in users if u["id"] == user_id), None)
        if not user:
            return json.dumps({"error": f"Không tìm thấy người dùng có ID '{user_id}'"}, ensure_ascii=False)

        logged = user.get("logged_meals", [])
        total_cal = sum(m["calories_kcal"] for m in logged)
        total_protein = sum(m["protein_g"] for m in logged)
        total_carbs = sum(m["carbohydrates_g"] for m in logged)
        total_fat = sum(m["fat_g"] for m in logged)

        summary = {
            "user_id": user_id,
            "name": user["name"],
            "goal": user["goal"],
            "targets": {
                "calories": user.get("target_calories", 2000),
                "protein_g": user.get("target_protein_g", 120),
                "carbohydrates_g": user.get("target_carbs_g", 220),
                "fat_g": user.get("target_fat_g", 65)
            },
            "consumed": {
                "calories": total_cal,
                "protein_g": total_protein,
                "carbohydrates_g": total_carbs,
                "fat_g": total_fat
            },
            "remaining": {
                "calories": max(0, user.get("target_calories", 2000) - total_cal),
                "protein_g": max(0, user.get("target_protein_g", 120) - total_protein),
                "carbohydrates_g": max(0, user.get("target_carbs_g", 220) - total_carbs),
                "fat_g": max(0, user.get("target_fat_g", 65) - total_fat)
            },
            "logged_meals": logged
        }
        return json.dumps(summary, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"Lỗi tải thông tin dinh dưỡng: {str(e)}"}, ensure_ascii=False)
