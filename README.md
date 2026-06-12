# Báo Cáo Hoàn Thành: Part 6 - Production-ready AI Nutrition Agent

Đây là repository báo cáo kết quả thực hành bài **Lab 6: Localhost vs. Production (12-Factor App & Containerization)** của môn học Cloud Infrastructure & Deployment.

## Mục tiêu
Chuyển đổi một ứng dụng AI Nutrition Agent (hoạt động ở Localhost, lưu state file JSON, thiết kế Monolithic) thành một **hệ thống đạt chuẩn Production** theo nguyên lý **12-Factor App**.

## Các tiêu chuẩn Production đã triển khai thành công:

### 1. Stateless Architecture (Redis)
- **Vấn đề cũ**: Ứng dụng `old-pj` lưu trữ thông tin User và Chat History trực tiếp vào file JSON trên ổ cứng (`MockUser.json`, `ChatHistory.json`), gây ra lỗi mất tính đồng nhất khi scale ra nhiều container, khó load balancing.
- **Giải pháp**: Xây dựng lại `tools/db_utils.py` để kết nối và lưu trữ toàn bộ Application State vào **Redis**. Ứng dụng giờ đây trở thành Stateless hoàn toàn và có thể scale ra nhiều Replica.

### 2. Configuration & Secrets Management
- Thay thế hoàn toàn cách đọc `os.getenv` thủ công bằng module `pydantic-settings` tại `src/config.py`.
- Tập trung quản lý toàn bộ cấu hình: `PORT`, `REDIS_URL`, `GEMINI_API_KEY`, `AGENT_API_KEY`.

### 3. API Security & Reliability
- **Xác thực API Key**: Thêm cơ chế Auth Header (`X-API-Key`) bảo mật toàn bộ các Endpoint nhạy cảm.
- **Rate Limiting**: Giới hạn tấn công DDoS và Spam bằng cách lưu bộ đếm số request trên Redis (Giới hạn 10 request/phút).
- **Cost Guard**: Tính toán chi phí gọi LLM Gemini và block request nếu người dùng xài quá ngân sách trong tháng (Tracking qua Redis).
- Triển khai thông qua `FastAPI Depends()`.

### 4. Health Check & Observability
- Thêm Endpoint `/health` (Tính toán Uptime, báo hiệu Container sống/chết).
- Thêm Endpoint `/ready` (Ping thử kết nối Redis để đảm bảo ứng dụng đã có khả năng nhận request từ Load Balancer).
- Thay thế Print thông thường bằng hệ thống JSON Logging chuẩn hóa (xuất theo định dạng `{"time": "...", "level": "INFO", "msg": "..."}`).

### 5. Graceful Shutdown
- Tích hợp hàm bắt tín hiệu kết thúc từ Hệ điều hành/Docker (`signal.SIGTERM`).
- Tích hợp Context Manager (`lifespan`) của FastAPI để đóng an toàn các kết nối Data (sleep 1s để hoàn thành nốt request đang dang dở) trước khi thoát chương trình.

### 6. Containerization (Multi-stage Build & Docker Compose)
- Viết `Dockerfile` Multi-stage tách biệt hoàn toàn môi trường build (Cài đặt gcc, g++, build lib) và môi trường Runtime (Chỉ chứa bytecode). Giúp tối ưu hóa dung lượng image và bảo mật.
- Đóng gói toàn bộ Stack thông qua `docker-compose.yml` gồm:
  - **Nginx**: Cấu hình Reverse Proxy làm Load balancer.
  - **Redis**: Database phân tán lưu trữ State.
  - **Agent API**: Backend logic.
  - **Frontend Vite**: Giao diện Web được build và serve trên Nginx port 3000.

## Cấu trúc thư mục hiện tại (`my-production-agent`)
```
my-production-agent/
├── docker-compose.yml
├── Dockerfile (Backend Multi-stage)
├── nginx.conf (Nginx Reverse Proxy)
├── .env.example
├── requirements.txt
├── src/
│   ├── server.py (FastAPI, Middlewares, Routes)
│   ├── config.py (Pydantic Settings)
│   ├── auth.py (API Key Auth)
│   ├── rate_limiter.py (Redis Counter)
│   ├── cost_guard.py (Redis Budgeting)
│   └── agent/ (ReAct Agent Logic)
├── tools/
│   └── db_utils.py (Redis Stateful Storage)
└── frontend/
    ├── Dockerfile (Frontend Multi-stage)
    └── src/ (React + Vite)
```

## Hướng dẫn chạy

Chỉ với 1 lệnh duy nhất để đưa toàn bộ cụm hệ thống lên Production:

```bash
cd my-production-agent
docker compose up --build -d
```

- **Frontend**: Truy cập [http://localhost:3000](http://localhost:3000)
- **Nginx Backend Proxy**: [http://localhost/](http://localhost/)
- **Health Check**: [http://localhost/health](http://localhost/health)

---
*Báo cáo được tự động tạo và biên soạn trong môi trường Lab.*
