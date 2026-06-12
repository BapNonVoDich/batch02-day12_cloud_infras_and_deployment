import json

def calculate_tdee(weight_kg: float, height_cm: float, age: int, gender: str, activity_level: str, goal: str) -> str:
    """
    Calculates BMR, TDEE, and daily target calories/macros based on user details.
    
    Arguments:
    - weight_kg (float): Weight in kilograms.
    - height_cm (float): Height in centimeters.
    - age (int): Age in years.
    - gender (str): Gender ('Nam' or 'Nữ' / 'Male' or 'Female').
    - activity_level (str): 'sedentary', 'light', 'moderate', 'active', 'very_active'.
    - goal (str): 'lose_weight' (giảm cân), 'gain_weight' (tăng cân), 'build_muscle' (tăng cơ).
    """
    try:
        gender_clean = gender.strip().lower()
        if gender_clean in ['nam', 'male', 'm']:
            bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age + 5
        else:
            bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age - 161

        multipliers = {
            "sedentary": 1.2,
            "light": 1.375,
            "moderate": 1.55,
            "active": 1.725,
            "very_active": 1.9
        }
        
        act_lvl = activity_level.strip().lower()
        multiplier = multipliers.get(act_lvl, 1.2)
        tdee = bmr * multiplier

        if goal == "lose_weight":
            target_calories = tdee - 500
            min_calories = 1500 if gender_clean in ['nam', 'male', 'm'] else 1200
            target_calories = max(target_calories, min_calories)
            p_pct, c_pct, f_pct = 0.30, 0.40, 0.30
        elif goal == "gain_weight":
            target_calories = tdee + 400
            p_pct, c_pct, f_pct = 0.20, 0.55, 0.25
        elif goal == "build_muscle":
            target_calories = tdee + 200
            p_pct, c_pct, f_pct = 0.35, 0.40, 0.25
        else:
            target_calories = tdee
            p_pct, c_pct, f_pct = 0.20, 0.50, 0.30

        protein_g = int((target_calories * p_pct) / 4)
        carbs_g = int((target_calories * c_pct) / 4)
        fat_g = int((target_calories * f_pct) / 9)
        target_calories = int(target_calories)
        tdee = int(tdee)
        bmr = int(bmr)

        result = {
            "bmr": bmr,
            "tdee": tdee,
            "target_calories": target_calories,
            "target_protein_g": protein_g,
            "target_carbs_g": carbs_g,
            "target_fat_g": fat_g,
            "message": f"Tính toán thành công! Nhu cầu năng lượng hàng ngày (TDEE): {tdee} kcal. Để đạt mục tiêu '{goal}', bạn cần nạp {target_calories} kcal mỗi ngày (Protein: {protein_g}g, Carbs: {carbs_g}g, Fat: {fat_g}g)."
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"Lỗi tính toán TDEE: {str(e)}"}, ensure_ascii=False)
