# Individual Report: Lab 3 - Chatbot vs ReAct Agent

- **Student Name**: [Your Name Here]
- **Student ID**: [Your ID Here]
- **Date**: 2026-06-01

---

## I. Technical Contribution (15 Points)

Trong lab này, phần đóng góp kỹ thuật chính của tôi là xây dựng hai tool phục vụ agent tư vấn dinh dưỡng: một tool tính nhu cầu năng lượng cá nhân và một tool đọc/ghi dữ liệu mock cho người dùng, món ăn, lịch sử chat.

- **Modules Implemented**:
  - `src/tools/tdee_calculator.py`
  - `src/tools/db.utils.py`

### 1. `calculate_tdee` - Tool tính BMR, TDEE và macro mục tiêu

Tool `calculate_tdee` nhận các thông tin cá nhân gồm cân nặng, chiều cao, tuổi, giới tính, mức độ vận động và mục tiêu. Sau đó tool tính:

- **BMR** theo công thức Mifflin-St Jeor.
- **TDEE** bằng cách nhân BMR với hệ số vận động.
- **Target calories** theo mục tiêu:
  - `lose_weight`: giảm 500 kcal nhưng không thấp hơn ngưỡng an toàn cơ bản.
  - `gain_weight`: tăng 400 kcal.
  - `build_muscle`: tăng 200 kcal.
- **Macro targets** gồm protein, carbohydrates và fat theo tỉ lệ phù hợp với từng mục tiêu.

Code highlight:

```python
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
```

Kết quả được trả về dưới dạng JSON string bằng `json.dumps(..., ensure_ascii=False)`, giúp agent dễ dùng kết quả trong vòng ReAct và vẫn giữ được nội dung tiếng Việt.

Ví dụ kiểm thử nhanh:

```bash
python3 -c "from src.tools.tdee_calculator import calculate_tdee; print(calculate_tdee(68,175,24,'Nam','moderate','build_muscle'))"
```

Kết quả chính:

```json
{
  "bmr": 1658,
  "tdee": 2571,
  "target_calories": 2771,
  "target_protein_g": 242,
  "target_carbs_g": 277,
  "target_fat_g": 76
}
```

### 2. `db.utils` - Tool tiện ích dữ liệu mock

Module `db.utils.py` chịu trách nhiệm làm lớp truy cập dữ liệu cục bộ cho agent:

- `load_meals()`: đọc danh sách món ăn từ `mock-data/MealMockData.Json`.
- `load_users()`: đọc danh sách người dùng từ `mock-data/MockUser.json`.
- `get_user_with_targets(user)`: tự tính target calories/macro nếu dữ liệu user chưa có sẵn các field mục tiêu.
- `save_users(users)`: lưu user trở lại file mock, đồng thời bỏ các target được tính động để file mock sạch hơn.
- `load_chat_history(user_id)` và `save_chat_history(user_id, messages)`: đọc/ghi lịch sử hội thoại theo user.

Điểm quan trọng của module này là dữ liệu user không cần lưu sẵn `target_calories`, `target_protein_g`, `target_carbs_g`, `target_fat_g`. Khi agent load user, hàm `get_user_with_targets` sẽ tính động các trường này từ thông tin cơ bản của user. Điều này giúp tránh dữ liệu bị lệch nếu cân nặng, chiều cao, tuổi hoặc mục tiêu thay đổi.

Code highlight:

```python
if (user.get("target_calories") is not None and
    user.get("target_protein_g") is not None and
    user.get("target_carbs_g") is not None and
    user.get("target_fat_g") is not None):
    return user
```

### 3. Cách hai tool hỗ trợ ReAct loop

Trong mô hình ReAct, LLM không chỉ trả lời trực tiếp mà phải chọn tool, gọi tool, đọc `Observation`, rồi mới kết luận. Hai tool này tạo ra workflow tự nhiên cho các câu hỏi dinh dưỡng nhiều bước.

Ví dụ user hỏi:

> Tôi là nam, 24 tuổi, 68kg, cao 175cm, tập vừa phải và muốn tăng cơ. Mỗi ngày tôi nên ăn bao nhiêu kcal và macro như thế nào?

Agent có thể xử lý theo trace:

```text
Thought: Cần tính nhu cầu năng lượng và macro mục tiêu từ thông tin cá nhân.
Action: calculate_tdee(68, 175, 24, "Nam", "moderate", "build_muscle")
Observation: {"bmr": 1658, "tdee": 2571, "target_calories": 2771, ...}
Final Answer: Bạn nên nạp khoảng 2771 kcal/ngày, gồm 242g protein, 277g carbs và 76g fat.
```

Với câu hỏi liên quan đến dữ liệu có sẵn, agent có thể gọi `load_users()` để lấy hồ sơ user, gọi `load_meals()` để tham khảo món ăn, rồi dùng kết quả target calories/macro để đưa ra gợi ý phù hợp.

---

## II. Debugging Case Study (10 Points)

### Problem Description

Khi kiểm tra module `db.utils.py`, tôi phát hiện các hàm `load_meals()` và `load_users()` trả về danh sách rỗng dù trong repo đã có dữ liệu ở `mock-data/MealMockData.Json` và `mock-data/MockUser.json`.

### Reproduction Trace

Lệnh kiểm tra:

```bash
python3 -c "import importlib.util; spec=importlib.util.spec_from_file_location('db_utils','src/tools/db.utils.py'); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); print(m.BASE_DIR); print(m.MEALS_FILE); print(len(m.load_meals())); print(len(m.load_users()))"
```

Kết quả:

```text
/media/le-duy-hung/code/lab333/ai-product-lab-Chatbot-vs-react-agent/src
/media/le-duy-hung/code/lab333/ai-product-lab-Chatbot-vs-react-agent/src/mock-data/MealMockData.Json
0
0
```

### Diagnosis

Nguyên nhân là biến `BASE_DIR` trong `db.utils.py` đang được tính bằng:

```python
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
```

Với file nằm ở `src/tools/db.utils.py`, biểu thức trên chỉ đi lên đến thư mục `src`. Vì vậy tool tìm dữ liệu ở `src/mock-data/...`, trong khi dữ liệu thật nằm ở project root: `mock-data/...`.

Đây là một lỗi môi trường/tooling, không phải lỗi reasoning của LLM. Nếu dùng trong ReAct loop, agent sẽ nhận `Observation: []` và có thể kết luận sai rằng hệ thống không có dữ liệu user hoặc món ăn.

### Solution

Cách xử lý là tính project root bằng cách đi lên thêm một cấp, hoặc dùng `pathlib` để code rõ hơn:

```python
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
MEALS_FILE = BASE_DIR / "mock-data" / "MealMockData.Json"
USERS_FILE = BASE_DIR / "mock-data" / "MockUser.json"
```

Sau khi sửa, cần kiểm tra lại:

- `load_meals()` trả về số lượng món ăn lớn hơn 0.
- `load_users()` trả về 3 mock users.
- User được load có thêm các field target calories/macro được tính động.

### Lesson Learned

Trong agentic system, một tool trả về kết quả rỗng có thể làm LLM suy luận sai ở các bước sau. Vì vậy cần log rõ đường dẫn file, số lượng record đọc được và lỗi I/O nếu có. Observation càng rõ thì vòng `Thought -> Action -> Observation` càng đáng tin cậy.

---

## III. Personal Insights: Chatbot vs ReAct (10 Points)

### 1. Reasoning

Chatbot thường trả lời dựa trên kiến thức nội tại của model, nên với bài toán tính TDEE/macro, chatbot có thể nói đúng về mặt khái niệm nhưng dễ sai số hoặc quên một bước tính. ReAct Agent tốt hơn vì ép model tách quá trình thành hai phần: suy nghĩ cần làm gì và gọi tool để lấy kết quả chính xác.

Với tool `calculate_tdee`, phần tính toán được đưa ra khỏi LLM và chuyển sang code Python. LLM chỉ cần hiểu khi nào nên gọi tool và diễn giải kết quả cho người dùng. Điều này làm câu trả lời ổn định hơn.

### 2. Reliability

Agent không phải lúc nào cũng tốt hơn chatbot. Agent có thể tệ hơn trong các trường hợp:

- Tool description không rõ, làm LLM chọn sai tool hoặc truyền sai argument.
- Tool trả về lỗi/rỗng nhưng Observation không đủ thông tin để agent tự phục hồi.
- Câu hỏi rất đơn giản, không cần tool, nhưng agent vẫn gọi tool làm tăng latency.
- Parser của Action quá cứng, khiến output hơi khác format là không gọi được tool.

Trong lab này, lỗi đường dẫn của `db.utils.py` là ví dụ rõ: chatbot vẫn có thể trả lời chung chung, còn agent phụ thuộc vào tool nên sẽ bị ảnh hưởng trực tiếp nếu tool không đọc được dữ liệu.

### 3. Observation

Observation là phần giúp agent tự điều chỉnh bước tiếp theo. Nếu Observation chứa JSON rõ ràng như kết quả của `calculate_tdee`, agent có thể chuyển nó thành lời khuyên dinh dưỡng cụ thể. Ngược lại, nếu Observation chỉ là `[]` hoặc `"Error"`, agent rất khó biết nên thử lại, đổi tool hay báo lỗi cho người dùng.

Vì vậy, tool nên trả về kết quả có cấu trúc và thông báo lỗi có ngữ cảnh, ví dụ:

```json
{
  "error": "MEALS_FILE_NOT_FOUND",
  "path": ".../mock-data/MealMockData.Json"
}
```

---

## IV. Future Improvements (5 Points)

- **Scalability**: Tách `db.utils.py` thành các module rõ hơn như `user_repository.py`, `meal_repository.py`, `chat_history_repository.py`; sau đó thay mock JSON bằng SQLite hoặc PostgreSQL khi dữ liệu lớn hơn.
- **Safety**: Thêm validation cho input của `calculate_tdee`, ví dụ không nhận tuổi âm, chiều cao/cân nặng bằng 0 hoặc goal ngoài danh sách cho phép.
- **Reliability**: Chuẩn hóa output của mọi tool theo format `{ "ok": true/false, "data": ..., "error": ... }` để ReAct loop dễ xử lý lỗi.
- **Performance**: Cache danh sách món ăn trong memory thay vì đọc JSON file ở mỗi lần gọi tool.
- **Agent Quality**: Bổ sung few-shot examples trong system prompt để LLM biết chính xác khi nào gọi `calculate_tdee`, khi nào đọc user bằng `load_users`, và khi nào trả lời trực tiếp.
- **Monitoring**: Log số lần gọi tool, thời gian đọc file, số record trả về và lỗi parse JSON để phục vụ phân tích failure trace.

---

> [!NOTE]
> Submit this report by renaming it to `REPORT_[YOUR_NAME].md` and placing it in this folder.
