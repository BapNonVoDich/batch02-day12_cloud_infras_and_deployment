# Hướng dẫn Khởi chạy Dự án (Onboarding Guide)

Chào mừng bạn đến với dự án **AI Nutrition Planner & Advisory Agent**! Đây là tài liệu hướng dẫn chi tiết các bước chuẩn bị và khởi chạy dự án sau khi bạn vừa pull source code về.

---

## 🛠️ Bước 1: Thiết lập Môi trường Backend (Python)

Backend của dự án được xây dựng bằng **FastAPI** và chạy trên môi trường Python.

1. **Di chuyển vào thư mục gốc của dự án** (thư mục chứa [requirements.txt](file:///e:/Work/VIN%20AI/Gr%20D3/ai-product-lab-Chatbot-vs-react-agent/requirements.txt)).
2. **Khởi tạo và kích hoạt Môi trường ảo (Virtual Environment)**:
   * **Trên Windows**:
     * *PowerShell:*
       ```powershell
       python -m venv .venv
       .venv\Scripts\Activate.ps1
       ```
     * *Command Prompt (cmd):*
       ```cmd
       python -m venv .venv
       .venv\Scripts\activate.bat
       ```
   * **Trên Linux / macOS**:
     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     ```
3. **Cài đặt các thư viện phụ thuộc (Dependencies)**:
   ```bash
   pip install -r requirements.txt
   ```
4. **Thiết lập Biến môi trường (.env)**:
   * Sao chép file [.env.example](file:///e:/Work/VIN%20AI/Gr%20D3/ai-product-lab-Chatbot-vs-react-agent/.env.example) thành `.env`:
     ```bash
     cp .env.example .env
     ```
   * Mở file [.env](file:///e:/Work/VIN%20AI/Gr%20D3/ai-product-lab-Chatbot-vs-react-agent/.env) và điền khóa API của bạn vào biến `GEMINI_API_KEY`:
     ```env
     GEMINI_API_KEY=your_actual_gemini_api_key_here
     ```

---

## 💻 Bước 2: Thiết lập Môi trường Frontend (React + Vite)

Frontend của dự án sử dụng **React (Vite)** và yêu cầu môi trường **Node.js** (đã cài đặt sẵn NPM).

1. **Di chuyển vào thư mục `frontend`**:
   ```bash
   cd frontend
   ```
2. **Cài đặt các gói phụ thuộc (Packages)**:
   ```bash
   npm install
   ```

---

## 🚀 Bước 3: Chạy dự án (Run Application)

Bạn cần mở **2 cửa sổ Terminal song song** để chạy đồng thời Backend và Frontend.

### 1. Khởi chạy Backend Server
Tại thư mục gốc dự án (đã kích hoạt môi trường ảo `.venv`), chạy lệnh:
```bash
python -m src.server
```
> Server API sẽ chạy tại: **`http://127.0.0.1:8000`**

### 2. Khởi chạy Frontend Dev Server
Tại thư mục `frontend/`, chạy lệnh:
```bash
npm run dev
```
> Giao diện người dùng sẽ chạy tại: **`http://localhost:5173`** (Mở liên kết này trên trình duyệt để sử dụng).

---

## 📁 Cấu trúc Dự án quan trọng
* [src/server.py](file:///e:/Work/VIN%20AI/Gr%20D3/ai-product-lab-Chatbot-vs-react-agent/src/server.py): Điểm khởi chạy của FastAPI Backend.
* [src/agent/agent.py](file:///e:/Work/VIN%20AI/Gr%20D3/ai-product-lab-Chatbot-vs-react-agent/src/agent/agent.py): Chứa logic ReAct Agent xử lý suy nghĩ (Thought) và gọi công cụ (Action).
* [frontend/src/App.jsx](file:///e:/Work/VIN%20AI/Gr%20D3/ai-product-lab-Chatbot-vs-react-agent/frontend/src/App.jsx): Giao diện người dùng React chính tích hợp Dashboard theo dõi và Console Chatbot.
* [mock-data/](file:///e:/Work/VIN%20AI/Gr%20D3/ai-product-lab-Chatbot-vs-react-agent/mock-data): Thư mục chứa cơ sở dữ liệu giả lập về người dùng ([MockUser.json](file:///e:/Work/VIN%20AI/Gr%20D3/ai-product-lab-Chatbot-vs-react-agent/mock-data/MockUser.json)), món ăn và lịch sử trò chuyện.
