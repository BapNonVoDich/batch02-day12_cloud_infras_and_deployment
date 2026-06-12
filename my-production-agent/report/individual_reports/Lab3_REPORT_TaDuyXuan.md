# Individual Report: Lab 3 - Chatbot vs ReAct Agent

- **Student Name**: Ta Duy Xuan
- **Student ID**: 2A202600970
- **Date**: 2026-06-01

---

## I. Technical Contribution (15 Points)

Trong lab này, phần đóng góp kỹ thuật chính của tôi là xây dựng hai tool phục vụ agent tư vấn dinh dưỡng: một tool tra cứu thông tin dinh dưỡng của món ăn và một tool đề xuất món ăn thay thế dựa trên mục tiêu dinh dưỡng.

- **Modules Implemented**:
  - `src/tools/dish_searcher.py`
  - `src/tools/alternative_suggester.py`

### 1. `search_dish_nutrition` - Tool tra cứu dinh dưỡng

Tool `search_dish_nutrition` cho phép agent tìm kiếm thông tin chi tiết về calo, protein, carb và fat của một hoặc nhiều món ăn từ cơ sở dữ liệu mock. Tool thực hiện tìm kiếm theo từ khóa (case-insensitive), giúp agent có dữ liệu chính xác để phân tích trước khi đưa ra lời khuyên.

Code highlight:

```python
matches = []
for m in meals:
    if query in m["name"].lower():
        matches.append(m)
```

Kết quả trả về là một danh sách các món ăn khớp với từ khóa dưới dạng JSON, giúp agent dễ dàng so sánh và tổng hợp thông tin.

### 2. `suggest_alternative` - Tool đề xuất món ăn thay thế

Tool `suggest_alternative` là một tool nâng cao giúp người dùng tối ưu hóa chế độ ăn. Nó nhận vào tên một món ăn và một tiêu chí macro cần tối ưu (ví dụ: giảm chất béo, giảm calo, hoặc tăng protein). 

Tool hoạt động theo cơ chế:
1. Tìm món ăn gốc trong database.
2. Lọc các món ăn khác thỏa mãn điều kiện (ví dụ: nếu muốn giảm fat, tìm các món có fat thấp hơn 70% món gốc).
3. Sắp xếp kết quả để đưa ra những lựa chọn tốt nhất.

Code highlight:

```python
if target_macro == "fat_g":
    if m["fat_g"] < original_dish["fat_g"] * 0.7:
        suggestions.append(m)
elif target_macro == "protein_g":
    if m["protein_g"] > original_dish["protein_g"]:
        suggestions.append(m)
```

Điều này giúp agent không chỉ trả lời "món này nhiều calo quá" mà có thể đưa ra giải pháp cụ thể: "Thay vì ăn món A, bạn có thể chọn món B để giảm 30% lượng chất béo mà vẫn đảm bảo dinh dưỡng."

### 3. Cách hai tool hỗ trợ ReAct loop

Hai tool này tạo ra một quy trình tư vấn thông minh trong vòng ReAct:

Ví dụ user hỏi: 
> "Tôi muốn ăn phở bò nhưng tôi đang trong chế độ giảm cân, có món nào thay thế ít calo hơn không?"

Agent sẽ xử lý theo trace:
```text
Thought: Cần kiểm tra lượng calo của phở bò và tìm món thay thế ít calo hơn.
Action: search_dish_nutrition("phở bò")
Observation: [{"name": "Phở Bò", "calories_kcal": 450, ...}]
Thought: Tìm món thay thế cho phở bò với tiêu chí giảm calories_kcal.
Action: suggest_alternative("phở bò", "calories_kcal")
Observation: [{"name": "Phở Gà", "calories_kcal": 320, ...}, ...]
Final Answer: Phở bò có khoảng 450 kcal. Để giảm cân, bạn có thể thay thế bằng Phở Gà (chỉ 320 kcal) hoặc các lựa chọn khác ít calo hơn.
```

---

## II. Debugging Case Study (10 Points)

### Problem Description

Khi triển khai `suggest_alternative`, tôi gặp vấn đề khi người dùng nhập tên món ăn không chính xác tuyệt đối (ví dụ: nhập "phở" thay vì "Phở Bò"). Ban đầu, tool chỉ tìm kiếm khớp chính xác, dẫn đến việc trả về lỗi "Không tìm thấy món ăn" dù trong database có nhiều món chứa từ "phở".

### Reproduction Trace

Lệnh kiểm tra:

```bash
python3 -c "from src.tools.alternative_suggester import suggest_alternative; print(suggest_alternative('phở', 'calories_kcal'))"
```

Kết quả ban đầu:
```json
{"error": "Không tìm thấy món ăn 'phở' trong dữ liệu để so sánh."}
```

### Diagnosis

Nguyên nhân là do sử dụng phép so sánh bằng `==` cho tên món ăn. Trong thực tế, người dùng thường nhập từ khóa ngắn gọn hoặc sai chính tả nhẹ, khiến tool quá cứng nhắc.

### Solution

Tôi đã cập nhật logic tìm kiếm món ăn gốc để hỗ trợ tìm kiếm tương đối (fuzzy search) đơn giản bằng cách kiểm tra xem từ khóa có nằm trong tên món ăn hay không (`if dish_name_clean in m["name"].lower()`). Nếu không tìm thấy khớp chính xác, tool sẽ lấy món ăn đầu tiên khớp với từ khóa để làm mốc so sánh.

Code cập nhật:

```python
if not original_dish:
    matches = [m for m in meals if dish_name_clean in m["name"].lower()]
    if matches:
        original_dish = matches[0]
```

### Lesson Learned

Trong agentic system, tool phải có khả năng chịu lỗi (fault-tolerant). Nếu tool trả về lỗi quá nhanh cho những sai sót nhỏ của người dùng, agent sẽ bị kẹt trong vòng lặp hoặc báo lỗi không cần thiết. Việc linh hoạt trong xử lý input giúp tăng tỷ lệ thành công của ReAct loop.

---

## III. Personal Insights: Chatbot vs ReAct (10 Points)

### 1. Reasoning

Chatbot thông thường chỉ có thể đưa ra lời khuyên chung chung dựa trên tập dữ liệu huấn luyện (ví dụ: "nên ăn nhiều rau hơn"). ReAct Agent với `dish_searcher` và `alternative_suggester` có khả năng lý luận dựa trên dữ liệu thực tế (grounded reasoning).

Khi user yêu cầu món thay thế, agent không "đoán" món nào ít calo hơn mà thực sự truy vấn database, so sánh con số cụ thể và đưa ra kết luận. Điều này loại bỏ hiện tượng hallucination (ảo giác) về thành phần dinh dưỡng của món ăn.

### 2. Reliability

Độ tin cậy của agent phụ thuộc hoàn toàn vào chất lượng của Tool và Observation. Nếu `dish_searcher` trả về kết quả sai, agent sẽ đưa ra lời khuyên sai. Tuy nhiên, so với chatbot, agent minh bạch hơn vì chúng ta có thể xem trace (Thought -> Action -> Observation) để biết agent đã dựa vào thông tin nào để kết luận.

### 3. Observation

Observation là "mắt" của agent. Với `suggest_alternative`, tôi thiết kế Observation trả về cả món ăn gốc và danh sách gợi ý kèm tin nhắn hướng dẫn. Điều này giúp agent hiểu rõ ngữ cảnh so sánh và có thể giải thích cho người dùng tại sao món ăn này lại được đề xuất (ví dụ: "vì nó có lượng protein cao hơn món A").

---

## IV. Future Improvements (5 Points)

- **Personalization**: Tích hợp `suggest_alternative` với dữ liệu user (từ `load_users`). Thay vì chỉ giảm calo nói chung, tool có thể đề xuất món ăn phù hợp với mục tiêu cụ thể của user (ví dụ: "Bạn đang muốn tăng cơ, tôi đề xuất món B thay cho món A vì có nhiều protein hơn").
- **Search Quality**: Sử dụng Vector Database (như ChromaDB hoặc FAISS) để tìm kiếm món ăn theo ngữ nghĩa (semantic search) thay vì chỉ tìm theo từ khóa, giúp tìm được các món tương đồng ngay cả khi tên gọi khác nhau.
- **Linguistic Flexibility**: Bổ sung hỗ trợ đa ngôn ngữ cho tên món ăn (ví dụ: tìm "beef noodle" cũng ra "phở bò").
- **Monitoring**: Log số lượng món ăn được lọc ra trong mỗi lần gọi `suggest_alternative` để đánh giá xem tiêu chí lọc (ví dụ: 70% calories) có quá khắt khe hay không.
- **Validation**: Thêm kiểm tra để đảm bảo danh sách gợi ý không chứa món ăn quá xa lạ với khẩu vị người dùng thông qua một hệ thống phân loại món ăn (category).

---

> [!NOTE]
> Submit this report by renaming it to `REPORT_[YOUR_NAME].md` and placing it in this folder.
