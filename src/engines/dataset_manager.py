"""Dataset Manager - 数据集管理引擎"""

import uuid
import duckdb
import pandas as pd
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from src.core.config import settings
from src.core.constants import DTYPE_MAPPING, MAX_COLUMNS, MAX_ROWS_SAMPLE
from src.models.dataset import DatasetMetadata, ColumnSchema, DatasetSample
from src.utils.logger import log


class DatasetManager:
    """数据集管理器"""

    # 数据集过期时间（小时）
    DATASET_TTL_HOURS = 24

    def __init__(self):
        self.db_path = settings.duckdb_dir / "datasets.db"
        self.datasets: Dict[str, DatasetMetadata] = {}

    def _get_connection(self) -> duckdb.DuckDBPyConnection:
        """获取 DuckDB 连接"""
        return duckdb.connect(str(self.db_path))

    def _normalize_dtype(self, dtype: str) -> str:
        """标准化数据类型"""
        dtype_str = str(dtype)
        return DTYPE_MAPPING.get(dtype_str, "string")

    def create_dataset(
        self,
        file_id: str,
        file_path: Path,
        original_filename: str,
        sheet: Optional[str] = None,
        header_row: int = 1
    ) -> DatasetMetadata:
        """
        创建数据集

        Args:
            file_id: 文件ID
            file_path: 文件路径
            original_filename: 原始文件名
            sheet: Excel Sheet 名称
            header_row: 表头行号（从1开始）

        Returns:
            DatasetMetadata: 数据集元数据
        """
        log.info(f"创建数据集: {original_filename}")

        # 生成数据集ID
        dataset_id = f"ds_{uuid.uuid4().hex[:12]}"

        # 读取文件
        try:
            if file_path.suffix.lower() in ['.xlsx', '.xls']:
                df = pd.read_excel(
                    file_path,
                    sheet_name=sheet or 0,
                    header=header_row - 1
                )
                source_type = "excel"
            elif file_path.suffix.lower() == '.csv':
                df = pd.read_csv(file_path, header=header_row - 1)
                source_type = "csv"
            else:
                raise ValueError(f"不支持的文件类型: {file_path.suffix}")

            log.info(f"数据集 {dataset_id} 读取成功: {len(df)} 行, {len(df.columns)} 列")

        except Exception as e:
            log.error(f"读取文件失败: {e}")
            raise

        # 检查列数限制
        if len(df.columns) > MAX_COLUMNS:
            raise ValueError(f"列数超过限制: {len(df.columns)} > {MAX_COLUMNS}")

        # 提取 Schema
        schema = self._extract_schema(df)

        # 存储到 DuckDB
        table_name = f"dataset_{dataset_id}"
        conn = self._get_connection()
        try:
            conn.execute(f"CREATE TABLE IF NOT EXISTS {table_name} AS SELECT * FROM df")
            log.info(f"数据集 {dataset_id} 已存储到 DuckDB 表: {table_name}")
        finally:
            conn.close()

        # 创建元数据
        metadata = DatasetMetadata(
            dataset_id=dataset_id,
            source_type=source_type,
            original_filename=original_filename,
            file_path=str(file_path),
            sheet_name=sheet,
            row_count=len(df),
            column_count=len(df.columns),
            columns_schema=schema,  # 使用新的字段名
            created_at=datetime.now(),
            size_bytes=file_path.stat().st_size
        )

        # 缓存元数据
        self.datasets[dataset_id] = metadata

        log.info(f"数据集 {dataset_id} 创建完成")
        return metadata

    def _extract_schema(self, df: pd.DataFrame) -> List[ColumnSchema]:
        """提取 DataFrame 的 Schema"""
        schema = []

        for col in df.columns:
            dtype = self._normalize_dtype(df[col].dtype)
            null_count = df[col].isna().sum()
            null_ratio = null_count / len(df) if len(df) > 0 else 0.0

            # 获取示例值（非空）
            non_null_values = df[col].dropna()
            example_values = non_null_values.head(3).tolist() if len(non_null_values) > 0 else []

            # 唯一值数量
            unique_count = df[col].nunique()

            # 最小/最大值（数值和日期类型）
            min_value = None
            max_value = None
            if dtype in ['int', 'float']:
                if len(non_null_values) > 0:
                    min_value = float(non_null_values.min())
                    max_value = float(non_null_values.max())

            col_schema = ColumnSchema(
                name=str(col),
                type=dtype,
                null_ratio=round(null_ratio, 4),
                example_values=example_values,
                unique_count=unique_count,
                min_value=min_value,
                max_value=max_value
            )
            schema.append(col_schema)

        return schema

    def get_schema(self, dataset_id: str) -> DatasetMetadata:
        """获取数据集 Schema"""
        if dataset_id in self.datasets:
            return self.datasets[dataset_id]

        # TODO: 从持久化存储中加载
        raise ValueError(f"数据集不存在: {dataset_id}")

    def sample_rows(
        self,
        dataset_id: str,
        n: int = 5,
        columns: Optional[List[str]] = None
    ) -> DatasetSample:
        """获取样本数据"""
        metadata = self.get_schema(dataset_id)
        table_name = f"dataset_{dataset_id}"

        # 构建 SQL
        col_list = "*"
        if columns:
            # 验证列名存在
            valid_cols = {c.name for c in metadata.columns_schema}
            invalid_cols = set(columns) - valid_cols
            if invalid_cols:
                raise ValueError(f"列不存在: {invalid_cols}")
            col_list = ", ".join([f'"{c}"' for c in columns])

        sql = f'SELECT {col_list} FROM {table_name} LIMIT {min(n, MAX_ROWS_SAMPLE)}'

        conn = self._get_connection()
        try:
            result = conn.execute(sql).fetchdf()
            return DatasetSample(
                columns=result.columns.tolist(),
                rows=result.values.tolist(),
                total_rows=metadata.row_count
            )
        finally:
            conn.close()

    def dataset_exists(self, dataset_id: str) -> bool:
        """检查数据集是否存在"""
        return dataset_id in self.datasets

    def get_table_name(self, dataset_id: str) -> str:
        """获取数据集对应的 DuckDB 表名"""
        if not self.dataset_exists(dataset_id):
            raise ValueError(f"数据集不存在: {dataset_id}")
        return f"dataset_{dataset_id}"

    def cleanup_expired_datasets(self) -> int:
        """
        清理过期的数据集

        Returns:
            清理的数据集数量
        """
        now = datetime.now()
        expired_ids = []

        for dataset_id, metadata in self.datasets.items():
            age = now - metadata.created_at
            if age > timedelta(hours=self.DATASET_TTL_HOURS):
                expired_ids.append(dataset_id)

        cleaned_count = 0
        for dataset_id in expired_ids:
            try:
                self.delete_dataset(dataset_id)
                cleaned_count += 1
            except Exception as e:
                log.error(f"清理数据集失败: {dataset_id} - {e}")

        if cleaned_count > 0:
            log.info(f"已清理 {cleaned_count} 个过期数据集")

        return cleaned_count

    def delete_dataset(self, dataset_id: str):
        """
        删除数据集

        Args:
            dataset_id: 数据集ID
        """
        if dataset_id not in self.datasets:
            raise ValueError(f"数据集不存在: {dataset_id}")

        metadata = self.datasets[dataset_id]

        # 删除 DuckDB 表
        table_name = f"dataset_{dataset_id}"
        conn = self._get_connection()
        try:
            conn.execute(f"DROP TABLE IF EXISTS {table_name}")
            log.info(f"已删除 DuckDB 表: {table_name}")
        finally:
            conn.close()

        # 删除上传的文件（可选）
        try:
            file_path = Path(metadata.file_path)
            if file_path.exists():
                file_path.unlink()
                log.info(f"已删除文件: {file_path}")
        except Exception as e:
            log.warning(f"删除文件失败: {e}")

        # 从缓存中移除
        del self.datasets[dataset_id]
        log.info(f"数据集 {dataset_id} 已删除")

    def get_all_datasets(self) -> List[DatasetMetadata]:
        """获取所有数据集列表"""
        return list(self.datasets.values())

    def get_stats(self) -> Dict[str, Any]:
        """获取数据集统计信息"""
        total_rows = sum(m.row_count for m in self.datasets.values())
        total_size = sum(m.size_bytes for m in self.datasets.values())

        return {
            "total_datasets": len(self.datasets),
            "total_rows": total_rows,
            "total_size_bytes": total_size,
            "ttl_hours": self.DATASET_TTL_HOURS
        }


# 全局单例
_dataset_manager = None


def get_dataset_manager() -> DatasetManager:
    """获取 DatasetManager 单例"""
    global _dataset_manager
    if _dataset_manager is None:
        _dataset_manager = DatasetManager()
    return _dataset_manager
