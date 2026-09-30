import os
import sys
import json
from typing import List

# Đảm bảo import đúng cấu trúc Clean Architecture
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.models import TestCase, ExperimentRecord
from adapters.sqlite_db import SqliteDatabaseAdapter
from adapters.cpa_llm import CPALlmAdapter
from adapters.json_reporter import JsonReporterAdapter
from services.auto_view import SchemaGraphAutoViewService
from services.evaluator import QueryEvaluatorService
from services.vsql_engine import VSQLExperimentEngine

def get_paper_views_ddl() -> str:
    """View viết tay theo đúng Table 4 & Figure 3 trong bài báo V-SQL (2024)"""
    return """CREATE VIEW `v_superhero` AS
SELECT
  `superhero`.`id`,
  `superhero`.`superhero_name` AS `superhero_name`,
  `superhero`.`full_name`,
  `gender`.`gender`,
  `eye_colour`.`colour` AS `eye_colour`,
  `hair_colour`.`colour` AS `hair_colour`,
  `skin_colour`.`colour` AS `skin_colour`,
  `race`.`race`,
  `publisher`.`publisher_name`,
  `alignment`.`alignment`,
  `superhero`.`height_cm`,
  `superhero`.`weight_kg`
FROM `superhero`
LEFT JOIN `gender` ON `superhero`.`gender_id` = `gender`.`id`
LEFT JOIN `colour` eye_colour ON `superhero`.`eye_colour_id` = `eye_colour`.`id`
LEFT JOIN `colour` hair_colour ON `superhero`.`hair_colour_id` = `hair_colour`.`id`
LEFT JOIN `colour` skin_colour ON `superhero`.`skin_colour_id` = `skin_colour`.`id`
LEFT JOIN `race` ON `superhero`.`race_id` = `race`.`id`
LEFT JOIN `publisher` ON `superhero`.`publisher_id` = `publisher`.`id`
LEFT JOIN `alignment` ON `alignment`.`id` = `superhero`.`alignment_id`;

CREATE VIEW `v_hero_attribute` AS
SELECT
  `hero_attribute`.`hero_id`,
  `superhero`.`superhero_name`,
  `attribute`.`attribute_name`,
  `hero_attribute`.`attribute_value`
FROM `hero_attribute`
LEFT JOIN `superhero` ON `hero_attribute`.`hero_id` = `superhero`.`id`
LEFT JOIN `attribute` ON `hero_attribute`.`attribute_id` = `attribute`.`id`;
"""

def load_bird_test_cases(dataset_json_path: str, db_id: str = "superhero", sample_limit: Optional[int] = None) -> List[TestCase]:
    """Tải các test cases CHÍNH THỨC từ file bird_mini_dev_sqlite.json"""
    with open(dataset_json_path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)
        
    filtered = [d for d in raw_data if d.get("db_id") == db_id]
    
    if sample_limit is not None and sample_limit < len(filtered):
        simple = [d for d in filtered if d.get("difficulty") == "simple"]
        moderate = [d for d in filtered if d.get("difficulty") == "moderate"]
        challenging = [d for d in filtered if d.get("difficulty") == "challenging"]
        k = max(1, sample_limit // 3)
        selected = simple[:k] + moderate[:k] + challenging[:k]
        if len(selected) < sample_limit:
            selected = filtered[:sample_limit]
    else:
        selected = filtered
        
    test_cases = []
    for d in selected:
        test_cases.append(TestCase(
            id=d["question_id"],
            difficulty=d.get("difficulty", "moderate").capitalize(),
            question=d["question"],
            gold_sql=d["SQL"],
            evidence=d.get("evidence", "")
        ))
    return test_cases

def main():
    print("=" * 75)
    print("    HỆ THỐNG THỰC NGHIỆM ĐỐI CHỨNG TEXT-TO-SQL TRÊN BIRD BENCHMARK GỐC    ")
    print("    Kiến trúc: Ports & Adapters + DI + OOP/FP (Clean Architecture)       ")
    print("    Mô hình: gemini-3.5-flash-lite via CPA Proxy (localhost:8317)       ")
    print("=" * 75)

    base_dir = os.path.dirname(os.path.abspath(__file__))
    db_file = os.path.join(base_dir, "data", "bird_databases", "superhero", "superhero.sqlite")
    dataset_json = os.path.join(base_dir, "data", "bird_mini_dev_sqlite.json")
    artifacts_dir = os.path.join(base_dir, "artifacts")

    if not os.path.exists(db_file):
        print(f"[!] Lỗi: Không tìm thấy database tại {db_file}")
        return

    # 1. Dependency Injection: Khởi tạo Adapters & Services
    print("\n[1/4] Khởi tạo Adapters và Services (Dependency Injection)...")
    db_adapter = SqliteDatabaseAdapter(db_file)
    llm_adapter = CPALlmAdapter(
        endpoint_url="http://localhost:8317/v1/chat/completions",
        model_name="gemini-3.5-flash-lite",
        temperature=0.0
    )
    evaluator_service = QueryEvaluatorService(db=db_adapter)
    auto_view_service = SchemaGraphAutoViewService()
    reporter_adapter = JsonReporterAdapter(output_dir=artifacts_dir)
    vsql_engine = VSQLExperimentEngine(llm=llm_adapter, evaluator=evaluator_service)

    # 2. Phân tích Schema và Tạo Views tự động
    print("[2/4] Quét cấu trúc khóa ngoại và tự động tạo Views (Auto-View Generator)...")
    schema_meta = db_adapter.get_all_tables_metadata()
    raw_ddl = db_adapter.get_full_schema_ddl()
    
    auto_views_dict = auto_view_service.generate_views(schema_meta)
    auto_views_ddl = "\n\n".join(auto_views_dict.values())
    paper_views_ddl = get_paper_views_ddl()
    print(f"      -> Tự động sinh thành công {len(auto_views_dict)} views từ schema gốc.")

    # 3. Nạp tập Test Cases từ BIRD Benchmark (Full 52 câu)
    test_cases = load_bird_test_cases(dataset_json, db_id="superhero", sample_limit=None)
    print(f"[3/4] Đã nạp toản bộ {len(test_cases)} câu hỏi chính thức của BIRD Mini-Dev (SuperHero DB).")
    print("      Phân bố: " + ", ".join([f"{diff}: {sum(1 for t in test_cases if t.difficulty.lower() == diff.lower())}" for diff in ["Simple", "Moderate", "Challenging"]]))

    # 4. Thực thi thực nghiệm đối chứng
    print(f"\n[4/4] Bắt đầu chạy thực nghiệm đối chứng trên FULL {len(test_cases)} câu...")
    records: List[ExperimentRecord] = []

    for idx, tc in enumerate(test_cases, 1):
        print(f"\n--- [Case {idx}/{len(test_cases)} | ID:{tc.id}] [{tc.difficulty}] ---")
        print(f"  Q: {tc.question}")
        if tc.evidence:
            print(f"  E: {tc.evidence[:60]}...")

        # Config 1: Baseline Direct
        base_out = vsql_engine.run_baseline_direct(tc.question, raw_ddl, tc.gold_sql, tc.evidence)
        base_status = "ĐÚNG" if base_out.execution.is_correct else "SAI"
        print(f"  [1] Baseline Direct : [{base_status}] {base_out.execution.error_message}")

        # Config 2: V-SQL Replicated (Paper manual views)
        vsql_out = vsql_engine.run_two_stage_view_sql(tc.question, raw_ddl, paper_views_ddl, tc.gold_sql, tc.evidence)
        vsql_status = "ĐÚNG" if vsql_out.execution.is_correct else "SAI"
        print(f"  [2] V-SQL (Paper)   : [{vsql_status}] {vsql_out.execution.error_message}")

        # Config 3: Auto-V-SQL (Our Proposed Auto-Views)
        autovsql_out = vsql_engine.run_two_stage_view_sql(tc.question, raw_ddl, auto_views_ddl, tc.gold_sql, tc.evidence)
        autovsql_status = "ĐÚNG" if autovsql_out.execution.is_correct else "SAI"
        print(f"  [3] Auto-V-SQL (Ours): [{autovsql_status}] {autovsql_out.execution.error_message}")

        records.append(ExperimentRecord(
            test_id=tc.id,
            difficulty=tc.difficulty,
            question=tc.question,
            gold_sql=tc.gold_sql,
            baseline=base_out,
            vsql_paper=vsql_out,
            autovsql=autovsql_out
        ))

    # Lưu Artifacts ra JSON
    saved_path = reporter_adapter.save_records(records, "experiment_results.json")
    print(f"\n[OK] Toàn bộ kết quả chi tiết đã được lưu tại: {saved_path}")

    # Tự động cập nhật vào visualize.html
    html_file = os.path.join(base_dir, "visualize.html")
    if os.path.exists(html_file):
        with open(saved_path, "r", encoding="utf-8") as f:
            json_text = f.read()
        with open(html_file, "r", encoding="utf-8") as f:
            html = f.read()
        import re
        html = re.sub(r"let experimentData = \[.*?\];", f"let experimentData = {json_text};", html, flags=re.DOTALL)
        with open(html_file, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"[OK] Đã cập nhật kết quả full vào Dashboard: {html_file}")

    # Báo cáo thống kê
    total = len(records)
    base_acc = sum(1 for r in records if r.baseline.execution.is_correct) / total * 100
    vsql_acc = sum(1 for r in records if r.vsql_paper.execution.is_correct) / total * 100
    autovsql_acc = sum(1 for r in records if r.autovsql.execution.is_correct) / total * 100

    print("\n" + "=" * 75)
    print("                     BẢNG TỔNG HỢP KẾT QUẢ CUỐI CÙNG                   ")
    print("=" * 75)
    print(f"  * Baseline Direct (1-Stage)     : {base_acc:6.2f}% ({sum(1 for r in records if r.baseline.execution.is_correct)}/{total})")
    print(f"  * V-SQL Paper Replicate (Manual): {vsql_acc:6.2f}% ({sum(1 for r in records if r.vsql_paper.execution.is_correct)}/{total})")
    print(f"  * Auto-V-SQL (Our Contribution) : {autovsql_acc:6.2f}% ({sum(1 for r in records if r.autovsql.execution.is_correct)}/{total})")
    print("=" * 75)

if __name__ == "__main__":
    main()
