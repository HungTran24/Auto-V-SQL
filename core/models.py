from dataclasses import dataclass, field
from typing import List, Tuple, Any, Optional, Set

@dataclass(frozen=True)
class ForeignKeyInfo:
    """Mô tả một liên kết khóa ngoại giữa 2 bảng (bất biến - FP style)"""
    from_col: str
    target_table: str
    to_col: str

@dataclass(frozen=True)
class TableMetadata:
    """Metadata cấu trúc của một bảng trong database"""
    name: str
    columns: Tuple[str, ...]
    foreign_keys: Tuple[ForeignKeyInfo, ...]
    create_sql: str

@dataclass(frozen=True)
class TestCase:
    """Mẫu thử nghiệm Text-to-SQL"""
    id: int
    difficulty: str
    question: str
    gold_sql: str
    evidence: str = ""

@dataclass(frozen=True)
class ExecutionResult:
    """Kết quả thực thi câu SQL trên Database Engine"""
    is_executable: bool
    is_correct: bool
    error_message: str
    rows: Optional[Tuple[Any, ...]] = None

@dataclass(frozen=True)
class MethodRunOutput:
    """Kết quả dự đoán của một phương pháp Text-to-SQL"""
    predicted_sql: str
    execution: ExecutionResult
    dummy_sql: Optional[str] = None
    views_used: Optional[str] = None

@dataclass
class ExperimentRecord:
    """Bản ghi tổng hợp kết quả của 1 test case trên tất cả phương pháp"""
    test_id: int
    difficulty: str
    question: str
    gold_sql: str
    baseline: MethodRunOutput
    vsql_paper: MethodRunOutput
    autovsql: MethodRunOutput
