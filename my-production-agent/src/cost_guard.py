import redis
from datetime import datetime
from fastapi import HTTPException
from .config import settings

r = redis.from_url(settings.REDIS_URL, decode_responses=True)

def check_budget(user_id: str = "default"):
    month_key = datetime.now().strftime("%Y-%m")
    key = f"budget:{user_id}:{month_key}"
    
    current = float(r.get(key) or 0)
    estimated_cost = 0.01  # Cost per request
    if current + estimated_cost > settings.MONTHLY_BUDGET_USD:
        raise HTTPException(status_code=402, detail="Payment Required: Budget Exceeded")
    
    r.incrbyfloat(key, estimated_cost)
    r.expire(key, 32 * 24 * 3600)
