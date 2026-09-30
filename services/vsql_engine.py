from typing import Dict, Optional
from core.models import MethodRunOutput, ExecutionResult
from core.ports import LLMPort, ViewGeneratorPort
from services.evaluator import QueryEvaluatorService

class VSQLExperimentEngine:
    """
    Engine điều phối quy trình Text-to-SQL (OOP với Dependency Injection).
    Đóng gói các chiến lược Prompting và tích hợp chặt chẽ với LLMPort và Evaluator.
    """
    def __init__(self, llm: LLMPort, evaluator: QueryEvaluatorService):
        self.llm = llm
        self.evaluator = evaluator

    def run_baseline_direct(self, question: str, raw_schema_ddl: str, gold_sql: str, evidence: str = "") -> MethodRunOutput:
        """Chiến lược 1: Direct Zero-shot (1-Stage Baseline)"""
        q_text = f"{question}\n-- Evidence: {evidence}" if evidence else question
        prompt = f"""# Target
You are an experienced database administrator, please answer "question" by sql with no explanation.
Notice:
1. Do not alias the output fields
2. Must avoid ambiguous column name by using table name and column name in the SQL statement. For example, use `table_name.column_name` instead of just `column_name`.
3. Refer to "relevant db schema"
4. Comply with the syntax of SQLite.

# relevant db schema
{raw_schema_ddl}

# question
{q_text}
"""
        predicted_sql = self.llm.generate_sql(prompt)
        exec_res = self.evaluator.evaluate(predicted_sql, gold_sql)
        return MethodRunOutput(predicted_sql=predicted_sql, execution=exec_res)

    def run_two_stage_view_sql(self, question: str, raw_schema_ddl: str, 
                               views_ddl: str, gold_sql: str, evidence: str = "") -> MethodRunOutput:
        """
        Khung xử lý chung 2 giai đoạn (Two-Stage View-based Framework):
        Stage 1 (Encoder): Sinh Dummy SQL trên View.
        Stage 2 (Decoder): Tái cấu trúc thành Final SQL trên bảng gốc.
        """
        q_text = f"{question}\n-- Evidence: {evidence}" if evidence else question
        # --- Stage 1: Dummy SQL Generation (Prompt Figure 4 của bài báo) ---
        prompt_stage1 = f"""# target
You are an experienced database administrator, please answer "question" by sql with no explanation.
notice:
1. Do not alias the output fields
2. must avoid ambiguous column name by using table name and column name in the SQL statement. For example, use `table_name.column_name` instead of just `column_name`.
3. refer to "relevant db schema"

# relevant db schema
{views_ddl}

# question
{q_text}
"""
        dummy_sql = self.llm.generate_sql(prompt_stage1)

        # --- Stage 2: SQL Reconstruction (Prompt Figure 5 của bài báo) ---
        prompt_stage2 = f"""# target
According to the "views schemas", "view query" and "relevant table schemas", restore the sql in view query to one used the original table query without explanation
notice:
1. SQL should contain "join" as little as possible.
2. table in "views schemas" should not be contained in output.
3. comply with the syntax of SQLite.
4. must avoid ambiguous column name by using table name and column name in the SQL statement. For example, use `table_name.column_name` instead of just `column_name`.

# view schemas
{views_ddl}

# view query
Question: {q_text}
```sql
{dummy_sql}
```

# relevant table schemas
{raw_schema_ddl}

# format
```sql
{{sql}}
```
"""
        final_sql = self.llm.generate_sql(prompt_stage2)
        exec_res = self.evaluator.evaluate(final_sql, gold_sql)

        return MethodRunOutput(
            predicted_sql=final_sql,
            execution=exec_res,
            dummy_sql=dummy_sql,
            views_used=views_ddl
        )
