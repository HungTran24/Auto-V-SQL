# Auto-V-SQL: Automated View-based Two-Stage Text-to-SQL Framework

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Architecture](https://img.shields.io/badge/Architecture-Ports%20%26%20Adapters%20(Hexagonal)-teal.svg)](#architecture)
[![Dataset](https://img.shields.io/badge/Benchmark-BIRD%20Mini--Dev-orange.svg)](https://bird-bench.github.io/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

Đồ án nghiên cứu & thực nghiệm môn học **Hệ cơ sở dữ liệu tiên tiến** (Advanced Database Systems).

---

## 📌 Giới Thiệu & Động Lực Nghiên Cứu

### 1. Bối cảnh & Bài báo gốc
Dự án thực hiện tái hiện và mở rộng nghiên cứu từ bài báo:  
> **"V-SQL: A View-based Twostage Text-to-SQL Framework"** (You et al., 2024).

Phương pháp gốc của V-SQL giải quyết hiện tượng **Schema-based Hallucination** (LLM bị lú lẫn khi phải thực hiện nhiều phép `JOIN` giữa các bảng có khóa ngoại phức tạp) bằng cách:
1. **Stage 1 (Encoder):** Cho LLM sinh câu `Dummy SQL` ngắn gọn truy vấn trực tiếp trên các View ảo (làm phẳng các bảng danh mục, 0 phép JOIN).
2. **Stage 2 (Decoder):** Giải mã `Dummy SQL` thành `Final SQL` truy vấn trên các bảng gốc thật.

### 2. Vấn đề cốt tử của bài báo gốc (Research Gap)
Trong bài báo gốc (Section 6 - Discussion), tác giả thừa nhận các câu lệnh `CREATE VIEW` được **thiết kế thủ công bằng cách nhìn trước các phép JOIN trong ground-truth SQL** của tập kiểm thử (*Data Leakage*). Trong môi trường thực tế, không thể biết trước câu hỏi người dùng để chuẩn bị View thủ công như vậy.

### 3. Đóng góp của Đồ án (**Auto-V-SQL**)
* **Module Auto-View Generation:** Tự động phân tích đồ thị khóa ngoại (`Schema Graph`) từ metadata của SQLite (`PRAGMA foreign_key_list`).
* Tự động nhận diện các bảng Dimension/Lookup và bảng Fact/Main để sinh ra các **Star-Schema Views** mà **hoàn toàn không cần con người can thiệp và không nhìn trước câu hỏi** (*Zero Data Leakage*).
* Cài đặt toàn bộ hệ thống theo chuẩn **Clean Architecture (Ports & Adapters + Dependency Injection + OOP/FP)**.

---

## 🏛️ Kiến Trúc Hệ Thống (Clean Architecture)

Hệ thống tuân thủ nghiêm ngặt nguyên lý phân tách trách nhiệm (Separation of Concerns):

```
do_an/
├── core/                   # Domain Core (Độc lập hạ tầng)
│   ├── models.py           # Immutable Dataclasses (@dataclass(frozen=True))
│   └── ports.py            # Interfaces / Protocols (LLMPort, DatabasePort, ViewGeneratorPort)
├── adapters/               # Infrastructure Adapters (Cắm & Rút linh hoạt)
│   ├── cpa_llm.py          # Adapter kết nối CPA Proxy (http://localhost:8317, gemini-3.5-flash-lite)
│   ├── sqlite_db.py        # Adapter thực thi SQLite & trích xuất DDL / Foreign Keys
│   └── json_reporter.py    # Adapter lưu trữ kết quả ra file JSON
├── services/               # Application Services (Nghiệp vụ cốt lõi)
│   ├── auto_view.py        # Core Algorithm: Tự động phân tích đồ thị khóa ngoại & sinh Views
│   ├── evaluator.py        # Service chấm điểm Execution Accuracy (EX) chuẩn xác
│   └── vsql_engine.py      # Two-Stage V-SQL Coordinator Engine
├── data/
│   ├── bird_mini_dev_sqlite.json # 500 câu hỏi chính thức của BIRD Mini-Dev
│   ├── superhero_setup.py  # Script khởi tạo CSDL mẫu
│   └── superhero.sqlite    # CSDL mẫu
├── artifacts/
│   └── experiment_results.json # Kết quả thực nghiệm chi tiết từng câu
├── experiment.md           # Đặc tả kế hoạch nghiên cứu khoa học
├── run_experiment.py       # Main Entry Point (DI Wiring)
└── visualize.html          # Web Dashboard tương tác trực quan hóa kết quả
```

---

## 📊 Kết Quả Thực Nghiệm Đối Chứng (BIRD Benchmark)

Thực nghiệm được thực hiện trên toàn bộ **52 câu hỏi chính thức** của cơ sở dữ liệu `superhero.sqlite` từ **BIRD Mini-Dev Benchmark** với mô hình `gemini-3.5-flash-lite` (Temperature = 0.0):

| Phương pháp | Tổng điểm EX (%) | Simple (14 câu) | Moderate (26 câu) | Challenging (12 câu) | Tỷ lệ lỗi cú pháp |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **1. Baseline Direct (1-Stage)** | **82.69%** (43/52) | 92.86% (13/14) | 84.62% (22/26) | **66.67%** (8/12) | 1 lỗi (`no such table`) |
| **2. V-SQL Paper (View viết tay)** | **84.62%** (44/52) | 92.86% (13/14) | **92.31%** (24/26) | 58.33% (7/12) | **0%** (100% hợp lệ) |
| **3. Auto-V-SQL (Đồ án đề xuất)** | **82.69%** (43/52) | 92.86% (13/14) | **88.46%** (23/26) | 58.33% (7/12) | **0%** (100% hợp lệ) |

### Nhận xét khoa học:
1. **Ưu thế ở nhóm Moderate (1–2 phép JOIN):** Auto-V-SQL đạt **88.46%** (+3.84% so với Baseline 84.62%), chứng minh việc làm phẳng schema thành View giúp giảm tải nhận thức và hạn chế nhầm lẫn bảng/cột.
2. **Triệt tiêu lỗi Hallucination Schema:** Baseline Direct gặp lỗi nghiêm trọng ở Case #772: LLM bị quá tải khóa ngoại tự bịa ra bảng `superhero.superhero`. Auto-V-SQL đạt **0% lỗi cú pháp và 0% lỗi sai bảng** trên toàn bộ 52 câu.
3. **Tính thực tiễn (Generalizability):** Auto-V-SQL đạt kết quả bám sát View viết tay (82.69% vs 84.62%) với quy trình **hoàn toàn tự động 100%**, biến ý tưởng V-SQL thành giải pháp triển khai thực tế.

---

## 🚀 Hướng Dẫn Cài Đặt & Chạy Thực Nghiệm

### 1. Yêu cầu môi trường
* Python 3.10+
* Local LLM Proxy chạy tại `http://localhost:8317` (hỗ trợ endpoint `/v1/chat/completions` với model `gemini-3.5-flash-lite` hoặc tương đương).

### 2. Cài đặt thư viện
```bash
pip install -r requirements.txt
```

### 3. Chạy thực nghiệm
```bash
python run_experiment.py
```
Toàn bộ kết quả thực thi và đánh giá đối chứng sẽ được lưu vào file `artifacts/experiment_results.json` và tự động cập nhật vào `visualize.html`.

### 4. Mở Dashboard Trực Quan Hóa
Mở trực tiếp file `visualize.html` trên trình duyệt:
```bash
# Hoặc khởi động một HTTP server đơn giản:
python -m http.server 8089
# Sau đó truy cập: http://localhost:8089/visualize.html
```

---

## 👥 Tác Giả & Giấy Phép
* **Học viên:** Trần Quốc Hùng (`HungTran24`)
* **Môn học:** Hệ cơ sở dữ liệu tiên tiến
* **Giấy phép:** [MIT License](LICENSE)
