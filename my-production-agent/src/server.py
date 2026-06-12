import os
import sys
import json
import logging
import time
import signal
from typing import Dict, Any, List, Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.config import settings
from src.auth import verify_api_key
from src.rate_limiter import check_rate_limit
from src.cost_guard import check_budget
from src.core.gemini_provider import GeminiProvider
from src.agent.agent import ReActAgent
from tools.db_utils import load_users, save_users, load_meals, load_chat_history, save_chat_history, r as redis_client
from tools.tdee_calculator import calculate_tdee
from tools.meal_logger import log_meal
from tools.summary_viewer import get_daily_summary
from tools.menu_recommendation import recommend_daily_menu

# Cấu hình JSON logging
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format='{"time":"%(asctime)s","level":"%(levelname)s","msg":"%(message)s"}',
)
logger = logging.getLogger(__name__)

START_TIME = time.time()
is_ready = False

@asynccontextmanager
async def lifespan(app: FastAPI):
    global is_ready
    logger.info(json.dumps({"event": "startup", "msg": "Starting server"}))
    # Simulate DB connections
    time.sleep(0.1)
    is_ready = True
    yield
    is_ready = False
    logger.info(json.dumps({"event": "shutdown", "msg": "Shutting down gracefully..."}))
    time.sleep(1)

def handle_sigterm(*args):
    logger.info(json.dumps({"event": "sigterm", "msg": "Received SIGTERM, initiating graceful shutdown"}))

signal.signal(signal.SIGTERM, handle_sigterm)

app = FastAPI(title="AI Nutrition Agent API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_key = settings.GEMINI_API_KEY
if not api_key or api_key == "your_gemini_api_key_here":
    logger.warning("GEMINI_API_KEY not found or default! Agent features will fail.")

# Models
class UserProfileRequest(BaseModel):
    id: Optional[str] = None
    name: str
    age: int
    gender: str
    weight_kg: float
    height_cm: float
    activity_level: str
    goal: str

class LogMealRequest(BaseModel):
    meal_type: str
    dish_name: str
    portion_size: float = 1.0

class ChatRequest(BaseModel):
    user_id: Optional[str] = None
    message: str

# Health & Ready endpoints
@app.get("/health")
def health_check():
    uptime = round(time.time() - START_TIME, 1)
    return {"status": "ok", "uptime": uptime}

@app.get("/ready")
def ready_check():
    if not is_ready:
        raise HTTPException(status_code=503, detail="Agent not ready yet")
    try:
        redis_client.ping()
        return {"ready": True}
    except Exception as e:
        logger.error(f"Redis check failed: {e}")
        raise HTTPException(status_code=503, detail="Redis connection failed")

@app.get("/")
def read_root():
    return {"status": "ok", "message": "AI Nutrition Agent API is running."}

@app.get("/api/users", dependencies=[Depends(verify_api_key)])
def get_users():
    return load_users()

@app.post("/api/users", dependencies=[Depends(verify_api_key)])
def create_or_update_user(profile: UserProfileRequest):
    users = load_users()
    tdee_json_str = calculate_tdee(
        weight_kg=profile.weight_kg,
        height_cm=profile.height_cm,
        age=profile.age,
        gender=profile.gender,
        activity_level=profile.activity_level,
        goal=profile.goal
    )
    tdee_data = json.loads(tdee_json_str)
    if "error" in tdee_data:
        raise HTTPException(status_code=400, detail=tdee_data["error"])
        
    user_id = profile.id if profile.id else f"user_{len(users) + 1}"
    user = next((u for u in users if u["id"] == user_id), None)
    if user:
        user["name"] = profile.name
        user["age"] = profile.age
        user["gender"] = profile.gender
        user["weight_kg"] = profile.weight_kg
        user["height_cm"] = profile.height_cm
        user["activity_level"] = profile.activity_level
        user["goal"] = profile.goal
        user["target_calories"] = tdee_data["target_calories"]
        user["target_protein_g"] = tdee_data["target_protein_g"]
        user["target_carbs_g"] = tdee_data["target_carbs_g"]
        user["target_fat_g"] = tdee_data["target_fat_g"]
    else:
        user = {
            "id": user_id,
            "name": profile.name,
            "age": profile.age,
            "gender": profile.gender,
            "weight_kg": profile.weight_kg,
            "height_cm": profile.height_cm,
            "activity_level": profile.activity_level,
            "goal": profile.goal,
            "target_calories": tdee_data["target_calories"],
            "target_protein_g": tdee_data["target_protein_g"],
            "target_carbs_g": tdee_data["target_carbs_g"],
            "target_fat_g": tdee_data["target_fat_g"],
            "logged_meals": []
        }
        users.append(user)
        
    save_users(users)
    return user

@app.get("/api/users/{user_id}/summary", dependencies=[Depends(verify_api_key)])
def get_user_summary(user_id: str):
    summary_str = get_daily_summary(user_id)
    summary_data = json.loads(summary_str)
    if "error" in summary_data:
        raise HTTPException(status_code=404, detail=summary_data["error"])
    return summary_data

@app.get("/api/users/{user_id}/recommend_menu", dependencies=[Depends(verify_api_key)])
def get_user_menu_recommendation(
    user_id: str,
    preferred_dishes: Optional[str] = None,
    allergies: Optional[str] = None
):
    pref_list = [d.strip() for d in preferred_dishes.split(",")] if preferred_dishes else None
    allergy_list = [a.strip() for a in allergies.split(",")] if allergies else None
    
    menu_str = recommend_daily_menu(user_id, preferred_dishes=pref_list, allergies=allergy_list)
    menu_data = json.loads(menu_str)
    if "error" in menu_data:
        raise HTTPException(status_code=400, detail=menu_data["error"])
    return menu_data

@app.post("/api/users/{user_id}/log", dependencies=[Depends(verify_api_key)])
def user_log_meal(user_id: str, request: LogMealRequest):
    log_result_str = log_meal(
        user_id=user_id,
        meal_type=request.meal_type,
        dish_name=request.dish_name,
        portion_size=request.portion_size
    )
    log_result = json.loads(log_result_str)
    if "error" in log_result:
        raise HTTPException(status_code=400, detail=log_result["error"])
    return log_result

@app.get("/api/dishes", dependencies=[Depends(verify_api_key)])
def get_dishes(q: Optional[str] = None):
    meals = load_meals()
    if not q:
        return meals
    query = q.lower().strip()
    return [m for m in meals if query in m["name"].lower()]

@app.post("/api/chat")
def chat_with_agent(
    request: ChatRequest,
    api_key_user: str = Depends(verify_api_key),
    _rate: None = Depends(check_rate_limit),
    _budget: None = Depends(check_budget)
):
    if not api_key:
        raise HTTPException(status_code=500, detail="Gemini API Key is not configured.")
        
    user_context = None
    if request.user_id:
        users = load_users()
        user_context = next((u for u in users if u["id"] == request.user_id), None)

    try:
        history = []
        if request.user_id:
            history = load_chat_history(request.user_id)

        provider = GeminiProvider(model_name="gemini-3.5-flash", api_key=api_key)
        agent = ReActAgent(llm=provider)
        
        result = agent.run(user_input=request.message, user_context=user_context, chat_history=history)
        
        if request.user_id:
            history.append({
                "sender": "user",
                "text": request.message,
                "trace": None,
                "eval": None
            })
            history.append({
                "sender": "assistant",
                "text": result["final_answer"],
                "trace": result["history"],
                "eval": result.get("eval")
            })
            save_chat_history(request.user_id, history)
            
        logger.info(json.dumps({"event": "chat_processed", "user": request.user_id}))
        return result
    except Exception as e:
        logger.error(json.dumps({"event": "chat_error", "error": str(e)}))
        raise HTTPException(status_code=500, detail=f"Error in Agent reasoning: {str(e)}")

@app.get("/api/chat/history/{user_id}", dependencies=[Depends(verify_api_key)])
def get_user_chat_history(user_id: str):
    history = load_chat_history(user_id)
    if not history:
        users = load_users()
        user = next((u for u in users if u["id"] == user_id), None)
        name = user["name"] if user else "bạn"
        return [
            {
                "sender": "assistant",
                "text": f"Chào mừng {name} trở lại! Hôm nay bạn cần tôi hỗ trợ gì về dinh dưỡng hoặc lập kế hoạch ăn uống?",
                "trace": None
            }
        ]
    return history

@app.post("/api/chat/history/{user_id}/clear", dependencies=[Depends(verify_api_key)])
def clear_user_chat_history(user_id: str):
    save_chat_history(user_id, [])
    users = load_users()
    user = next((u for u in users if u["id"] == user_id), None)
    name = user["name"] if user else "bạn"
    return [
        {
            "sender": "assistant",
            "text": f"Chào mừng {name} trở lại! Hôm nay bạn cần tôi hỗ trợ gì về dinh dưỡng hoặc lập kế hoạch ăn uống?",
            "trace": None
        }
    ]

if __name__ == "__main__":
    import uvicorn
    logger.info(f"Starting API on port {settings.PORT}")
    uvicorn.run("src.server:app", host="0.0.0.0", port=settings.PORT)
