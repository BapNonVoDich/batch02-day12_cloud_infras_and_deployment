import json
import json
import json
from tools.db_utils import load_meals

def suggest_alternative(dish_name: str, target_macro: str) -> str:
    """
    Suggests alternative dishes that have lower value for a macro or higher protein.
    """
    try:
        meals = load_meals()
        dish_name_clean = dish_name.strip().lower()
        original_dish = next((m for m in meals if m["name"].lower() == dish_name_clean), None)
        
        if not original_dish:
            matches = [m for m in meals if dish_name_clean in m["name"].lower()]
            if matches:
                original_dish = matches[0]

        if not original_dish:
            return json.dumps({"error": f"Không tìm thấy món ăn '{dish_name}' trong dữ liệu để so sánh."}, ensure_ascii=False)

        suggestions = []
        for m in meals:
            if m["id"] == original_dish["id"]:
                continue
            
            if target_macro == "fat_g":
                if m["fat_g"] < original_dish["fat_g"] * 0.7:
                    suggestions.append(m)
            elif target_macro == "calories_kcal":
                if m["calories_kcal"] < original_dish["calories_kcal"] * 0.75:
                    suggestions.append(m)
            elif target_macro == "carbohydrates_g":
                if m["carbohydrates_g"] < original_dish["carbohydrates_g"] * 0.7:
                    suggestions.append(m)
            elif target_macro == "protein_g":
                if m["protein_g"] > original_dish["protein_g"]:
                    suggestions.append(m)
            else:
                if m["calories_kcal"] < original_dish["calories_kcal"]:
                    suggestions.append(m)

        if target_macro in ["fat_g", "calories_kcal", "carbohydrates_g"]:
            suggestions = sorted(suggestions, key=lambda x: x[target_macro])
        elif target_macro == "protein_g":
            suggestions = sorted(suggestions, key=lambda x: x[target_macro], reverse=True)

        top_suggestions = suggestions[:5]
        
        return json.dumps({
            "original_dish": original_dish,
            "target_macro": target_macro,
            "suggestions": top_suggestions,
            "message": f"Dưới đây là các món ăn thay thế cho '{original_dish['name']}' giúp tối ưu '{target_macro}'."
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"Lỗi đề xuất món ăn thay thế: {str(e)}"}, ensure_ascii=False)
