import sqlite3
from typing import Dict, Tuple, Any, Optional
from core.models import TableMetadata, ForeignKeyInfo
from core.ports import DatabasePort

class SqliteDatabaseAdapter(DatabasePort):
    """Adapter thao tác với SQLite Database Engine"""
    def __init__(self, db_path: str):
        self.db_path = db_path

    def get_all_tables_metadata(self) -> Dict[str, TableMetadata]:
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        
        cur.execute("SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
        tables_data = cur.fetchall()
        
        metadata_dict = {}
        for table_name, create_sql in tables_data:
            # Lấy cột
            cur.execute(f"PRAGMA table_info(`{table_name}`);")
            cols = tuple(row[1] for row in cur.fetchall())
            
            # Lấy khóa ngoại: (id, seq, to_table, from_col, to_col, ...)
            cur.execute(f"PRAGMA foreign_key_list(`{table_name}`);")
            raw_fks = cur.fetchall()
            
            fk_infos = tuple(
                ForeignKeyInfo(from_col=row[3], target_table=row[2], to_col=row[4])
                for row in raw_fks
            )
            
            metadata_dict[table_name] = TableMetadata(
                name=table_name,
                columns=cols,
                foreign_keys=fk_infos,
                create_sql=create_sql or ""
            )
            
        conn.close()
        return metadata_dict

    def get_full_schema_ddl(self) -> str:
        meta = self.get_all_tables_metadata()
        return "\n\n".join(t.create_sql for t in meta.values())

    def execute_query(self, sql: str) -> Tuple[bool, Optional[Tuple[Any, ...]], str]:
        """Thực thi câu SQL, trả về (thành công, dữ liệu dòng, thông báo lỗi)"""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        try:
            cur.execute(sql)
            rows = tuple(cur.fetchall())
            conn.close()
            return True, rows, ""
        except Exception as e:
            conn.close()
            return False, None, str(e)
