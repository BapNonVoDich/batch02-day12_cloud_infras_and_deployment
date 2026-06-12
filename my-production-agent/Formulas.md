
### 1. Công thức tính BMR: Phương trình Mifflin-St Jeor (1990)

Đoạn tính toán `bmr` trong code của bạn sử dụng chính xác **phương trình Mifflin-St Jeor**. Đây là công thức được công bố trên tạp chí *American Journal of Clinical Nutrition* vào năm 1990 bởi các nhà nghiên cứu MD Mifflin và ST St Jeor.

* **Nam giới:** $BMR = 10 \times \text{weight\_kg} + 6.25 \times \text{height\_cm} - 5 \times \text{age} + 5$
* **Nữ giới:** $BMR = 10 \times \text{weight\_kg} + 6.25 \times \text{height\_cm} - 5 \times \text{age} - 161$

Hiệp hội Dinh dưỡng Hoa Kỳ (ADA) đánh giá Mifflin-St Jeor là một trong những công thức tính BMR chính xác nhất cho lối sống hiện đại, có độ tin cậy cao hơn và sát thực tế hơn so với công thức Harris-Benedict (1919) cũ.

### 2. Hệ số hoạt động (TDEE Multipliers)

Các hệ số `1.2`, `1.375`, `1.55`, `1.725`, và `1.9` là **Hệ số Hoạt động Thể chất (PAL - Physical Activity Level)** tiêu chuẩn. Các hệ số này ban đầu được phát triển ứng dụng rộng rãi cùng phương trình Harris-Benedict, nhưng ngày nay đã trở thành quy chuẩn được Tổ chức Y tế Thế giới (WHO) và Tổ chức Lương thực và Nông nghiệp Liên Hợp Quốc (FAO) công nhận để nhân với BMR nhằm tính ra tổng năng lượng tiêu hao (TDEE).

### 3. Điều chỉnh Calo & Phân bổ Macro (Đa lượng)

Phần xử lý `goal` tuân theo **khuyến nghị chung của các tổ chức y tế và y học thể thao (như ACSM - American College of Sports Medicine)** chứ không nằm trong một nghiên cứu đơn lẻ:

* **Mức tăng/giảm calo:** Việc trừ đi `500` kcal để giảm cân (lose_weight) dựa trên nguyên lý thâm hụt $\sim 3500$ kcal mỗi tuần để giảm khoảng 0.45kg (1 pound) mỡ.
* **Mức calo sàn an toàn:** Đoạn code quy định mức tối thiểu là `1500` kcal cho nam và `1200` kcal cho nữ. Điều này tuân thủ chính xác khuyến nghị an toàn y tế cơ bản của Viện Y tế Quốc gia Hoa Kỳ (NIH) nhằm đảm bảo cơ thể không bị suy nhược và mất trao đổi chất khi ăn kiêng.
* **Tỷ lệ Macro:** Các tỷ lệ (ví dụ: `0.30/0.40/0.30` cho giảm cân, `0.35/0.40/0.25` cho tăng cơ) nằm hoàn toàn trong phạm vi an toàn **AMDR (Acceptable Macronutrient Distribution Ranges)** của Viện Hàn lâm Khoa học Quốc gia Hoa Kỳ. Chúng được tinh chỉnh theo các nghiên cứu khoa học thể hình thực chứng để tối ưu hóa việc tổng hợp protein cho cơ bắp hoặc duy trì cơ bắp trong quá trình thâm hụt calo.

Nhìn chung, hàm tính toán này được bạn thiết lập rất logic, sử dụng đúng những chuẩn mực y khoa uy tín và ổn định nhất để lập kế hoạch dinh dưỡng cá nhân.