import os
import sys
import json
import argparse
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from typing import List, Optional

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

BATCH_SIZE = 20
MODEL = "gemini-3.5-flash-lite"
ENDPOINT = "http://localhost:8317/v1/chat/completions"


def stage1_schema(auto_views: dict, meta: dict) -> str:
    """D' = các View tự sinh + DDL gốc của bảng chưa có View (DB không sinh được View thì dùng nguyên D)."""
    uncovered = [t.create_sql for name, t in meta.items() if f"v_{name}" not in auto_views]
    return "\n\n".join(list(auto_views.values()) + uncovered)


def build_context(base_dir: str, db_id: str) -> dict:
    db = SqliteDatabaseAdapter(os.path.join(base_dir, "data", "bird_databases", db_id, f"{db_id}.sqlite"))
    llm = CPALlmAdapter(endpoint_url=ENDPOINT, model_name=MODEL, temperature=0.0, max_attempts=3)
    engine = VSQLExperimentEngine(llm=llm, evaluator=QueryEvaluatorService(db=db))
    meta = db.get_all_tables_metadata()
    auto_views = SchemaGraphAutoViewService().generate_views(meta)
    return {
        "engine": engine,
        "raw_ddl": db.get_full_schema_ddl(),
        "auto_ddl": stage1_schema(auto_views, meta),
        "paper_ddl": get_paper_views_ddl() if db_id == "superhero" else None,  # View viết tay chỉ có cho superhero
        "n_views": len(auto_views),
    }


def run_case(ctx: dict, db_id: str, tc: TestCase) -> dict:
    e = ctx["engine"]
    base = e.run_baseline_direct(tc.question, ctx["raw_ddl"], tc.gold_sql, tc.evidence)
    paper = (e.run_two_stage_view_sql(tc.question, ctx["raw_ddl"], ctx["paper_ddl"], tc.gold_sql, tc.evidence)
             if ctx["paper_ddl"] else None)
    auto = e.run_two_stage_view_sql(tc.question, ctx["raw_ddl"], ctx["auto_ddl"], tc.gold_sql, tc.evidence)
    rec = asdict(ExperimentRecord(tc.id, tc.difficulty, tc.question, tc.gold_sql, base, paper, auto, db_id))
    for key in ("baseline", "vsql_paper", "autovsql"):  # rows + DDL lặp lại làm file phình hàng trăm nghìn dòng
        if rec[key]:
            rec[key]["execution"]["rows"] = None
            rec[key]["views_used"] = None
    return rec


def summarize(records: List[dict]) -> None:
    def ex(rows, key):
        rows = [r for r in rows if r[key]]
        return (f"{sum(r[key]['execution']['is_correct'] for r in rows) / len(rows) * 100:6.2f}% "
                f"({sum(r[key]['execution']['is_correct'] for r in rows)}/{len(rows)})") if rows else "   n/a"
    groups = defaultdict(list)
    for r in records:
        groups["TOTAL"].append(r); groups[r["db_id"]].append(r); groups["~" + r["difficulty"]].append(r)
    print(f"\n{'Nhóm':28}{'Direct':>18}{'V-SQL paper':>18}{'Auto-V-SQL':>18}")
    for g in sorted(groups, key=lambda k: (k != "TOTAL", k.startswith("~"), k)):
        rows = groups[g]
        print(f"{g:28}{ex(rows,'baseline'):>18}{ex(rows,'vsql_paper'):>18}{ex(rows,'autovsql'):>18}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit-per-db", type=int, default=None, help="Chạy thử: chỉ lấy N câu mỗi DB")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--output", default="experiment_results_full.json")
    args = ap.parse_args()

    base_dir = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(base_dir, "data", "bird_mini_dev_sqlite.json"), encoding="utf-8") as f:
        raw = json.load(f)
    db_ids = sorted({d["db_id"] for d in raw})
    reporter = JsonReporterAdapter(output_dir=os.path.join(base_dir, "artifacts"))
    out_path = os.path.join(base_dir, "artifacts", args.output)

    records: List[dict] = json.load(open(out_path, encoding="utf-8")) if os.path.exists(out_path) else []
    done = {(r["db_id"], r["test_id"]) for r in records}
    print(f"Model: {MODEL} | {len(db_ids)} DB | đã có {len(records)} bản ghi (resume) | workers={args.workers}")

    tasks = []
    contexts = {}
    for db_id in db_ids:
        contexts[db_id] = build_context(base_dir, db_id)
        cases = load_bird_test_cases(os.path.join(base_dir, "data", "bird_mini_dev_sqlite.json"), db_id=db_id)
        if args.limit_per_db:
            cases = cases[:args.limit_per_db]
        print(f"  {db_id:26} {len(cases):3} câu | auto-view: {contexts[db_id]['n_views']} view")
        tasks += [(db_id, tc) for tc in cases if (db_id, tc.id) not in done]
    print(f"Còn {len(tasks)} câu cần chạy.\n")

    since_save = 0
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for i, rec in enumerate(pool.map(lambda t: run_case(contexts[t[0]], *t), tasks), 1):
            records.append(rec)
            since_save += 1
            mark = lambda m: "-" if m is None else ("OK" if m["execution"]["is_correct"] else "X")
            print(f"[{i}/{len(tasks)}] {rec['db_id']}#{rec['test_id']} {rec['difficulty']:11} "
                  f"direct={mark(rec['baseline'])} paper={mark(rec['vsql_paper'])} auto={mark(rec['autovsql'])}", flush=True)
            if since_save >= BATCH_SIZE:
                reporter.save_raw(records, args.output)
                since_save = 0
    reporter.save_raw(records, args.output)
    print(f"\n[OK] Đã lưu {len(records)} bản ghi -> {out_path}")
    summarize(records)


if __name__ == "__main__":
    main()
