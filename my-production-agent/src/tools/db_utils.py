import os
import json
from typing import Dict, Any, List

# Calculate paths relative to workspace root
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEALS_FILE = os.path.join(BASE_DIR, "mock-data", "MealMockData.Json")
USERS_FILE = os.path.join(BASE_DIR, "mock-data", "MockUser.json")

def load_meals() -> List[Dict[str, Any]]:
    try:
        if os.path.exists(MEALS_FILE):
            with open(MEALS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading meals: {e}")
    return []

def get_user_with_targets(user: Dict[str, Any]) -> Dict[str, Any]:
    if not user:
        return user
    # If all targets are already present, return as is
    if (user.get("target_calories") is not None and 
        user.get("target_protein_g") is not None and 
        user.get("target_carbs_g") is not None and 
        user.get("target_fat_g") is not None):
        return user
    
    # Calculate dynamically
    try:
        weight = float(user.get("weight_kg", 60.0))
        height = float(user.get("height_cm", 160.0))
        age = int(user.get("age", 25))
        gender = user.get("gender", "Nam")
        activity_level = user.get("activity_level", "sedentary")
        goal = user.get("goal", "build_muscle")
        
        gender_clean = gender.strip().lower()
        if gender_clean in ['nam', 'male', 'm']:
            bmr = 10 * weight + 6.25 * height - 5 * age + 5
        else:
            bmr = 10 * weight + 6.25 * height - 5 * age - 161

        multipliers = {
            "sedentary": 1.2,
            "light": 1.375,
            "moderate": 1.55,
            "active": 1.725,
            "very_active": 1.9
        }
        multiplier = multipliers.get(activity_level.strip().lower(), 1.2)
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
        
        user["target_calories"] = int(target_calories)
        user["target_protein_g"] = protein_g
        user["target_carbs_g"] = carbs_g
        user["target_fat_g"] = fat_g
    except Exception as e:
        print(f"Error dynamically calculating user targets: {e}")
    return user

def load_users() -> List[Dict[str, Any]]:
    try:
        if os.path.exists(USERS_FILE):
            with open(USERS_FILE, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    users = json.loads(content)
                    return [get_user_with_targets(u) for u in users]
    except Exception as e:
        print(f"Error loading users: {e}")
    return []

def save_users(users: List[Dict[str, Any]]):
    try:
        users_to_save = []
        for u in users:
            u_copy = u.copy()
            # Remove targets to keep the mock file clean of pre-computed targets
            for target_key in ["target_calories", "target_protein_g", "target_carbs_g", "target_fat_g"]:
                u_copy.pop(target_key, None)
            users_to_save.append(u_copy)
            
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(users_to_save, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving users: {e}")

CHAT_HISTORY_FILE = os.path.join(BASE_DIR, "mock-data", "ChatHistory.json")

def load_chat_history(user_id: str) -> List[Dict[str, Any]]:
    try:
        if os.path.exists(CHAT_HISTORY_FILE):
            with open(CHAT_HISTORY_FILE, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    history = json.loads(content)
                    return history.get(user_id, [])
    except Exception as e:
        print(f"Error loading chat history: {e}")
    return []

def save_chat_history(user_id: str, messages: List[Dict[str, Any]]):
    try:
        history = {}
        if os.path.exists(CHAT_HISTORY_FILE):
            with open(CHAT_HISTORY_FILE, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    history = json.loads(content)
        
        history[user_id] = messages
        
        with open(CHAT_HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving chat history: {e}")

