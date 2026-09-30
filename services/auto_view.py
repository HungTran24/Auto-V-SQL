from typing import Dict, List
from core.models import TableMetadata
from core.ports import ViewGeneratorPort

class SchemaGraphAutoViewService(ViewGeneratorPort):
    """
    Service sinh View tự động (Đóng góp của đồ án).
    Áp dụng nguyên lý Functional Programming:
    - Nhận vào metadata cấu trúc (bất biến)
    - Không làm thay đổi trạng thái (Stateless)
    - Trả về tập hợp các câu lệnh CREATE VIEW
    """
    def generate_views(self, schema_metadata: Dict[str, TableMetadata]) -> Dict[str, str]:
        views = {}
        for main_table_name, meta in schema_metadata.items():
            if not meta.foreign_keys:
                continue
                
            select_clauses = [f"`{main_table_name}`.`{col}` AS `{col}`" for col in meta.columns]
            join_clauses = []
            
            for fk in meta.foreign_keys:
                target_table = fk.target_table
                from_col = fk.from_col
                to_col = fk.to_col
                
                if target_table in schema_metadata:
                    target_meta = schema_metadata[target_table]
                    # Nhận diện bảng Dimension/Lookup: ít hơn hoặc bằng 4 cột
                    if len(target_meta.columns) <= 4:
                        alias = from_col.replace("_id", "") if from_col.endswith("_id") else f"{target_table}_{from_col}"
                        join_clauses.append(
                            f"LEFT JOIN `{target_table}` AS `{alias}` ON `{main_table_name}`.`{from_col}` = `{alias}`.`{to_col}`"
                        )
                        
                        # Làm phẳng các thuộc tính ngữ nghĩa vào View
                        for t_col in target_meta.columns:
                            if t_col != to_col:
                                field_alias = f"{alias}_{t_col}" if t_col == alias else (
                                    alias if t_col in ["name", "value", "desc", target_table] else f"{alias}_{t_col}"
                                )
                                select_clauses.append(f"`{alias}`.`{t_col}` AS `{field_alias}`")
                                
            if join_clauses:
                view_name = f"v_{main_table_name}"
                view_sql = (
                    f"CREATE VIEW `{view_name}` AS\n"
                    f"SELECT\n  " + ",\n  ".join(select_clauses) + "\n"
                    f"FROM `{main_table_name}`\n" + "\n".join(join_clauses) + ";"
                )
                views[view_name] = view_sql
                
        return views
