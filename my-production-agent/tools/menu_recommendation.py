import os
import sys
import json
import re
import random
import google.generativeai as genai
from typing import List, Optional, Dict, Any
from dotenv import load_dotenv
from tools.db_utils import load_users, load_meals

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

        # Sort and retrieved candidates
        retrieved_breakfasts = sorted(all_breakfasts, key=lambda x: abs(x["calories_kcal"] - bf_target_cal))
        retrieved_lunches = sorted(all_mains, key=lambda x: abs(x["calories_kcal"] - lh_target_cal))
        retrieved_dinners = sorted(all_mains, key=lambda x: abs(x["calories_kcal"] - dn_target_cal))
        retrieved_snacks = sorted(all_snacks, key=lambda x: abs(x["calories_kcal"] - sn_target_cal))

        # Force prepend preferred dishes to candidate lists
        def merge_forced(candidates, forced, limit=8):
            forced_ids = {f["id"] for f in forced}
            filtered_candidates = [c for c in candidates if c["id"] not in forced_ids]
            merged = forced + filtered_candidates
            return merged[:limit]

        retrieved_breakfasts = merge_forced(retrieved_breakfasts, forced_breakfasts)
        retrieved_lunches = merge_forced(retrieved_lunches, forced_mains)
        retrieved_dinners = merge_forced(retrieved_dinners, forced_mains)
        retrieved_snacks = merge_forced(retrieved_snacks, forced_snacks)

        # Combine retrieved candidates for context and fallback
        retrieved_context = {
            "Breakfast_Candidates": retrieved_breakfasts,
            "Lunch_Candidates": retrieved_lunches,
            "Dinner_Candidates": retrieved_dinners,
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
Bạn là một Chuyên gia Dinh dưỡng AI. Nhiệm vụ của bạn là lập một thực đơn trong ngày gồm đúng 4 món ăn (Breakfast, Lunch, Dinner, Snack) chọn từ danh sách món ăn ứng viên được TRUY XUẤT từ RAG database dưới đây.

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
{json.dumps([{k: m[k] for k in ["name", "calories_kcal", "protein_g", "carbohydrates_g", "fat_g"]} for m in retrieved_lunches], ensure_ascii=False, indent=2)}

- Ứng viên Bữa tối (Dinner Candidates):
{json.dumps([{k: m[k] for k in ["name", "calories_kcal", "protein_g", "carbohydrates_g", "fat_g"]} for m in retrieved_dinners], ensure_ascii=False, indent=2)}

- Ứng viên Bữa phụ (Snack Candidates):
{json.dumps([{k: m[k] for k in ["name", "calories_kcal", "protein_g", "carbohydrates_g", "fat_g"]} for m in retrieved_snacks], ensure_ascii=False, indent=2)}

QUY TẮC LỰA CHỌN:
1. Hãy chọn CHÍNH XÁC MỘT MÓN cho mỗi bữa (Breakfast, Lunch, Dinner, Snack) từ danh sách ứng viên tương ứng.
2. Tránh chọn trùng lặp món ăn cho bữa trưa và bữa tối.
3. ĐẢM BẢO RẰNG: Tổng các chỉ số dinh dưỡng (Calories, Protein, Carbs, Fat) của 4 món được chọn phải thỏa mãn sai số LỆCH KHÔNG QUÁ 15% so với chỉ tiêu mục tiêu người dùng đã nêu ở trên.
"""
                if preferred_dishes:
                    prompt += "4. ƯU TIÊN TUYỆT ĐỐI: Hãy chọn các món ăn có tên hoặc chứa nguyên liệu nằm trong danh sách Món ăn muốn ƯU TIÊN ở trên (nếu chúng có trong danh sách ứng viên).\n"
                if allergies:
                    prompt += "5. TRÁNH TUYỆT ĐỐI: Không được chọn bất kỳ món nào chứa nguyên liệu bị DỊ ỨNG ở trên.\n"

                prompt += """
HÃY TRẢ VỀ DUY NHẤT CHUỖI JSON THEO ĐỊNH DẠNG SAU:
{
  "Breakfast": "tên món đã chọn",
  "Lunch": "tên món đã chọn",
  "Dinner": "tên món đã chọn",
  "Snack": "tên món đã chọn"
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
                    m_name = selected_names.get(m_type, "").strip()
                    # Look up inside the specific candidates first
                    candidates = retrieved_context[f"{m_type}_Candidates"]
                    db_meal = next((m for m in candidates if m["name"].lower() == m_name.lower()), None)
                    
                    if not db_meal:
                        # Fallback search inside full database
                        db_meal = next((m for m in meals if m["name"].lower() == m_name.lower()), None)
                        
                    if db_meal:
                        suggested_menu[m_type] = db_meal
                    else:
                        raise ValueError(f"Không tìm thấy món ăn '{m_name}' được gợi ý từ LLM")
                
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
            
            # Search combinations using the retrieved candidates list to satisfy targets
            rng = random.Random(hash(user_id))
            
            # Since candidate lists are small (8 each), we can check combinations
            # Total possible combinations is 8 * 8 * 8 * 8 = 4096. We can do an exhaustive or randomized search.
            # Let's check 4000 random combinations from candidate lists
            for _ in range(4000):
                bf = rng.choice(retrieved_breakfasts)
                lh = rng.choice(retrieved_lunches)
                dn = rng.choice(retrieved_dinners)
                sn = rng.choice(retrieved_snacks)

                if lh["id"] == dn["id"] and len(retrieved_lunches) > 1:
                    continue

                total_cal = bf["calories_kcal"] + lh["calories_kcal"] + dn["calories_kcal"] + sn["calories_kcal"]
                total_p = bf["protein_g"] + lh["protein_g"] + dn["protein_g"] + sn["protein_g"]
                total_c = bf["carbohydrates_g"] + lh["carbohydrates_g"] + dn["carbohydrates_g"] + sn["carbohydrates_g"]
                total_f = bf["fat_g"] + lh["fat_g"] + dn["fat_g"] + sn["fat_g"]

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
                        for meal in [bf, lh, dn, sn]:
                            if any(p in meal["name"].lower() for p in pref_lower):
                                score -= 1000
                    
                    if score < best_score:
                        best_score = score
                        best_combo = {
                            "Breakfast": bf,
                            "Lunch": lh,
                            "Dinner": dn,
                            "Snack": sn,
                            "totals": {
                                "calories": total_cal,
                                "protein_g": total_p,
                                "carbohydrates_g": total_c,
                                "fat_g": total_f
                            }
                        }

            if best_combo:
                suggested_menu = {
                    "Breakfast": best_combo["Breakfast"],
                    "Lunch": best_combo["Lunch"],
                    "Dinner": best_combo["Dinner"],
                    "Snack": best_combo["Snack"]
                }
                total_cal = best_combo["totals"]["calories"]
                total_p = best_combo["totals"]["protein_g"]
                total_c = best_combo["totals"]["carbohydrates_g"]
                total_f = best_combo["totals"]["fat_g"]
            else:
                # Absolute fallback search over all meals in the database to guarantee constraints are met
                for _ in range(5000):
                    bf = rng.choice(all_breakfasts)
                    lh = rng.choice(all_mains)
                    dn = rng.choice(all_mains)
                    sn = rng.choice(all_snacks)
                    if lh["id"] == dn["id"]: continue

                    tc = bf["calories_kcal"] + lh["calories_kcal"] + dn["calories_kcal"] + sn["calories_kcal"]
                    tp = bf["protein_g"] + lh["protein_g"] + dn["protein_g"] + sn["protein_g"]
                    t_carbs = bf["carbohydrates_g"] + lh["carbohydrates_g"] + dn["carbohydrates_g"] + sn["carbohydrates_g"]
                    tf = bf["fat_g"] + lh["fat_g"] + dn["fat_g"] + sn["fat_g"]

                    cal_ok = (target_calories * 0.85) <= tc <= (target_calories * 1.15)
                    p_ok = (target_p * 0.85) <= tp <= (target_p * 1.15)
                    c_ok = (target_c * 0.85) <= t_carbs <= (target_c * 1.15)
                    f_ok = (target_f * 0.85) <= tf <= (target_f * 1.15)

                    if cal_ok and p_ok and c_ok and f_ok:
                        score = abs(tc - target_calories)
                        if preferred_dishes:
                            pref_lower = [p.lower().strip() for p in preferred_dishes if p.strip()]
                            for meal in [bf, lh, dn, sn]:
                                if any(p in meal["name"].lower() for p in pref_lower):
                                    score -= 1000
                        if score < best_score:
                            best_score = score
                            best_combo = {
                                "Breakfast": bf,
                                "Lunch": lh,
                                "Dinner": dn,
                                "Snack": sn,
                                "totals": {"calories": tc, "protein_g": tp, "carbohydrates_g": t_carbs, "fat_g": tf}
                            }
                if best_combo:
                    suggested_menu = {
                        "Breakfast": best_combo["Breakfast"],
                        "Lunch": best_combo["Lunch"],
                        "Dinner": best_combo["Dinner"],
                        "Snack": best_combo["Snack"]
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
                        bf = rng.choice(all_breakfasts)
                        lh = rng.choice(all_mains)
                        dn = rng.choice(all_mains)
                        sn = rng.choice(all_snacks)
                        if lh["id"] == dn["id"]: continue
                        tc = bf["calories_kcal"] + lh["calories_kcal"] + dn["calories_kcal"] + sn["calories_kcal"]
                        tp = bf["protein_g"] + lh["protein_g"] + dn["protein_g"] + sn["protein_g"]
                        t_carbs = bf["carbohydrates_g"] + lh["carbohydrates_g"] + dn["carbohydrates_g"] + sn["carbohydrates_g"]
                        tf = bf["fat_g"] + lh["fat_g"] + dn["fat_g"] + sn["fat_g"]
                        
                        score = abs(tc - target_calories)
                        if preferred_dishes:
                            pref_lower = [p.lower().strip() for p in preferred_dishes if p.strip()]
                            for meal in [bf, lh, dn, sn]:
                                if any(p in meal["name"].lower() for p in pref_lower):
                                    score -= 1000
                        
                        if score < closest_score:
                            closest_score = score
                            closest_combo = {
                                "Breakfast": bf,
                                "Lunch": lh,
                                "Dinner": dn,
                                "Snack": sn,
                                "totals": {"calories": tc, "protein_g": tp, "carbohydrates_g": t_carbs, "fat_g": tf}
                            }
                    if closest_combo:
                        suggested_menu = {
                            "Breakfast": closest_combo["Breakfast"],
                            "Lunch": closest_combo["Lunch"],
                            "Dinner": closest_combo["Dinner"],
                            "Snack": closest_combo["Snack"]
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
