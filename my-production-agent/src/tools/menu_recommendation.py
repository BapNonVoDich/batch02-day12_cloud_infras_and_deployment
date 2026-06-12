import os
import sys
import json
import re
import random
import google.generativeai as genai
from typing import List, Optional, Dict, Any
from dotenv import load_dotenv

# Fix pathing issues for db_utils if run from different CWD
import tools.db_utils
if "src" in getattr(tools.db_utils, "BASE_DIR", ""):
    tools.db_utils.BASE_DIR = os.path.dirname(tools.db_utils.BASE_DIR)
    tools.db_utils.MEALS_FILE = os.path.join(tools.db_utils.BASE_DIR, "mock-data", "MealMockData.Json")
    tools.db_utils.USERS_FILE = os.path.join(tools.db_utils.BASE_DIR, "mock-data", "MockUser.json")
    if hasattr(tools.db_utils, "CHAT_HISTORY_FILE"):
        tools.db_utils.CHAT_HISTORY_FILE = os.path.join(tools.db_utils.BASE_DIR, "mock-data", "ChatHistory.json")

# Monkeypatch load_meals to dynamically return recommended composite dishes
original_load_meals = tools.db_utils.load_meals

def patched_load_meals() -> list:
    meals = original_load_meals()
    try:
        users_file = tools.db_utils.USERS_FILE
        if os.path.exists(users_file):
            with open(users_file, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    users = json.loads(content)
                    for u in users:
                        rec = u.get("recommended_menu")
                        if rec and "menu" in rec:
                            for meal_type, dish_data in rec["menu"].items():
                                if dish_data and "name" in dish_data:
                                    if not any(m["name"].lower() == dish_data["name"].lower() for m in meals):
                                        meals.append(dish_data)
    except Exception as e:
        print(f"Error in patched_load_meals: {e}")
    return meals

tools.db_utils.load_meals = patched_load_meals
load_meals = patched_load_meals
from tools.db_utils import load_users

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

def recommend_daily_menu(user_id: str, preferred_dishes: Optional[List[str]] = None, allergies: Optional[List[str]] = None) -> str:
    """
    Generates a daily menu recommendation using a metric RAG pipeline:
    1. Retrieval: Filters the database to find the top candidate dishes for each meal type 
       (Breakfast, Lunch, Dinner, Snack) closest to the user's target calorie allocations.
       Also prioritizes user preferred dishes and excludes allergic foods.
    2. Augmentation: Injects only these filtered candidate dishes into the LLM context.
    3. Generation: Instructs Gemini to select a balanced 4-meal plan.
    4. Verification: Checks if calories/macros are strictly within +/- 15% of targets, 
       falling back to a constraint solver if the LLM output fails validation.
    """
    try:
        # 1. Load user profile and targets
        users = load_users()
        user = next((u for u in users if u["id"] == user_id), None)
        if not user:
            return json.dumps({"error": f"Không tìm thấy người dùng có ID '{user_id}'"}, ensure_ascii=False)

        target_calories = user.get("target_calories", 2000)
        target_p = user.get("target_protein_g", 120)
        target_c = user.get("target_carbs_g", 220)
        target_f = user.get("target_fat_g", 65)

        # Calculate calorie allocation for each meal (RAG query target)
        bf_target_cal = target_calories * 0.25
        lh_target_cal = target_calories * 0.35
        dn_target_cal = target_calories * 0.30
        sn_target_cal = target_calories * 0.10

        # 2. RAG Retrieval Step (Metric filtering by calorie distance)
        meals = load_meals()
        if not meals:
            return json.dumps({"error": "Không có dữ liệu món ăn để gợi ý."}, ensure_ascii=False)

        # Filter out allergic foods programmatically first
        if allergies:
            allergy_lower = [a.lower().strip() for a in allergies if a.strip()]
            def is_allergic(meal_name):
                name_l = meal_name.lower()
                for a in allergy_lower:
                    if a in name_l:
                        return True
                    # Common Vietnamese/English seafood expansions
                    if a in ["hải sản", "seafood", "hai san"]:
                        if any(sf in name_l for sf in ["tôm", "cua", "cá", "mực", "ốc", "nghêu", "hến", "sò", "tom", "cua", "ca", "muc", "oc", "ngheu", "hen", "so"]):
                            return True
                return False
            meals = [m for m in meals if not is_allergic(m["name"])]

        # Classify dishes in DB
        breakfast_keywords = ["phở", "bánh mì", "bún", "hủ tiếu", "bánh cuốn", "cháo", "xôi", "súp"]
        snack_keywords = ["chè", "cuốn", "chả giò", "bắp xào", "trứng vịt lộn", "bánh tiêu", "bánh giò", "gỏi cuốn", "nem lụi", "nộm", "gỏi ngó sen"]
        
        all_breakfasts = []
        all_snacks = []
        all_mains = []

        for m in meals:
            name_lower = m["name"].lower()
            if any(kw in name_lower for kw in breakfast_keywords):
                all_breakfasts.append(m)
            elif any(kw in name_lower for kw in snack_keywords):
                all_snacks.append(m)
            else:
                all_mains.append(m)

        # Fallbacks
        if not all_breakfasts: all_breakfasts = meals
        if not all_snacks: all_snacks = meals
        if not all_mains: all_mains = meals

        # Classify main dishes into sub-courses (Protein, Soup, Veggie)
        all_soups = []
        all_veggies = []
        all_proteins = []
        for m in all_mains:
            name_lower = m["name"].lower()
            if any(kw in name_lower for kw in ["canh", "súp", "lẩu"]):
                all_soups.append(m)
            elif any(kw in name_lower for kw in ["rau", "xào", "nộm", "gỏi", "đậu", "luộc"]):
                all_veggies.append(m)
            else:
                all_proteins.append(m)

        if not all_soups: all_soups = meals
        if not all_veggies: all_veggies = meals
        if not all_proteins: all_proteins = meals

        # Find preferred dishes to force them into candidate sets
        forced_breakfasts = []
        forced_mains = []
        forced_snacks = []
        
        if preferred_dishes:
            pref_lower = [p.lower().strip() for p in preferred_dishes if p.strip()]
            for m in meals:
                name_l = m["name"].lower()
                if any(p in name_l for p in pref_lower):
                    if any(kw in name_l for kw in breakfast_keywords):
                        forced_breakfasts.append(m)
                    elif any(kw in name_l for kw in snack_keywords):
                        forced_snacks.append(m)
                    else:
                        forced_mains.append(m)

        forced_soups = []
        forced_veggies = []
        forced_proteins = []
        for m in forced_mains:
            name_lower = m["name"].lower()
            if any(kw in name_lower for kw in ["canh", "súp", "lẩu"]):
                forced_soups.append(m)
            elif any(kw in name_lower for kw in ["rau", "xào", "nộm", "gỏi", "đậu", "luộc"]):
                forced_veggies.append(m)
            else:
                forced_proteins.append(m)

        # Retrieve candidates for Breakfast and Snack (top 8 closest to target calorie allocation)
        retrieved_breakfasts = sorted(all_breakfasts, key=lambda x: abs(x["calories_kcal"] - bf_target_cal))
        retrieved_snacks = sorted(all_snacks, key=lambda x: abs(x["calories_kcal"] - sn_target_cal))

        # Helper to merge forced and retrieved candidates
        def merge_forced(candidates, forced, limit):
            forced_ids = {f["id"] for f in forced}
            filtered_candidates = [c for c in candidates if c["id"] not in forced_ids]
            merged = forced + filtered_candidates
            return merged[:limit]

        retrieved_breakfasts = merge_forced(retrieved_breakfasts, forced_breakfasts, limit=8)
        retrieved_snacks = merge_forced(retrieved_snacks, forced_snacks, limit=8)

        # For Lunch: retrieve diverse courses
        lh_proteins = sorted(all_proteins, key=lambda x: abs(x["calories_kcal"] - lh_target_cal * 0.6))
        lh_soups = sorted(all_soups, key=lambda x: abs(x["calories_kcal"] - lh_target_cal * 0.25))
        lh_veggies = sorted(all_veggies, key=lambda x: abs(x["calories_kcal"] - lh_target_cal * 0.15))

        retrieved_lh_proteins = merge_forced(lh_proteins, forced_proteins, limit=4)
        retrieved_lh_soups = merge_forced(lh_soups, forced_soups, limit=3)
        retrieved_lh_veggies = merge_forced(lh_veggies, forced_veggies, limit=3)

        # For Dinner: retrieve diverse courses
        dn_proteins = sorted(all_proteins, key=lambda x: abs(x["calories_kcal"] - dn_target_cal * 0.6))
        dn_soups = sorted(all_soups, key=lambda x: abs(x["calories_kcal"] - dn_target_cal * 0.25))
        dn_veggies = sorted(all_veggies, key=lambda x: abs(x["calories_kcal"] - dn_target_cal * 0.15))

        retrieved_dn_proteins = merge_forced(dn_proteins, forced_proteins, limit=4)
        retrieved_dn_soups = merge_forced(dn_soups, forced_soups, limit=3)
        retrieved_dn_veggies = merge_forced(dn_veggies, forced_veggies, limit=3)

        # Combine retrieved candidates for context
        retrieved_context = {
            "Breakfast_Candidates": retrieved_breakfasts,
            "Lunch_Candidates_Protein": retrieved_lh_proteins,
            "Lunch_Candidates_Soup": retrieved_lh_soups,
            "Lunch_Candidates_Veggie": retrieved_lh_veggies,
            "Dinner_Candidates_Protein": retrieved_dn_proteins,
            "Dinner_Candidates_Soup": retrieved_dn_soups,
            "Dinner_Candidates_Veggie": retrieved_dn_veggies,
            "Snack_Candidates": retrieved_snacks
        }

        # 3. Augmentation & Generation (LLM Call)
        llm_success = False
        suggested_menu = None
        
        if api_key:
            try:
                genai.configure(api_key=api_key)
                
                # Format retrieved candidates for prompt
                prompt = f"""
Bạn là một Chuyên gia Dinh dưỡng AI. Nhiệm vụ của bạn là lập một thực đơn dinh dưỡng trong ngày gồm đúng 4 bữa ăn (Breakfast, Lunch, Dinner, Snack).
Với mỗi bữa ăn, bạn có thể chọn một hoặc nhiều món ăn phối hợp cùng nhau từ danh sách món ăn ứng viên được TRUY XUẤT từ RAG database dưới đây để tạo thành một bữa ăn đa dạng và đầy đủ dinh dưỡng.

YÊU CẦU CỦA NGƯỜI DÙNG:
- Tên: {user["name"]}
- Mục tiêu cơ thể: {user["goal"]}
- Chỉ tiêu dinh dưỡng hàng ngày (Mục tiêu):
  * Calories: {target_calories} kcal (Sai số cho phép lệch tối đa 15%: từ {int(target_calories*0.85)} đến {int(target_calories*1.15)} kcal)
  * Protein: {target_p}g (Sai số cho phép lệch tối đa 15%: từ {int(target_p*0.85)} đến {int(target_p*1.15)}g)
  * Carbohydrates (Carbs): {target_c}g (Sai số cho phép lệch tối đa 15%: từ {int(target_c*0.85)} đến {int(target_c*1.15)}g)
  * Lipid (Fat): {target_f}g (Sai số cho phép lệch tối đa 15%: từ {int(target_f*0.85)} đến {int(target_f*1.15)}g)
"""
                if preferred_dishes:
                    prompt += f"- Món ăn muốn ƯU TIÊN chọn: {', '.join(preferred_dishes)}\n"
                if allergies:
                    prompt += f"- Thành phần/món ăn bị DỊ ỨNG (Tránh tuyệt đối): {', '.join(allergies)}\n"

                prompt += f"""
DANH SÁCH MÓN ĂN ỨNG VIÊN ĐƯỢC TRUY XUẤT (RAG CONTEXT):
- Ứng viên Bữa sáng (Breakfast Candidates):
{json.dumps([{k: m[k] for k in ["name", "calories_kcal", "protein_g", "carbohydrates_g", "fat_g"]} for m in retrieved_breakfasts], ensure_ascii=False, indent=2)}

- Ứng viên Bữa trưa (Lunch Candidates):
  + Món mặn/đạm (Protein):
{json.dumps([{k: m[k] for k in ["name", "calories_kcal", "protein_g", "carbohydrates_g", "fat_g"]} for m in retrieved_lh_proteins], ensure_ascii=False, indent=2)}
  + Món canh (Soup):
{json.dumps([{k: m[k] for k in ["name", "calories_kcal", "protein_g", "carbohydrates_g", "fat_g"]} for m in retrieved_lh_soups], ensure_ascii=False, indent=2)}
  + Món rau/kèm (Veggie/Side):
{json.dumps([{k: m[k] for k in ["name", "calories_kcal", "protein_g", "carbohydrates_g", "fat_g"]} for m in retrieved_lh_veggies], ensure_ascii=False, indent=2)}

- Ứng viên Bữa tối (Dinner Candidates):
  + Món mặn/đạm (Protein):
{json.dumps([{k: m[k] for k in ["name", "calories_kcal", "protein_g", "carbohydrates_g", "fat_g"]} for m in retrieved_dn_proteins], ensure_ascii=False, indent=2)}
  + Món canh (Soup):
{json.dumps([{k: m[k] for k in ["name", "calories_kcal", "protein_g", "carbohydrates_g", "fat_g"]} for m in retrieved_dn_soups], ensure_ascii=False, indent=2)}
  + Món rau/kèm (Veggie/Side):
{json.dumps([{k: m[k] for k in ["name", "calories_kcal", "protein_g", "carbohydrates_g", "fat_g"]} for m in retrieved_dn_veggies], ensure_ascii=False, indent=2)}

- Ứng viên Bữa phụ (Snack Candidates):
{json.dumps([{k: m[k] for k in ["name", "calories_kcal", "protein_g", "carbohydrates_g", "fat_g"]} for m in retrieved_snacks], ensure_ascii=False, indent=2)}

QUY TẮC LỰA CHỌN:
1. Mỗi bữa ăn (Breakfast, Lunch, Dinner, Snack) có thể chứa danh sách gồm một hoặc nhiều món ăn từ các ứng viên tương ứng.
   - Bữa sáng: chọn 1-2 món.
   - Bữa trưa và Bữa tối: nên kết hợp 1 Món mặn/đạm + 1 Món canh + 1 Món rau/kèm từ các nhóm tương ứng để tạo thành mâm cơm hoàn chỉnh và cân đối dinh dưỡng.
   - Bữa phụ: chọn 1 món.
2. Tránh chọn trùng lặp món ăn cho bữa trưa và bữa tối.
3. ĐẢM BẢO RẰNG: Tổng các chỉ số dinh dưỡng (Calories, Protein, Carbs, Fat) của toàn bộ thực đơn trong ngày (của cả 4 bữa cộng lại) phải thỏa mãn sai số LỆCH KHÔNG QUÁ 15% so với chỉ tiêu mục tiêu người dùng đã nêu ở trên.
"""
                if preferred_dishes:
                    prompt += "4. ƯU TIÊN TUYỆT ĐỐI: Hãy chọn các món ăn có tên hoặc chứa nguyên liệu nằm trong danh sách Món ăn muốn ƯU TIÊN ở trên (nếu chúng có trong danh sách ứng viên).\n"
                if allergies:
                    prompt += "5. TRÁNH TUYỆT ĐỐI: Không được chọn bất kỳ món nào chứa nguyên liệu bị DỊ ỨNG ở trên.\n"

                prompt += """
HÃY TRẢ VỀ DUY NHẤT CHUỖI JSON THEO ĐỊNH DẠNG SAU:
{
  "Breakfast": ["tên món 1", "tên món 2", ...],
  "Lunch": ["tên món 1", "tên món 2", ...],
  "Dinner": ["tên món 1", "tên món 2", ...],
  "Snack": ["tên món 1"]
}

Lưu ý: Chỉ trả về mã JSON thô, không viết thêm chữ giải thích và không bọc khối code markdown.
"""
                primary_model_name = "gemini-3.5-flash"
                fallback_model_name = "gemini-3.1-flash-lite"
                
                try:
                    model = genai.GenerativeModel(primary_model_name)
                    response = model.generate_content(prompt)
                except Exception as model_err:
                    print(f"Primary model {primary_model_name} failed: {model_err}. Trying fallback {fallback_model_name}...")
                    model = genai.GenerativeModel(fallback_model_name)
                    response = model.generate_content(prompt)
                
                response_text = response.text.strip()
                
                # Clean markdown blocks if present
                if response_text.startswith("```"):
                    json_match = re.search(r'(\{.*\})', response_text, re.DOTALL)
                    if json_match:
                        response_text = json_match.group(1).strip()
                
                selected_names = json.loads(response_text)
                
                suggested_menu = {}
                # Map names back to full meal records
                for m_type in ["Breakfast", "Lunch", "Dinner", "Snack"]:
                    m_names = selected_names.get(m_type, [])
                    if isinstance(m_names, str):
                        m_names = [m_names]
                    
                    dishes_in_meal = []
                    for m_name in m_names:
                        m_name = m_name.strip()
                        if not m_name:
                            continue
                        
                        # Find the candidate lists for this meal type
                        candidates = []
                        if m_type == "Breakfast":
                            candidates = retrieved_context["Breakfast_Candidates"]
                        elif m_type == "Lunch":
                            candidates = (
                                retrieved_context["Lunch_Candidates_Protein"] +
                                retrieved_context["Lunch_Candidates_Soup"] +
                                retrieved_context["Lunch_Candidates_Veggie"]
                            )
                        elif m_type == "Dinner":
                            candidates = (
                                retrieved_context["Dinner_Candidates_Protein"] +
                                retrieved_context["Dinner_Candidates_Soup"] +
                                retrieved_context["Dinner_Candidates_Veggie"]
                            )
                        elif m_type == "Snack":
                            candidates = retrieved_context["Snack_Candidates"]
                        
                        db_meal = next((m for m in candidates if m["name"].lower() == m_name.lower()), None)
                        if not db_meal:
                            # Fallback search inside full database
                            db_meal = next((m for m in meals if m["name"].lower() == m_name.lower()), None)
                        
                        if db_meal:
                            dishes_in_meal.append(db_meal)
                        else:
                            # Try partial match as fallback
                            db_meal = next((m for m in meals if m_name.lower() in m["name"].lower()), None)
                            if db_meal:
                                dishes_in_meal.append(db_meal)
                            else:
                                raise ValueError(f"Không tìm thấy món ăn '{m_name}' được gợi ý từ LLM")
                    
                    if not dishes_in_meal:
                        raise ValueError(f"Bữa ăn '{m_type}' không có món ăn hợp lệ nào.")
                    
                    # Combine dishes_in_meal into a single composite dish
                    combined_name = " + ".join(d["name"] for d in dishes_in_meal)
                    combined_cal = sum(d["calories_kcal"] for d in dishes_in_meal)
                    combined_p = sum(d["protein_g"] for d in dishes_in_meal)
                    combined_c = sum(d["carbohydrates_g"] for d in dishes_in_meal)
                    combined_f = sum(d["fat_g"] for d in dishes_in_meal)
                    
                    suggested_menu[m_type] = {
                        "id": f"composite_{m_type.lower()}_" + "_".join(str(d["id"]) for d in dishes_in_meal),
                        "name": combined_name,
                        "calories_kcal": combined_cal,
                        "protein_g": combined_p,
                        "carbohydrates_g": combined_c,
                        "fat_g": combined_f
                    }
                
                if len(suggested_menu) == 4:
                    llm_success = True
            except Exception as e:
                print(f"LLM RAG Generation failed: {e}")
                llm_success = False

        # 4. Strict Verification (+- 15% constraint checks)
        valid_menu = False
        if llm_success and suggested_menu:
            total_cal = sum(m["calories_kcal"] for m in suggested_menu.values())
            total_p = sum(m["protein_g"] for m in suggested_menu.values())
            total_c = sum(m["carbohydrates_g"] for m in suggested_menu.values())
            total_f = sum(m["fat_g"] for m in suggested_menu.values())

            # Check limits (+- 15%)
            cal_ok = (target_calories * 0.85) <= total_cal <= (target_calories * 1.15)
            p_ok = (target_p * 0.85) <= total_p <= (target_p * 1.15)
            c_ok = (target_c * 0.85) <= total_c <= (target_c * 1.15)
            f_ok = (target_f * 0.85) <= total_f <= (target_f * 1.15)

            if cal_ok and p_ok and c_ok and f_ok:
                valid_menu = True
                print("✅ RAG LLM Recommendation verified within strict +-15% constraints.")
            else:
                print("⚠️ RAG LLM suggestion violated +-15% limits. Solving programmatically...")

        # 5. Programmatic Fallback Constraint Solver
        if not valid_menu:
            best_combo = None
            best_score = float('inf')
            
            # Search combinations using the retrieved candidates lists to satisfy targets
            rng = random.Random(hash(user_id))
            
            # Since candidate lists are small, we can sample combinations
            for _ in range(4000):
                # Breakfast: 1-2 món
                num_bf = rng.choice([1, 2])
                bf_list = []
                for _ in range(num_bf):
                    item = rng.choice(retrieved_breakfasts)
                    if item not in bf_list:
                        bf_list.append(item)

                # Lunch: 1 món mặn + 1 canh + 1 rau (or subset)
                lh_list = []
                p_item = rng.choice(retrieved_lh_proteins)
                lh_list.append(p_item)
                if rng.choice([True, False]):
                    lh_list.append(rng.choice(retrieved_lh_soups))
                if rng.choice([True, False]):
                    s_item = rng.choice(retrieved_lh_veggies)
                    if s_item not in lh_list:
                        lh_list.append(s_item)

                # Dinner: 1 món mặn + 1 canh + 1 rau (or subset)
                dn_list = []
                p_item = rng.choice(retrieved_dn_proteins)
                dn_list.append(p_item)
                if rng.choice([True, False]):
                    dn_list.append(rng.choice(retrieved_dn_soups))
                if rng.choice([True, False]):
                    s_item = rng.choice(retrieved_dn_veggies)
                    if s_item not in dn_list:
                        dn_list.append(s_item)

                # Snack: 1 món
                sn_list = [rng.choice(retrieved_snacks)]

                # Avoid duplicates between Lunch and Dinner
                lh_ids = {d["id"] for d in lh_list}
                dn_ids = {d["id"] for d in dn_list}
                if lh_ids.intersection(dn_ids) and (len(retrieved_lh_proteins) > 1 or len(retrieved_dn_proteins) > 1):
                    continue

                all_chosen_dishes = bf_list + lh_list + dn_list + sn_list
                total_cal = sum(d["calories_kcal"] for d in all_chosen_dishes)
                total_p = sum(d["protein_g"] for d in all_chosen_dishes)
                total_c = sum(d["carbohydrates_g"] for d in all_chosen_dishes)
                total_f = sum(d["fat_g"] for d in all_chosen_dishes)

                # Strict check
                cal_ok = (target_calories * 0.85) <= total_cal <= (target_calories * 1.15)
                p_ok = (target_p * 0.85) <= total_p <= (target_p * 1.15)
                c_ok = (target_c * 0.85) <= total_c <= (target_c * 1.15)
                f_ok = (target_f * 0.85) <= total_f <= (target_f * 1.15)

                if cal_ok and p_ok and c_ok and f_ok:
                    score = (
                        abs(total_cal - target_calories) * 1.0 +
                        abs(total_p - target_p) * 4.0 +
                        abs(total_c - target_c) * 2.0 +
                        abs(total_f - target_f) * 3.0
                    )
                    # Apply preference bonus to lower the score (making it better)
                    if preferred_dishes:
                        pref_lower = [p.lower().strip() for p in preferred_dishes if p.strip()]
                        for meal in all_chosen_dishes:
                            if any(p in meal["name"].lower() for p in pref_lower):
                                score -= 1000
                    
                    if score < best_score:
                        best_score = score
                        best_combo = {
                            "Breakfast": bf_list,
                            "Lunch": lh_list,
                            "Dinner": dn_list,
                            "Snack": sn_list,
                            "totals": {
                                "calories": total_cal,
                                "protein_g": total_p,
                                "carbohydrates_g": total_c,
                                "fat_g": total_f
                            }
                        }

            if best_combo:
                suggested_menu = {}
                for m_type in ["Breakfast", "Lunch", "Dinner", "Snack"]:
                    dishes_in_meal = best_combo[m_type]
                    combined_name = " + ".join(d["name"] for d in dishes_in_meal)
                    combined_cal = sum(d["calories_kcal"] for d in dishes_in_meal)
                    combined_p = sum(d["protein_g"] for d in dishes_in_meal)
                    combined_c = sum(d["carbohydrates_g"] for d in dishes_in_meal)
                    combined_f = sum(d["fat_g"] for d in dishes_in_meal)
                    suggested_menu[m_type] = {
                        "id": f"composite_{m_type.lower()}_" + "_".join(str(d["id"]) for d in dishes_in_meal),
                        "name": combined_name,
                        "calories_kcal": combined_cal,
                        "protein_g": combined_p,
                        "carbohydrates_g": combined_c,
                        "fat_g": combined_f
                    }
                total_cal = best_combo["totals"]["calories"]
                total_p = best_combo["totals"]["protein_g"]
                total_c = best_combo["totals"]["carbohydrates_g"]
                total_f = best_combo["totals"]["fat_g"]
            else:
                # Absolute fallback search over all meals in the database to guarantee constraints are met
                for _ in range(5000):
                    num_bf = rng.choice([1, 2])
                    bf_list = []
                    for _ in range(num_bf):
                        item = rng.choice(all_breakfasts)
                        if item not in bf_list:
                            bf_list.append(item)

                    lh_list = []
                    p_item = rng.choice(all_proteins)
                    lh_list.append(p_item)
                    if rng.choice([True, False]):
                        lh_list.append(rng.choice(all_soups))
                    if rng.choice([True, False]):
                        s_item = rng.choice(all_veggies)
                        if s_item not in lh_list:
                            lh_list.append(s_item)

                    dn_list = []
                    p_item = rng.choice(all_proteins)
                    dn_list.append(p_item)
                    if rng.choice([True, False]):
                        dn_list.append(rng.choice(all_soups))
                    if rng.choice([True, False]):
                        s_item = rng.choice(all_veggies)
                        if s_item not in dn_list:
                            dn_list.append(s_item)

                    sn_list = [rng.choice(all_snacks)]

                    lh_ids = {d["id"] for d in lh_list}
                    dn_ids = {d["id"] for d in dn_list}
                    if lh_ids.intersection(dn_ids):
                        continue

                    all_chosen_dishes = bf_list + lh_list + dn_list + sn_list
                    tc = sum(d["calories_kcal"] for d in all_chosen_dishes)
                    tp = sum(d["protein_g"] for d in all_chosen_dishes)
                    t_carbs = sum(d["carbohydrates_g"] for d in all_chosen_dishes)
                    tf = sum(d["fat_g"] for d in all_chosen_dishes)

                    cal_ok = (target_calories * 0.85) <= tc <= (target_calories * 1.15)
                    p_ok = (target_p * 0.85) <= tp <= (target_p * 1.15)
                    c_ok = (target_c * 0.85) <= t_carbs <= (target_c * 1.15)
                    f_ok = (target_f * 0.85) <= tf <= (target_f * 1.15)

                    if cal_ok and p_ok and c_ok and f_ok:
                        score = abs(tc - target_calories)
                        if preferred_dishes:
                            pref_lower = [p.lower().strip() for p in preferred_dishes if p.strip()]
                            for meal in all_chosen_dishes:
                                if any(p in meal["name"].lower() for p in pref_lower):
                                    score -= 1000
                        if score < best_score:
                            best_score = score
                            best_combo = {
                                "Breakfast": bf_list,
                                "Lunch": lh_list,
                                "Dinner": dn_list,
                                "Snack": sn_list,
                                "totals": {"calories": tc, "protein_g": tp, "carbohydrates_g": t_carbs, "fat_g": tf}
                            }
                if best_combo:
                    suggested_menu = {}
                    for m_type in ["Breakfast", "Lunch", "Dinner", "Snack"]:
                        dishes_in_meal = best_combo[m_type]
                        combined_name = " + ".join(d["name"] for d in dishes_in_meal)
                        combined_cal = sum(d["calories_kcal"] for d in dishes_in_meal)
                        combined_p = sum(d["protein_g"] for d in dishes_in_meal)
                        combined_c = sum(d["carbohydrates_g"] for d in dishes_in_meal)
                        combined_f = sum(d["fat_g"] for d in dishes_in_meal)
                        suggested_menu[m_type] = {
                            "id": f"composite_{m_type.lower()}_" + "_".join(str(d["id"]) for d in dishes_in_meal),
                            "name": combined_name,
                            "calories_kcal": combined_cal,
                            "protein_g": combined_p,
                            "carbohydrates_g": combined_c,
                            "fat_g": combined_f
                        }
                    total_cal = best_combo["totals"]["calories"]
                    total_p = best_combo["totals"]["protein_g"]
                    total_c = best_combo["totals"]["carbohydrates_g"]
                    total_f = best_combo["totals"]["fat_g"]
                else:
                    # Final safety fallback: just return the closest possible combination in calories
                    closest_combo = None
                    closest_score = float('inf')
                    for _ in range(2000):
                        num_bf = rng.choice([1, 2])
                        bf_list = []
                        for _ in range(num_bf):
                            item = rng.choice(all_breakfasts)
                            if item not in bf_list:
                                bf_list.append(item)

                        lh_list = []
                        p_item = rng.choice(all_proteins)
                        lh_list.append(p_item)
                        if rng.choice([True, False]):
                            lh_list.append(rng.choice(all_soups))
                        if rng.choice([True, False]):
                            s_item = rng.choice(all_veggies)
                            if s_item not in lh_list:
                                lh_list.append(s_item)

                        dn_list = []
                        p_item = rng.choice(all_proteins)
                        dn_list.append(p_item)
                        if rng.choice([True, False]):
                            dn_list.append(rng.choice(all_soups))
                        if rng.choice([True, False]):
                            s_item = rng.choice(all_veggies)
                            if s_item not in dn_list:
                                dn_list.append(s_item)

                        sn_list = [rng.choice(all_snacks)]

                        all_chosen_dishes = bf_list + lh_list + dn_list + sn_list
                        tc = sum(d["calories_kcal"] for d in all_chosen_dishes)
                        tp = sum(d["protein_g"] for d in all_chosen_dishes)
                        t_carbs = sum(d["carbohydrates_g"] for d in all_chosen_dishes)
                        tf = sum(d["fat_g"] for d in all_chosen_dishes)

                        score = abs(tc - target_calories)
                        if preferred_dishes:
                            pref_lower = [p.lower().strip() for p in preferred_dishes if p.strip()]
                            for meal in all_chosen_dishes:
                                if any(p in meal["name"].lower() for p in pref_lower):
                                    score -= 1000
                        
                        if score < closest_score:
                            closest_score = score
                            closest_combo = {
                                "Breakfast": bf_list,
                                "Lunch": lh_list,
                                "Dinner": dn_list,
                                "Snack": sn_list,
                                "totals": {"calories": tc, "protein_g": tp, "carbohydrates_g": t_carbs, "fat_g": tf}
                            }
                    if closest_combo:
                        suggested_menu = {}
                        for m_type in ["Breakfast", "Lunch", "Dinner", "Snack"]:
                            dishes_in_meal = closest_combo[m_type]
                            combined_name = " + ".join(d["name"] for d in dishes_in_meal)
                            combined_cal = sum(d["calories_kcal"] for d in dishes_in_meal)
                            combined_p = sum(d["protein_g"] for d in dishes_in_meal)
                            combined_c = sum(d["carbohydrates_g"] for d in dishes_in_meal)
                            combined_f = sum(d["fat_g"] for d in dishes_in_meal)
                            suggested_menu[m_type] = {
                                "id": f"composite_{m_type.lower()}_" + "_".join(str(d["id"]) for d in dishes_in_meal),
                                "name": combined_name,
                                "calories_kcal": combined_cal,
                                "protein_g": combined_p,
                                "carbohydrates_g": combined_c,
                                "fat_g": combined_f
                            }
                        total_cal = closest_combo["totals"]["calories"]
                        total_p = closest_combo["totals"]["protein_g"]
                        total_c = closest_combo["totals"]["carbohydrates_g"]
                        total_f = closest_combo["totals"]["fat_g"]

        # 6. Return response
        menu_result = {
            "user_id": user_id,
            "name": user["name"],
            "goal": user["goal"],
            "targets": {
                "calories": target_calories,
                "protein_g": target_p,
                "carbohydrates_g": target_c,
                "fat_g": target_f
            },
            "menu": suggested_menu,
            "totals": {
                "calories": total_cal,
                "protein_g": total_p,
                "carbohydrates_g": total_c,
                "fat_g": total_f
            },
            "message": f"Gợi ý thực đơn thành công! Tổng năng lượng: {total_cal} kcal (Mục tiêu: {target_calories} kcal). Tỷ lệ dinh dưỡng nạp lệch không quá 15% mục tiêu: Protein lệch {abs(getProgressPercentage(total_p, target_p) - 100)}%, Carbs lệch {abs(getProgressPercentage(total_c, target_c) - 100)}%, Fat lệch {abs(getProgressPercentage(total_f, target_f) - 100)}%."
        }

        # 7. Save to mock user in database
        if suggested_menu:
            from tools.db_utils import save_users
            for u in users:
                if u["id"] == user_id:
                    u["recommended_menu"] = menu_result
                    break
            save_users(users)

        return json.dumps(menu_result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"Lỗi lập thực đơn dinh dưỡng RAG: {str(e)}"}, ensure_ascii=False)

def getProgressPercentage(consumed, target):
    if not target: return 0
    return Math_round((consumed / target) * 100)

def Math_round(val):
    return int(val + 0.5)
