from typing import Protocol, Dict, Tuple, Any, List
from core.models import TableMetadata, ExecutionResult

class LLMPort(Protocol):
    """Port giao tiếp với Large Language Model"""
    def generate_sql(self, prompt: str, system_prompt: str = "") -> str:
        """Gửi prompt tới LLM và nhận về câu SQL đã làm sạch"""
        ...

class DatabasePort(Protocol):
    """Port giao tiếp với Database Engine"""
    def get_all_tables_metadata(self) -> Dict[str, TableMetadata]:
        """Lấy thông tin cấu trúc schema và khóa ngoại toàn bộ database"""
        ...
        
    def get_full_schema_ddl(self) -> str:
        """Lấy toàn bộ câu lệnh DDL của database"""
        ...

    def execute_query(self, sql: str) -> Tuple[bool, Optional[Tuple[Any, ...]], str]:
        """Thực thi câu SQL, trả về (thành công, dữ liệu dòng, thông báo lỗi)"""
        ...

class ViewGeneratorPort(Protocol):
    """Port sinh View từ metadata cấu trúc cơ sở dữ liệu"""
    def generate_views(self, schema_metadata: Dict[str, TableMetadata]) -> Dict[str, str]:
        """Nhận schema metadata và sinh tập hợp các câu lệnh CREATE VIEW"""
        ...
