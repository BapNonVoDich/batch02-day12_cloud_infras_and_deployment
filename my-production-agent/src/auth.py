from fastapi import Header, HTTPException
from .config import settings

def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != settings.AGENT_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    # Tạm thời trả về user mặc định vì old-pj dùng user_id trong body, 
    # nhưng để đơn giản, ta cho qua header. Trong thực tế sẽ map key với user.
    return "user_from_api_key"
