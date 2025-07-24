#!/usr/bin/env python3
"""
API数据存储管理器
负责将API获取的数据存储到临时数据库文件中
"""

import sqlite3
import pandas as pd
import json
import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from pathlib import Path
import uuid
import hashlib

logger = logging.getLogger(__name__)

class APIDataStorage:
    """API数据存储管理器"""
    
    def __init__(self, storage_dir: str = "data/api_storage"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_db = self.storage_dir / "metadata.db"
        self._init_metadata_db()
    
    def _init_metadata_db(self):
        """初始化元数据数据库"""
        try:
            with sqlite3.connect(self.metadata_db) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS storage_sessions (
                        session_id TEXT PRIMARY KEY,
                        session_name TEXT NOT NULL,
                        description TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        api_name TEXT,
                        endpoint_name TEXT,
                        total_records INTEGER DEFAULT 0,
                        file_path TEXT,
                        status TEXT DEFAULT 'active'
                    )
                """)
                
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS data_operations (
                        operation_id TEXT PRIMARY KEY,
                        session_id TEXT,
                        operation_type TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        records_affected INTEGER,
                        operation_details TEXT,
                        FOREIGN KEY (session_id) REFERENCES storage_sessions (session_id)
                    )
                """)
                
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_sessions_api 
                    ON storage_sessions (api_name, endpoint_name)
                """)
                
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_operations_session 
                    ON data_operations (session_id, timestamp)
                """)
                
                conn.commit()
                logger.info("元数据数据库初始化完成")
        except Exception as e:
            logger.error(f"初始化元数据数据库失败: {e}")
            raise
    
    def create_storage_session(self, 
                             session_name: str,
                             api_name: str,
                             endpoint_name: str,
                             description: str = None) -> tuple[bool, str, str]:
        """创建存储会话"""
        try:
            session_id = str(uuid.uuid4())
            file_name = f"{api_name}_{endpoint_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            file_path = self.storage_dir / file_name
            
            with sqlite3.connect(self.metadata_db) as conn:
                conn.execute("""
                    INSERT INTO storage_sessions 
                    (session_id, session_name, description, api_name, endpoint_name, file_path)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (session_id, session_name, description, api_name, endpoint_name, str(file_path)))
                conn.commit()
            
            # 创建数据存储文件
            with sqlite3.connect(file_path) as data_conn:
                data_conn.execute("""
                    CREATE TABLE IF NOT EXISTS api_data (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        data_hash TEXT UNIQUE,
                        raw_data TEXT,
                        processed_data TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        source_params TEXT
                    )
                """)
                data_conn.commit()
            
            self._log_operation(session_id, "create_session", 0, 
                              f"创建存储会话: {session_name}")
            
            return True, session_id, f"存储会话创建成功: {session_name}"
            
        except Exception as e:
            logger.error(f"创建存储会话失败: {e}")
            return False, "", f"创建存储会话失败: {str(e)}"
    
    def store_api_data(self, 
                      session_id: str,
                      raw_data: Any,
                      processed_data: Any = None,
                      source_params: Dict[str, Any] = None) -> tuple[bool, int, str]:
        """存储API数据"""
        try:
            # 获取会话信息
            session_info = self._get_session_info(session_id)
            if not session_info:
                return False, 0, f"存储会话不存在: {session_id}"
            
            file_path = session_info['file_path']
            
            # 生成数据哈希（用于去重）
            data_str = json.dumps(raw_data, sort_keys=True, default=str)
            data_hash = hashlib.md5(data_str.encode()).hexdigest()
            
            with sqlite3.connect(file_path) as conn:
                # 检查是否已存在相同数据
                cursor = conn.execute("SELECT id FROM api_data WHERE data_hash = ?", (data_hash,))
                if cursor.fetchone():
                    return True, 0, "数据已存在，跳过重复存储"
                
                # 存储数据
                conn.execute("""
                    INSERT INTO api_data (data_hash, raw_data, processed_data, source_params)
                    VALUES (?, ?, ?, ?)
                """, (
                    data_hash,
                    json.dumps(raw_data, default=str),
                    json.dumps(processed_data, default=str) if processed_data else None,
                    json.dumps(source_params, default=str) if source_params else None
                ))
                
                records_added = conn.total_changes
                conn.commit()
            
            # 更新会话统计
            self._update_session_stats(session_id)
            
            # 记录操作
            self._log_operation(session_id, "store_data", records_added, 
                              f"存储API数据，哈希: {data_hash[:8]}...")
            
            return True, records_added, f"数据存储成功，新增 {records_added} 条记录"
            
        except Exception as e:
            logger.error(f"存储API数据失败: {e}")
            return False, 0, f"存储API数据失败: {str(e)}"
    
    def get_stored_data(self, 
                       session_id: str,
                       limit: int = None,
                       offset: int = 0,
                       format_type: str = "json") -> tuple[bool, Any, str]:
        """获取存储的数据"""
        try:
            session_info = self._get_session_info(session_id)
            if not session_info:
                return False, None, f"存储会话不存在: {session_id}"
            
            file_path = session_info['file_path']
            
            with sqlite3.connect(file_path) as conn:
                conn.row_factory = sqlite3.Row
                
                # 构建查询
                query = "SELECT * FROM api_data ORDER BY timestamp DESC"
                params = []
                
                if limit:
                    query += " LIMIT ?"
                    params.append(limit)
                    
                if offset > 0:
                    query += " OFFSET ?"
                    params.append(offset)
                
                cursor = conn.execute(query, params)
                rows = cursor.fetchall()
            
            if not rows:
                return True, [], "没有找到存储的数据"
            
            # 转换数据格式
            if format_type == "json":
                data = []
                for row in rows:
                    item = {
                        'id': row['id'],
                        'raw_data': json.loads(row['raw_data']),
                        'processed_data': json.loads(row['processed_data']) if row['processed_data'] else None,
                        'source_params': json.loads(row['source_params']) if row['source_params'] else None,
                        'timestamp': row['timestamp']
                    }
                    data.append(item)
                return True, data, f"获取到 {len(data)} 条记录"
            
            elif format_type == "dataframe":
                # 提取原始数据并转换为DataFrame
                raw_data_list = []
                for row in rows:
                    raw_data = json.loads(row['raw_data'])
                    if isinstance(raw_data, list):
                        raw_data_list.extend(raw_data)
                    else:
                        raw_data_list.append(raw_data)
                
                if raw_data_list:
                    df = pd.DataFrame(raw_data_list)
                    return True, df, f"转换为DataFrame成功，共 {len(df)} 行"
                else:
                    return True, pd.DataFrame(), "数据为空"
            
            elif format_type == "excel":
                # 转换为Excel格式
                success, df, message = self.get_stored_data(session_id, limit, offset, "dataframe")
                if success and not df.empty:
                    from io import BytesIO
                    excel_buffer = BytesIO()
                    with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                        df.to_excel(writer, index=False, sheet_name='API_Data')
                    excel_bytes = excel_buffer.getvalue()
                    return True, excel_bytes, f"转换为Excel成功，共 {len(df)} 行"
                else:
                    return False, None, "无法转换为Excel格式"
            
            else:
                return False, None, f"不支持的格式类型: {format_type}"
                
        except Exception as e:
            logger.error(f"获取存储数据失败: {e}")
            return False, None, f"获取存储数据失败: {str(e)}"
    
    def list_storage_sessions(self, 
                            api_name: str = None,
                            status: str = "active") -> tuple[bool, List[Dict[str, Any]], str]:
        """列出存储会话"""
        try:
            with sqlite3.connect(self.metadata_db) as conn:
                conn.row_factory = sqlite3.Row
                
                query = "SELECT * FROM storage_sessions WHERE status = ?"
                params = [status]
                
                if api_name:
                    query += " AND api_name = ?"
                    params.append(api_name)
                
                query += " ORDER BY created_at DESC"
                
                cursor = conn.execute(query, params)
                rows = cursor.fetchall()
            
            sessions = []
            for row in rows:
                session = {
                    'session_id': row['session_id'],
                    'session_name': row['session_name'],
                    'description': row['description'],
                    'api_name': row['api_name'],
                    'endpoint_name': row['endpoint_name'],
                    'total_records': row['total_records'],
                    'created_at': row['created_at'],
                    'updated_at': row['updated_at'],
                    'status': row['status'],
                    'file_path': row['file_path']  # 添加file_path字段
                }
                sessions.append(session)
            
            return True, sessions, f"找到 {len(sessions)} 个存储会话"
            
        except Exception as e:
            logger.error(f"列出存储会话失败: {e}")
            return False, [], f"列出存储会话失败: {str(e)}"
    
    def delete_storage_session(self, session_id: str) -> tuple[bool, str]:
        """删除存储会话"""
        try:
            session_info = self._get_session_info(session_id)
            if not session_info:
                return False, f"存储会话不存在: {session_id}"
            
            file_path = Path(session_info['file_path'])
            
            # 删除数据文件
            if file_path.exists():
                file_path.unlink()
            
            # 更新会话状态
            with sqlite3.connect(self.metadata_db) as conn:
                conn.execute(
                    "UPDATE storage_sessions SET status = 'deleted', updated_at = CURRENT_TIMESTAMP WHERE session_id = ?",
                    (session_id,)
                )
                conn.commit()
            
            self._log_operation(session_id, "delete_session", 0, "删除存储会话")
            
            return True, f"存储会话删除成功: {session_info['session_name']}"
            
        except Exception as e:
            logger.error(f"删除存储会话失败: {e}")
            return False, f"删除存储会话失败: {str(e)}"
    
    def export_session_data(self, 
                          session_id: str,
                          export_path: str,
                          format_type: str = "excel") -> tuple[bool, str]:
        """导出会话数据"""
        try:
            success, data, message = self.get_stored_data(session_id, format_type="dataframe")
            if not success or data.empty:
                return False, f"无法获取数据进行导出: {message}"
            
            export_path = Path(export_path)
            export_path.parent.mkdir(parents=True, exist_ok=True)
            
            if format_type == "excel":
                data.to_excel(export_path, index=False)
            elif format_type == "csv":
                data.to_csv(export_path, index=False, encoding='utf-8-sig')
            elif format_type == "json":
                data.to_json(export_path, orient='records', force_ascii=False, indent=2)
            else:
                return False, f"不支持的导出格式: {format_type}"
            
            session_info = self._get_session_info(session_id)
            self._log_operation(session_id, "export_data", len(data), 
                              f"导出数据到: {export_path}")
            
            return True, f"数据导出成功: {export_path} ({len(data)} 行)"
            
        except Exception as e:
            logger.error(f"导出会话数据失败: {e}")
            return False, f"导出会话数据失败: {str(e)}"
    
    def _get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取会话信息"""
        try:
            with sqlite3.connect(self.metadata_db) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    "SELECT * FROM storage_sessions WHERE session_id = ?",
                    (session_id,)
                )
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"获取会话信息失败: {e}")
            return None
    
    def _update_session_stats(self, session_id: str):
        """更新会话统计信息"""
        try:
            session_info = self._get_session_info(session_id)
            if not session_info:
                return
            
            file_path = session_info['file_path']
            
            with sqlite3.connect(file_path) as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM api_data")
                total_records = cursor.fetchone()[0]
            
            with sqlite3.connect(self.metadata_db) as conn:
                conn.execute(
                    "UPDATE storage_sessions SET total_records = ?, updated_at = CURRENT_TIMESTAMP WHERE session_id = ?",
                    (total_records, session_id)
                )
                conn.commit()
                
        except Exception as e:
            logger.error(f"更新会话统计失败: {e}")
    
    def _log_operation(self, session_id: str, operation_type: str, 
                      records_affected: int, details: str):
        """记录操作日志"""
        try:
            operation_id = str(uuid.uuid4())
            with sqlite3.connect(self.metadata_db) as conn:
                conn.execute("""
                    INSERT INTO data_operations 
                    (operation_id, session_id, operation_type, records_affected, operation_details)
                    VALUES (?, ?, ?, ?, ?)
                """, (operation_id, session_id, operation_type, records_affected, details))
                conn.commit()
        except Exception as e:
            logger.warning(f"记录操作日志失败: {e}")
    
    def get_session_operations(self, session_id: str) -> tuple[bool, List[Dict[str, Any]], str]:
        """获取会话操作历史"""
        try:
            with sqlite3.connect(self.metadata_db) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT * FROM data_operations 
                    WHERE session_id = ? 
                    ORDER BY timestamp DESC
                """, (session_id,))
                rows = cursor.fetchall()
            
            operations = []
            for row in rows:
                operation = {
                    'operation_id': row['operation_id'],
                    'operation_type': row['operation_type'],
                    'timestamp': row['timestamp'],
                    'records_affected': row['records_affected'],
                    'operation_details': row['operation_details']
                }
                operations.append(operation)
            
            return True, operations, f"找到 {len(operations)} 个操作记录"
            
        except Exception as e:
            logger.error(f"获取会话操作历史失败: {e}")
            return False, [], f"获取会话操作历史失败: {str(e)}"

# 创建全局实例
api_data_storage = APIDataStorage()