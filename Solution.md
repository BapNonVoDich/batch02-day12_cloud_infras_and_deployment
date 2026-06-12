# Solution for Code Lab: Deploy Your AI Agent to Production

## Part 1: Localhost vs Production

### Exercise 1.1: Phát hiện anti-patterns
Phân tích 10 vấn đề nghiêm trọng trong `app.py` (basic version):
1. **API Key & Database URL hardcoded**: Rủi ro bảo mật cực kỳ lớn. Lộ secrets nếu source code bị đưa lên GitHub hoặc chia sẻ.
2. **Log ra secret**: Cố tình `print` API key ra console (`print(f"[DEBUG] Using key: {OPENAI_API_KEY}")`). Đây là lỗi bảo mật (CWE-532), hệ thống log có thể bị các nhân sự khác truy cập làm lộ lọt thông tin.
3. **Không có Config Management**: Các thông số `DEBUG`, `MAX_TOKENS` bị gán cứng. Theo nguyên tắc 12-Factor App, cấu hình nên được đọc từ Environment Variables để dễ thay đổi giữa các môi trường (Dev/Stag/Prod).
4. **Sử dụng `print` thay vì proper logging**: Khó theo dõi, không có các mức độ log (INFO, ERROR, WARN), khó kết hợp với các hệ thống phân tích log tập trung (Datadog, Loki).
5. **Thiếu Middleware CORS**: API sẽ không thể được gọi từ một Web Frontend chạy ở domain khác do trình duyệt sẽ block theo cơ chế bảo mật CORS.
6. **Không có Health/Ready Check endpoints**: Hệ thống Cloud hoặc Container Orchestrator không thể biết khi nào app đã sẵn sàng nhận request, hoặc khi nào app bị treo để restart.
7. **Thiếu Graceful Shutdown**: Không bắt tín hiệu tắt (SIGTERM), app sẽ dừng ngay lập tức khiến các request đang xử lý dở bị lỗi.
8. **Hardcode `host="localhost"`**: Chỉ nhận kết nối từ bên trong chính hệ điều hành đó. Nếu đóng gói vào Docker, app sẽ hoàn toàn bị cô lập khỏi thế giới bên ngoài (cần bind vào `0.0.0.0`).
9. **Hardcode `port=8000`**: Rất nhiều nền tảng Cloud (Railway, Render, Heroku) tự động cấp một port ngẫu nhiên thông qua biến môi trường `PORT`. Hardcode sẽ làm app không thể expose dịch vụ.
10. **Bật `reload=True`**: Tính năng hot-reload của uvicorn chỉ dùng để code. Dùng trên production sẽ gây tốn tài nguyên và có thể crash app nếu file bị thay đổi ngẫu nhiên.

### Exercise 1.3: So sánh với advanced version

| Feature | Basic | Advanced | Tại sao quan trọng? |
|---------|-------|----------|---------------------|
| **Cấu hình (Config)** | Hardcode trong file | Đọc từ biến môi trường theo 12-Factor | Tách biệt code và cấu hình. Giúp 1 image Docker có thể deploy lên nhiều môi trường mà không cần build lại. Bảo vệ thông tin nhạy cảm. |
| **Giao tiếp mạng (Host/Port)**| Bị gán cứng `localhost:8000` | Binding `0.0.0.0` và cổng động từ `$PORT` | Mở kết nối ra ngoài container (`0.0.0.0`). Tương thích với các Cloud platforms có cấp phát port ngẫu nhiên. |
| **Tắt ứng dụng (Shutdown)**| Đột ngột (kill) | Graceful Shutdown (Bắt tín hiệu `SIGTERM`) | Cho phép app từ chối request mới và xử lý xong các request hiện tại, đóng an toàn kết nối DB trước khi thoát, không gây downtime. |
| **Giám sát sức khoẻ (Health)**| Không có | Có `/health`, `/ready`, `/metrics` | Giúp Load Balancer điều phối traffic chuẩn xác và tự động restart nếu ứng dụng bị treo. |
| **Logging** | `print()` thuần, in ra secret | Structured JSON Logging, ẩn thông tin nhạy cảm | Log dạng JSON giúp hệ thống dễ dàng tự động parse, tìm kiếm và tạo dashboard giám sát. Tăng cường bảo mật. |
| **CORS Middleware** | Không có | Có khai báo middleware | Đảm bảo Frontend (React/Vue/Angular) ở domain khác có quyền truy cập API mà không bị lỗi trình duyệt. |

---

## Part 2: Docker Containerization

### Exercise 2.1: Dockerfile cơ bản
1. **Base image là gì?** `python:3.11`
2. **Working directory là gì?** `/app`
3. **Tại sao COPY requirements.txt trước?** Tận dụng Docker layer cache. Nếu requirements.txt không đổi, Docker sẽ không cần cài lại dependencies, giúp thời gian chạy giảm đáng kể tiw
4. **CMD vs ENTRYPOINT khác nhau thế nào?** `CMD` định nghĩa lệnh mặc định được chạy khi khởi tạo container, có thể bị ghi đè.

### Exercise 2.3: Multi-stage build
- **Stage 1 (Builder):** Cài đặt tất cả build dependencies (gcc, libpq-dev) và tải các packages qua pip.
- **Stage 2 (Runtime):** Chỉ sao chép mã nguồn và các built packages từ Stage 1, tạo một môi trường cực kì gọn nhẹ chỉ gồm Runtime.
- **Tại sao image nhỏ hơn?** Vì Stage 2 không chứa các file rác sinh ra trong quá trình build và các compilers/tools không cần thiết khi chạy ứng dụng.

---

## Part 3: Cloud Deployment

### Exercise 3.2: So sánh Render vs Railway
- `railway.toml`: Thường tập trung vào start command, build builder (nixpacks, docker) và các biến số.
- `render.yaml`: (Blueprint) Cấu hình định dạng declarative để triển khai Infrastructure as Code cho ứng dụng Render, định nghĩa env, branch, plan...

---

## Part 4: API Security

### Exercise 4.1: API Key authentication
- API key được check bằng header `X-API-Key`.
- Nếu sai key: Ứng dụng trả về lỗi 401 Unauthorized.
- Làm sao rotate key: Đổi biến môi trường chứa API Key và khởi động lại ứng dụng.

### Exercise 4.3: Rate limiting
- **Algorithm:** Phổ biến là Sliding Window hoặc Token Bucket lưu trong Redis.
- **Limit:** Ví dụ 10 requests/minute.
- **Bypass:** Kiểm tra quyền admin thông qua token hoặc role.

### Exercise 4.4: Cost guard (Solution)
```python
import redis
from datetime import datetime

r = redis.Redis(host='localhost', port=6379, db=0)

def check_budget(user_id: str, estimated_cost: float) -> bool:
    month_key = datetime.now().strftime("%Y-%m")
    key = f"budget:{user_id}:{month_key}"
    
    current = float(r.get(key) or 0)
    if current + estimated_cost > 10:
        return False
    
    r.incrbyfloat(key, estimated_cost)
    r.expire(key, 32 * 24 * 3600)
    return True
```

---

## Part 5: Scaling & Reliability

### Exercise 5.1: Health checks
```python
@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/ready")
def ready():
    try:
        r.ping()
        return {"status": "ready"}
    except:
        return JSONResponse(status_code=503, content={"status": "not ready"})
```

### Exercise 5.2 & 5.3 & 5.4: Stateful vs Stateless
- Stateless: State nên lưu ở bộ nhớ dùng chung như Redis, Database để các request từ cùng 1 user có thể được xử lý bởi bất kỳ instance nào (khi load balancing), và không mất đi khi 1 container bị tắt (Graceful shutdown).

---

## Part 6: Final Project

Source code cho Final Project (Production-ready AI Agent) đã được đặt trong thư mục `my-production-agent`.
