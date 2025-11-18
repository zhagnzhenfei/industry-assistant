"""
数据库操作工具集
提供PostgreSQL、SQLite等数据库的常用操作
"""

import json
import sqlite3
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Dict, Any, List, Optional
from datetime import datetime
import os
from pathlib import Path


class DatabaseOperations:
    """数据库操作工具类"""

    def __init__(self):
        self.connections = {}

    def test_connection(self, db_type: str, connection_params: Dict[str, Any]) -> Dict[str, Any]:
        """测试数据库连接"""
        try:
            if db_type == 'sqlite':
                return self._test_sqlite_connection(connection_params)
            elif db_type == 'postgresql':
                return self._test_postgresql_connection(connection_params)
            else:
                return {
                    "success": False,
                    "error": f"不支持的数据库类型: {db_type}"
                }
        except Exception as e:
            return {
                "success": False,
                "error": f"连接测试失败: {str(e)}"
            }

    def _test_sqlite_connection(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """测试SQLite连接"""
        db_path = params.get('database', '')
        if not db_path:
            return {
                "success": False,
                "error": "数据库路径不能为空"
            }

        try:
            # 检查数据库文件是否存在
            if not os.path.exists(db_path):
                return {
                    "success": False,
                    "error": f"数据库文件不存在: {db_path}"
                }

            # 尝试连接
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT sqlite_version()")
            version = cursor.fetchone()[0]
            conn.close()

            return {
                "success": True,
                "message": f"SQLite连接成功，版本: {version}",
                "database_type": "SQLite",
                "version": version
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"SQLite连接失败: {str(e)}"
            }

    def _test_postgresql_connection(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """测试PostgreSQL连接"""
        required_params = ['host', 'database', 'user']
        for param in required_params:
            if not params.get(param):
                return {
                    "success": False,
                    "error": f"缺少必需参数: {param}"
                }

        try:
            conn = psycopg2.connect(
                host=params['host'],
                port=params.get('port', 5432),
                database=params['database'],
                user=params['user'],
                password=params.get('password', ''),
                connect_timeout=5
            )

            cursor = conn.cursor()
            cursor.execute("SELECT version()")
            version = cursor.fetchone()[0]
            conn.close()

            return {
                "success": True,
                "message": "PostgreSQL连接成功",
                "database_type": "PostgreSQL",
                "version": version
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"PostgreSQL连接失败: {str(e)}"
            }

    def execute_query(self, db_type: str, connection_params: Dict[str, Any], query: str, params: List[Any] = None) -> Dict[str, Any]:
        """执行SQL查询"""
        try:
            if db_type == 'sqlite':
                return self._execute_sqlite_query(connection_params, query, params)
            elif db_type == 'postgresql':
                return self._execute_postgresql_query(connection_params, query, params)
            else:
                return {
                    "success": False,
                    "error": f"不支持的数据库类型: {db_type}"
                }
        except Exception as e:
            return {
                "success": False,
                "error": f"查询执行失败: {str(e)}"
            }

    def _execute_sqlite_query(self, params: Dict[str, Any], query: str, query_params: List[Any] = None) -> Dict[str, Any]:
        """执行SQLite查询"""
        db_path = params.get('database', '')
        if not db_path:
            return {
                "success": False,
                "error": "数据库路径不能为空"
            }

        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row  # 使查询结果支持列名访问
            cursor = conn.cursor()

            # 执行查询
            if query_params:
                cursor.execute(query, query_params)
            else:
                cursor.execute(query)

            # 判断是否为SELECT查询
            is_select = query.strip().lower().startswith('select')

            if is_select:
                # 获取查询结果
                rows = cursor.fetchall()
                columns = [description[0] for description in cursor.description] if cursor.description else []

                results = []
                for row in rows:
                    results.append(dict(row))

                conn.close()

                return {
                    "success": True,
                    "query_type": "SELECT",
                    "columns": columns,
                    "data": results,
                    "row_count": len(results),
                    "message": f"查询成功，返回 {len(results)} 行数据"
                }
            else:
                # 非SELECT查询（INSERT, UPDATE, DELETE等）
                affected_rows = cursor.rowcount
                lastrowid = cursor.lastrowid if query.strip().lower().startswith('insert') else None
                conn.commit()
                conn.close()

                return {
                    "success": True,
                    "query_type": "NON_SELECT",
                    "affected_rows": affected_rows,
                    "last_insert_id": lastrowid,
                    "message": f"操作成功，影响 {affected_rows} 行数据"
                }

        except Exception as e:
            return {
                "success": False,
                "error": f"SQLite查询失败: {str(e)}"
            }

    def _execute_postgresql_query(self, params: Dict[str, Any], query: str, query_params: List[Any] = None) -> Dict[str, Any]:
        """执行PostgreSQL查询"""
        try:
            conn = psycopg2.connect(
                host=params['host'],
                port=params.get('port', 5432),
                database=params['database'],
                user=params['user'],
                password=params.get('password', '')
            )

            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # 执行查询
            if query_params:
                cursor.execute(query, query_params)
            else:
                cursor.execute(query)

            # 判断是否为SELECT查询
            is_select = query.strip().lower().startswith('select')

            if is_select:
                # 获取查询结果
                rows = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description] if cursor.description else []

                results = [dict(row) for row in rows]

                cursor.close()
                conn.close()

                return {
                    "success": True,
                    "query_type": "SELECT",
                    "columns": columns,
                    "data": results,
                    "row_count": len(results),
                    "message": f"查询成功，返回 {len(results)} 行数据"
                }
            else:
                # 非SELECT查询
                affected_rows = cursor.rowcount
                conn.commit()

                cursor.close()
                conn.close()

                return {
                    "success": True,
                    "query_type": "NON_SELECT",
                    "affected_rows": affected_rows,
                    "message": f"操作成功，影响 {affected_rows} 行数据"
                }

        except Exception as e:
            return {
                "success": False,
                "error": f"PostgreSQL查询失败: {str(e)}"
            }

    def get_database_info(self, db_type: str, connection_params: Dict[str, Any]) -> Dict[str, Any]:
        """获取数据库信息"""
        try:
            if db_type == 'sqlite':
                return self._get_sqlite_info(connection_params)
            elif db_type == 'postgresql':
                return self._get_postgresql_info(connection_params)
            else:
                return {
                    "success": False,
                    "error": f"不支持的数据库类型: {db_type}"
                }
        except Exception as e:
            return {
                "success": False,
                "error": f"获取数据库信息失败: {str(e)}"
            }

    def _get_sqlite_info(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """获取SQLite数据库信息"""
        db_path = params.get('database', '')
        if not db_path:
            return {
                "success": False,
                "error": "数据库路径不能为空"
            }

        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # 获取所有表
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]

            # 获取每个表的信息
            table_info = []
            for table in tables:
                cursor.execute(f"PRAGMA table_info({table})")
                columns = []
                for col in cursor.fetchall():
                    columns.append({
                        "name": col[1],
                        "type": col[2],
                        "nullable": not col[3],
                        "default": col[4],
                        "primary_key": bool(col[5])
                    })

                # 获取表的数据量
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                row_count = cursor.fetchone()[0]

                table_info.append({
                    "name": table,
                    "columns": columns,
                    "row_count": row_count
                })

            conn.close()

            return {
                "success": True,
                "database_type": "SQLite",
                "database_path": db_path,
                "tables": table_info,
                "total_tables": len(tables)
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"获取SQLite信息失败: {str(e)}"
            }

    def _get_postgresql_info(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """获取PostgreSQL数据库信息"""
        try:
            conn = psycopg2.connect(
                host=params['host'],
                port=params.get('port', 5432),
                database=params['database'],
                user=params['user'],
                password=params.get('password', '')
            )

            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # 获取所有表
            cursor.execute("""
                SELECT table_name, table_type
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)
            tables = cursor.fetchall()

            # 获取每个表的详细信息
            table_info = []
            for table in tables:
                table_name = table['table_name']

                # 获取列信息
                cursor.execute("""
                    SELECT column_name, data_type, is_nullable, column_default
                    FROM information_schema.columns
                    WHERE table_name = %s
                    ORDER BY ordinal_position
                """, (table_name,))
                columns = cursor.fetchall()

                # 获取主键信息
                cursor.execute("""
                    SELECT kcu.column_name
                    FROM information_schema.table_constraints tc
                    JOIN information_schema.key_column_usage kcu
                    ON tc.constraint_name = kcu.constraint_name
                    WHERE tc.table_name = %s AND tc.constraint_type = 'PRIMARY KEY'
                """, (table_name,))
                primary_keys = [row['column_name'] for row in cursor.fetchall()]

                # 获取数据量
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                row_count = cursor.fetchone()['count']

                # 格式化列信息
                formatted_columns = []
                for col in columns:
                    formatted_columns.append({
                        "name": col['column_name'],
                        "type": col['data_type'],
                        "nullable": col['is_nullable'] == 'YES',
                        "default": col['column_default'],
                        "primary_key": col['column_name'] in primary_keys
                    })

                table_info.append({
                    "name": table_name,
                    "type": table['table_type'],
                    "columns": formatted_columns,
                    "row_count": row_count
                })

            # 获取数据库大小
            cursor.execute("SELECT pg_database_size(current_database())")
            db_size = cursor.fetchone()['pg_database_size']

            cursor.close()
            conn.close()

            return {
                "success": True,
                "database_type": "PostgreSQL",
                "database_name": params['database'],
                "tables": table_info,
                "total_tables": len(tables),
                "database_size_bytes": db_size,
                "database_size_mb": round(db_size / (1024 * 1024), 2)
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"获取PostgreSQL信息失败: {str(e)}"
            }

    def create_backup(self, db_type: str, connection_params: Dict[str, Any], backup_path: str) -> Dict[str, Any]:
        """创建数据库备份（SQLite）"""
        try:
            if db_type != 'sqlite':
                return {
                    "success": False,
                    "error": "目前只支持SQLite数据库备份"
                }

            db_path = connection_params.get('database', '')
            if not db_path:
                return {
                    "success": False,
                    "error": "数据库路径不能为空"
                }

            if not os.path.exists(db_path):
                return {
                    "success": False,
                    "error": f"数据库文件不存在: {db_path}"
                }

            # 确保备份目录存在
            backup_dir = Path(backup_path).parent
            backup_dir.mkdir(parents=True, exist_ok=True)

            # 创建备份
            source_conn = sqlite3.connect(db_path)
            backup_conn = sqlite3.connect(backup_path)

            with backup_conn:
                source_conn.backup(backup_conn)

            source_conn.close()
            backup_conn.close()

            return {
                "success": True,
                "message": f"数据库备份创建成功",
                "source_database": db_path,
                "backup_path": backup_path,
                "backup_size": os.path.getsize(backup_path)
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"创建备份失败: {str(e)}"
            }


# 统一的数据库操作接口
def database_operation(operation: str, **kwargs) -> Dict[str, Any]:
    """统一的数据库操作接口"""
    db_ops = DatabaseOperations()

    operations = {
        'test_connection': db_ops.test_connection,
        'execute_query': db_ops.execute_query,
        'get_info': db_ops.get_database_info,
        'create_backup': db_ops.create_backup
    }

    if operation not in operations:
        return {
            "success": False,
            "error": f"不支持的操作: {operation}"
        }

    try:
        return operations[operation](**kwargs)
    except Exception as e:
        return {
            "success": False,
            "error": f"操作失败: {str(e)}"
        }


if __name__ == "__main__":
    # 测试数据库操作
    test_params = {
        'database': 'test.db'
    }

    result = database_operation('test_connection', db_type='sqlite', connection_params=test_params)
    print(json.dumps(result, indent=2, ensure_ascii=False))