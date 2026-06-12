# Individual Report: Lab 3 - Chatbot vs ReAct Agent

- **Student Name**: Phạm Ngọc Vinh
- **Student ID**: 2A202600563
- **Date**: 01/06/2026

---

## I. Technical Contribution (15 Points)

*Đóng góp kỹ thuật cụ thể của tôi trong dự án này tập trung vào thiết kế và triển khai hai công cụ hỗ trợ thông tin dinh dưỡng cốt lõi của Agent: tìm kiếm món ăn và đề xuất món ăn thay thế lành mạnh hơn.*

- **Modules Implemented**:
  - `src/tools/dish_searcher.py`: Triển khai công cụ `search_dish_nutrition` cho phép tìm kiếm linh hoạt tên món ăn trong cơ sở dữ liệu (sử dụng đối sánh chuỗi không phân biệt hoa thường). Kết quả trả về dữ liệu dinh dưỡng chi tiết dưới dạng JSON gồm calories, carbohydrates, protein và fat.
  - `src/tools/alternative_suggester.py`: Triển khai công cụ `suggest_alternative` nhằm tự động hóa việc so sánh dinh dưỡng đa lượng (macros) giữa món ăn gốc và các lựa chọn thay thế trong DB. Hỗ trợ lọc tối ưu theo từng mục tiêu riêng biệt như giảm calo (dưới 75% calo gốc), giảm fat/carb (dưới 70% lượng gốc) hoặc tăng protein (lượng protein lớn hơn món gốc).

- **Code Highlights**:
  - **Hàm tra cứu dinh dưỡng trong `dish_searcher.py`**:
    ```python
    def search_dish_nutrition(dish_name: str) -> str:
        try:
            meals = load_meals()
            query = dish_name.strip().lower()
            
            matches = []
            for m in meals:
                if query in m["name"].lower():
                    matches.append(m)
                    
            if not matches:
                return json.dumps({"message": f"Không tìm thấy thông tin dinh dưỡng cho món '{dish_name}' in database."}, ensure_ascii=False)
                
            return json.dumps(matches, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": f"Lỗi tra cứu món ăn: {str(e)}"}, ensure_ascii=False)
    ```
  - **Logic lọc và phân loại món ăn thay thế trong `alternative_suggester.py`**:
    ```python
    # Cơ chế lọc tối ưu dựa trên chỉ số dinh dưỡng đa lượng mục tiêu (target_macro)
    for m in meals:
        if m["id"] == original_dish["id"]:
            continue
        
        if target_macro == "fat_g":
            if m["fat_g"] < original_dish["fat_g"] * 0.7:
                suggestions.append(m)
        elif target_macro == "calories_kcal":
            if m["calories_kcal"] < original_dish["calories_kcal"] * 0.75:
                suggestions.append(m)
        elif target_macro == "carbohydrates_g":
            if m["carbohydrates_g"] < original_dish["carbohydrates_g"] * 0.7:
                suggestions.append(m)
        elif target_macro == "protein_g":
            if m["protein_g"] > original_dish["protein_g"]:
                suggestions.append(m)
        else:
            if m["calories_kcal"] < original_dish["calories_kcal"]:
                suggestions.append(m)
    ```

- **Documentation**:
  - **Cơ chế tương tác với vòng lặp ReAct**: 
    Khi Agent nhận yêu cầu từ người dùng (ví dụ: *"Tìm món thay thế cho bánh mì thịt ít béo hơn"*), mô hình ngôn ngữ (LLM) sẽ tiến hành phân tích qua khối lệnh `Thought` và xác định cần dùng công cụ nào. LLM sẽ tạo ra chuỗi hành động chuẩn `Action: suggest_alternative({"dish_name": "bánh mì thịt", "target_macro": "fat_g"})`. 
    Trình điều phối Agent (`ReActAgent._execute_tool` trong `src/agent/agent.py`) sẽ gọi hàm tương ứng. Đầu ra JSON dạng chuỗi của công cụ được nạp lại vào context của LLM dưới khóa `Observation:`. Qua đó, LLM có dữ liệu dinh dưỡng thực tế để tiếp tục lập luận và đưa ra lời khuyên khoa học, tránh hiện tượng ảo tưởng thông tin (hallucination).

---

## II. Debugging Case Study (10 Points)

*Quá trình phát triển hệ thống Agent không tránh khỏi các lỗi liên quan đến việc LLM sinh đối số không khớp với đặc tả kỹ thuật của công cụ.*

- **Problem Description**: 
  Trong quá trình chạy thử nghiệm, Agent đôi khi rơi vào trạng thái gọi lại công cụ liên tục hoặc xử lý sai mục tiêu dinh dưỡng khi nhận các yêu cầu tìm món ăn thay thế. Nguyên nhân là do LLM tự ý rút ngắn tham số `target_macro` thành `"fat"` thay vì truyền chính xác `"fat_g"` hoặc `"carb"` thay vì `"carbohydrates_g"`. Do tham số truyền vào không khớp với các điều kiện so sánh chuỗi nghiêm ngặt trong `suggest_alternative`, hàm đã nhảy vào nhánh `else` mặc định (so sánh calories) dẫn đến việc gợi ý món ăn có ít calories hơn thay vì ít chất béo/carbs như yêu cầu thực tế của người dùng.

- **Log Source**: 
  Trích đoạn ghi nhận lỗi trong file log hệ thống `logs/2026-06-01.log`:
  ```json
  {"timestamp": "2026-06-01T09:40:12.421Z", "event": "LLM_CALL", "data": {"step": 2, "response": "Thought: Người dùng muốn tìm một món ăn thay thế ít chất béo hơn cho Phở bò. Tôi sẽ sử dụng công cụ suggest_alternative để tìm các lựa chọn thay thế.\nAction: suggest_alternative({\"dish_name\": \"Phở bò\", \"target_macro\": \"fat\"})"}}
  {"timestamp": "2026-06-01T09:40:12.602Z", "event": "LLM_CALL", "data": {"step": 3, "response": "Thought: Dữ liệu trả về chỉ ra các món ít calo thay vì ít béo, do tham số 'fat' không khớp đúng định dạng 'fat_g'. Tôi phải gọi lại.\nAction: suggest_alternative({\"dish_name\": \"Phở bò\", \"target_macro\": \"fat\"})"}}
  ```

- **Diagnosis**: 
  - **Lỗi cú pháp tham số**: Mặc dù phần mô tả công cụ (Tool Description) đã ghi rõ định dạng đối số gồm `'calories_kcal'`, `'fat_g'`, `'carbohydrates_g'`, `'protein_g'`, LLM đôi khi vẫn áp dụng tư duy ngôn ngữ tự nhiên để tối giản hóa từ ngữ (sinh ra `"fat"`, `"carb"`), dẫn đến mismatch khi so sánh chuỗi bằng toán tử `==` trong Python.
  - **Hậu quả**: Logic điều phối hoạt động bình thường nhưng kết quả trả về không chính xác so với mục tiêu người dùng yêu cầu, buộc LLM phải lặp lại suy nghĩ (Thought) hoặc đưa ra câu trả lời cuối cùng không chuẩn xác.

- **Solution**: 
  1. **Nâng cấp tính mềm dẻo của công cụ**: Cập nhật hàm `suggest_alternative` để hỗ trợ chuẩn hóa tham số đầu vào một cách thông minh:
     ```python
     # Chuẩn hóa target_macro đầu vào
     target_macro = target_macro.strip().lower()
     macro_mapping = {
         "fat": "fat_g", "lipids": "fat_g", "chất béo": "fat_g",
         "carb": "carbohydrates_g", "carbs": "carbohydrates_g", "tinh bột": "carbohydrates_g",
         "protein": "protein_g", "đạm": "protein_g",
         "calo": "calories_kcal", "calories": "calories_kcal", "năng lượng": "calories_kcal"
     }
     target_macro = macro_mapping.get(target_macro, target_macro)
     ```
  2. **Tối ưu hóa System Prompt**: Điều chỉnh phần mô tả công cụ `suggest_alternative` trong `src/agent/agent.py` để nhấn mạnh tính nghiêm ngặt của giá trị đối số và đưa ra ví dụ gọi hàm chuẩn xác để LLM noi theo.

---

## III. Personal Insights: Chatbot vs ReAct (10 Points)

*Việc phát triển và kiểm nghiệm hệ thống Agent dinh dưỡng này mang lại nhiều nhận thức sâu sắc về sự khác biệt giữa Chatbot thông thường và ReAct Agent.*

1. **Reasoning**: Khối lệnh `Thought` hoạt động tương tự cơ chế Chain-of-Thought, cung cấp cho mô hình khả năng "suy ngẫm" trước khi hành động. So với Chatbot thông thường (chỉ có thể đưa ra câu trả lời dựa trên phỏng đoán và xác suất từ ngữ), `Thought` cho phép Agent tự lập luận để giải quyết các bài toán phức tạp (như tính TDEE, sau đó tra cứu nhật ký và so sánh dinh dưỡng) theo các bước logic tuần tự, đưa ra phương án thu thập thông tin hợp lý nhất.
2. **Reliability**: ReAct Agent hoạt động kém hiệu quả hơn Chatbot thông thường khi xử lý các yêu cầu cực kỳ đơn giản (như chào hỏi, hỏi thông tin chung không liên quan đến dinh dưỡng). Với những tác vụ này, việc ép Agent đi qua vòng lặp Thought-Action sẽ làm tăng thời gian phản hồi (latency), tiêu tốn lượng token LLM không cần thiết và có nguy cơ lỗi định dạng phân tích cú pháp (parsing error) hoặc rơi vào các vòng lặp vô hạn ngoài ý muốn.
3. **Observation**: Phản hồi từ môi trường (`Observation`) là nguồn thông tin thực tế vô cùng quan trọng giúp Agent tự điều chỉnh hướng suy luận. Nếu một công cụ trả về lỗi hoặc không có dữ liệu (ví dụ: món ăn không có trong DB), khối `Observation` tiếp theo sẽ là bằng chứng thực tế buộc Agent phải thay đổi chiến lược trong `Thought` tiếp theo (ví dụ: đề xuất một món ăn tương tự hoặc hướng dẫn người dùng nhập lại) thay vì tự ảo tưởng ra số liệu dinh dưỡng không chính xác.

---

## IV. Future Improvements (5 Points)

*Để phát triển hệ thống Agent này đạt tiêu chuẩn vận hành thực tế trong doanh nghiệp (production-level), cần triển khai các cải tiến sau:*

- **Scalability**: Triển khai cơ chế hàng đợi công việc bất đồng bộ (Asynchronous Task Queue sử dụng Celery kết hợp Redis) để quản lý các tác vụ gọi API bên ngoài hoặc các tính toán nặng, ngăn ngừa việc nghẽn luồng xử lý chính của người dùng và đảm bảo phục vụ hàng ngàn yêu cầu đồng thời.
- **Safety**: Thiết lập một lớp bảo vệ trung gian (LLM Guardrails / Supervisor Node) để kiểm tra tính hợp lệ và an toàn của dữ liệu đầu vào trước khi gọi công cụ ghi nhận (`log_meal`) nhằm ngăn chặn việc chèn mã độc (injection) hoặc giả mạo nhật ký dinh dưỡng, đồng thời kiểm duyệt y khoa đối với câu trả lời Final Answer trước khi hiển thị cho người dùng.
- **Performance**: Chuyển đổi dữ liệu món ăn sang cơ sở dữ liệu Vector (Vector Database) kết hợp tìm kiếm ngữ nghĩa (Semantic Search) để nâng cao tốc độ tra cứu món ăn khi quy mô DB phình to. Bên cạnh đó, áp dụng kỹ thuật RAG và Tool Retrieval để chỉ nạp các mô tả công cụ cần thiết vào context window của LLM, giúp tiết kiệm tài nguyên và nâng cao độ chính xác của phản hồi.
