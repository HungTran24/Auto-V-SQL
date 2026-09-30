from typing import Tuple, Any, Optional
from core.models import ExecutionResult
from core.ports import DatabasePort

class QueryEvaluatorService:
    """Service đánh giá độ chính xác thực thi (Execution Accuracy - EX)"""
    def __init__(self, db: DatabasePort):
        self.db = db

    def evaluate(self, predicted_sql: str, gold_sql: str) -> ExecutionResult:
        """
        Thực thi cả 2 câu SQL trên DatabasePort và so khớp tập kết quả trả về.
        Pure Evaluation Logic: kết quả đúng khi và chỉ khi tập dữ liệu trả về giống nhau.
        """
        # 1. Chạy câu Gold SQL chuẩn
        gold_ok, gold_rows, gold_err = self.db.execute_query(gold_sql)
        if not gold_ok:
            return ExecutionResult(
                is_executable=False,
                is_correct=False,
                error_message=f"Gold Query Failed: {gold_err}"
            )

        if not predicted_sql.strip():
            return ExecutionResult(
                is_executable=False,
                is_correct=False,
                error_message="Empty predicted SQL"
            )

        # 2. Chạy câu Predicted SQL
        pred_ok, pred_rows, pred_err = self.db.execute_query(predicted_sql)
        if not pred_ok:
            return ExecutionResult(
                is_executable=False,
                is_correct=False,
                error_message=pred_err
            )

        # 3. So sánh dữ liệu thực thi (dạng set để bỏ qua thứ tự trừ khi cần)
        try:
            is_match = (set(pred_rows) == set(gold_rows)) if pred_rows is not None and gold_rows is not None else False
            err_msg = "" if is_match else "Data Mismatch (Returned rows do not match gold SQL)"
            return ExecutionResult(
                is_executable=True,
                is_correct=is_match,
                error_message=err_msg,
                rows=pred_rows
            )
        except Exception as e:
            return ExecutionResult(
                is_executable=True,
                is_correct=False,
                error_message=f"Comparison Error: {e}"
            )
