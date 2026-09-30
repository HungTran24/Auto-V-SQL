# KẾ HOẠCH THỰC NGHIỆM: TÁI HIỆN V-SQL VÀ ĐỀ XUẤT AUTO-V-SQL TRÊN BIRD BENCHMARK

**Môn học:** Hệ cơ sở dữ liệu tiên tiến  
**Mục tiêu:**  
1. Tái hiện và kiểm chứng phương pháp của bài báo *V-SQL: A View-based Two-stage Text-to-SQL Framework (2024)*.  
2. Khắc phục hạn chế cốt tử của bài báo gốc (tác giả tự tay viết View nhìn trước đáp án) bằng module **Auto-View Generation** (tự động phân tích đồ thị khóa ngoại SQLite).  
3. Đánh giá đối chứng công bằng trên cùng một mô hình ngôn ngữ thế hệ mới (`gemini-3.5-flash-lite`).

---

## 1. Lựa chọn Dataset: BIRD vs Spider 2.0

| Tiêu chí | Spider 2.0 (ICLR 2025) | BIRD Benchmark (Paper V-SQL sử dụng) | Lựa chọn tối ưu cho đồ án |
| :--- | :--- | :--- | :--- |
| **Môi trường thực thi** | Yêu cầu Cloud Data Warehouses (Snowflake, BigQuery), Docker, DBT projects phức tạp. | 100% CSDL cục bộ bằng file SQLite (`.sqlite`), gọn nhẹ, độc lập. | **BIRD** (khả thi, không phụ thuộc cloud credit) |
| **Bản chất tác vụ** | Text-to-Data-Workflow (viết code Python, biến đổi dữ liệu, >100 dòng code). | Text-to-SQL thuần túy trên CSDL quan hệ nhiều bảng chuẩn hóa. | **BIRD** (đúng trọng tâm môn CSDL) |
| **Độ khớp với Paper gốc** | Khác biệt hoàn toàn về định dạng và bài toán. | **Khớp 1:1** với bài báo V-SQL (tác giả test trên mini-dev 11 CSDL của BIRD). | **BIRD** (đảm bảo tính hợp lệ khi tái hiện) |
| **Khả năng kiểm soát** | SOTA hiện tại (o1, Sonnet) chỉ giải được 15–20%, quá nhiều yếu tố nhiễu. | Metric Execution Accuracy (EX) rõ ràng, phân tích được lỗi cụ thể. | **BIRD** |

> **Quyết định:** Sử dụng **BIRD Benchmark** (tập trung vào các database quan hệ phức tạp, tiêu biểu là `superhero`, `financial`, v.v. như trong bài báo).

---

## 2. Thiết lập Hệ thống & Mô hình thử nghiệm

* **LLM Engine:** `gemini-3.5-flash-lite`
* **API Gateway / Proxy:** Local CPA Proxy (`http://localhost:8317/v1/chat/completions`)
* **Tham số suy luận (Bám sát Section 5.1 của Paper):**
  * `temperature`: 0.0 (đảm bảo tính tái lập)
  * `top_p`: 1.0
  * `max_tokens`: 800
* **Nguyên tắc so sánh:** Giữ cố định model `gemini-3.5-flash-lite` và cùng bộ test set cho tất cả các phương pháp. Mọi sự chênh lệch về điểm số chỉ đến từ **hiệu quả của phương pháp xử lý schema**, không bị nhiễu bởi năng lực model.

---

## 3. Ma trận các Phương pháp Thực nghiệm (Experimental Matrix)

Hệ thống sẽ chạy và so sánh 4 cấu hình:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        CÂU HỎI NGƯỜI DÙNG                              │
└────────────────────────────────────────────────────────────────────────┘
          │                 │                    │                  │
          ▼                 ▼                    ▼                  ▼
   [BASELINE 1]      [BASELINE 2]          [V-SQL GỐC]        [AUTO-V-SQL]
   Direct 1-Stage    Schema Linking        Paper Replicate     (Đóng góp mới)
   Raw Schema D      Lọc bảng liên quan    View viết tay       Auto-View Generator
          │                 │                    │                  │
          │                 │            [Stage 1: Dummy]   [Stage 1: Dummy]
          │                 │                    │                  │
          │                 │            [Stage 2: Recon]   [Stage 2: Recon]
          ▼                 ▼                    ▼                  ▼
      Final SQL         Final SQL            Final SQL          Final SQL
          │                 │                    │                  │
          └─────────────────┴────────────────────┴──────────────────┘
                                    │
                                    ▼
                 [ SQLite Database Engine: Chạy thực tế ]
                                    │
                                    ▼
       [ So sánh kết quả với Gold SQL -> Execution Accuracy (EX) ]
```

### Chi tiết 4 cấu hình:
1. **Config 1: Direct Zero-shot (Baseline 1)**
   * Input: Toàn bộ DDL schema thô của các bảng + Câu hỏi.
   * Model sinh trực tiếp Final SQL trong 1 lượt prompt.
2. **Config 2: Schema Linking + Synthesis (Baseline 2)**
   * Stage 1: Cho LLM đọc câu hỏi và chọn ra các bảng thực sự cần thiết.
   * Stage 2: Đưa schema các bảng đã chọn để sinh Final SQL.
3. **Config 3: V-SQL Replicated (Paper Original)**
   * Sử dụng các câu lệnh `CREATE VIEW` được thiết kế sẵn (theo case study của bài báo gốc ở Table 4 & Table 6).
   * Stage 1: Sinh `Dummy SQL` trên View (Prompt Figure 4).
   * Stage 2: Tái cấu trúc thành `Final SQL` trên bảng gốc (Prompt Figure 5).
4. **Config 4: Auto-V-SQL (Our Proposed Method - Đóng góp chính)**
   * **Module Auto-View:** Thuật toán Python tự động phân tích đồ thị khóa ngoại (`PRAGMA foreign_key_list`), nhận diện các bảng Dimension/Lookup để tự động sinh các câu lệnh `CREATE VIEW v_...`. Hoàn toàn không biết trước câu hỏi người dùng.
   * Chạy pipeline 2-stage (Stage 1 Dummy $\rightarrow$ Stage 2 Reconstruct) dựa trên View tự động.

---

## 4. Các Chỉ số Đánh giá (Evaluation Metrics)

1. **Execution Accuracy (EX) (%):**
   $$EX = \frac{1}{N} \sum_{i=1}^{N} \mathbb{I}(Exec(SQL_{pred}, DB) == Exec(SQL_{gold}, DB))$$
   * Đo đạc theo 3 mức độ khó của BIRD: Simple, Moderate, Challenging (nhiều JOIN).
2. **Schema-based Hallucination Rate (%):**
   * Tỷ lệ câu SQL sinh ra bị lỗi `no such column` hoặc `no such table` do gán nhầm cột giữa các bảng quan hệ.
3. **Syntax Error Rate (%):**
   * Tỷ lệ câu SQL vi phạm cú pháp SQLite không thể thực thi.
4. **Hiệu quả Token (Token Efficiency):**
   * Số token output ở Stage 1 (chứng minh Dummy SQL ngắn hơn và tiết kiệm chi phí suy luận).

---

## 5. Cấu trúc Lưu trữ Artifacts & Kế hoạch Dashboard HTML

### 5.1. Định dạng Artifacts (`do_an/artifacts/`)
Mỗi lần chạy sẽ xuất ra file JSON chi tiết:
```json
{
  "question_id": 1,
  "question": "Please list the superhero names of all the superheroes that have blue eyes",
  "difficulty": "challenging",
  "db_name": "superhero",
  "gold_sql": "SELECT ...",
  "baseline_pred": "SELECT ...",
  "baseline_ex": 0,
  "baseline_error": "no such column: superhero.colour",
  "vsql_dummy": "SELECT ... FROM v_superhero ...",
  "vsql_pred": "SELECT ...",
  "vsql_ex": 1,
  "autovsql_views": ["CREATE VIEW v_superhero AS ..."],
  "autovsql_dummy": "SELECT ...",
  "autovsql_pred": "SELECT ...",
  "autovsql_ex": 1
}
```

### 5.2. Dashboard Trực quan hóa (`do_an/results_visualizer.html`)
Trang web tĩnh (HTML/CSS/JS) chạy ngay trên trình duyệt với các tính năng:
* **Overview Summary Cards:** Tỷ lệ EX của từng phương pháp, tổng số câu đúng/sai.
* **Biểu đồ so sánh (Chart.js):**
  * Cột so sánh EX theo độ khó (Simple, Moderate, Challenging) $\rightarrow$ Chứng minh thế mạnh của View ở nhóm câu hỏi nhiều JOIN.
  * Biểu đồ tròn phân bố lỗi (Hallucination Error vs Syntax Error).
* **Interactive Case Study Viewer:** Giao diện xem đối đầu từng câu hỏi:
  * So sánh Side-by-side: Gold SQL vs Baseline SQL vs Auto-V-SQL.
  * Hiển thị Dummy SQL trung gian và cách mà View tự động giúp LLM không bị nhầm cột.
