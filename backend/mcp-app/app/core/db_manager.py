"""
数据库连接管理器
提供PostgreSQL连接池管理、SQL安全验证和查询执行
"""
import asyncpg
import sqlparse
import logging
import re
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import os

logger = logging.getLogger(__name__)


class DatabaseManager:
    """PostgreSQL数据库连接管理器"""
    
    # SQL安全白名单 - 只允许SELECT
    FORBIDDEN_KEYWORDS = [
        'DELETE', 'UPDATE', 'INSERT', 'DROP',
        'CREATE', 'ALTER', 'TRUNCATE', 'EXEC',
        'EXECUTE', 'GRANT', 'REVOKE', 'COMMIT',
        'ROLLBACK', 'SAVEPOINT'
    ]
    
    # 查询限制
    MAX_RESULT_ROWS = 1000
    QUERY_TIMEOUT = 30  # 秒
    
    def __init__(
        self,
        host: str = None,
        port: int = None,
        user: str = None,
        password: str = None,
        database: str = None,
        min_connections: int = 1,
        max_connections: int = 10
    ):
        """
        初始化数据库管理器
        
        Args:
            host: 数据库主机
            port: 数据库端口
            user: 数据库用户
            password: 数据库密码
            database: 数据库名
            min_connections: 最小连接数
            max_connections: 最大连接数
        """
        self.host = host or os.getenv('POSTGRES_HOST', 'localhost')
        self.port = port or int(os.getenv('POSTGRES_PORT', '5432'))
        self.user = user or os.getenv('POSTGRES_USER', 'postgres')
        self.password = password or os.getenv('POSTGRES_PASSWORD', '')
        self.database = database or os.getenv('POSTGRES_DB', 'postgres')
        
        self.min_connections = min_connections
        self.max_connections = max_connections
        self.pool: Optional[asyncpg.Pool] = None
        
        logger.info(f"数据库管理器初始化: {self.user}@{self.host}:{self.port}/{self.database}")
    
    async def connect(self):
        """创建连接池"""
        if self.pool is not None:
            logger.warning("连接池已存在，跳过创建")
            return
        
        try:
            self.pool = await asyncpg.create_pool(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database,
                min_size=self.min_connections,
                max_size=self.max_connections,
                command_timeout=self.QUERY_TIMEOUT
            )
            logger.info(f"数据库连接池创建成功: {self.min_connections}-{self.max_connections}个连接")
            
            # 测试连接
            async with self.pool.acquire() as conn:
                version = await conn.fetchval('SELECT version()')
                logger.info(f"PostgreSQL版本: {version[:50]}...")
                
        except Exception as e:
            logger.error(f"创建数据库连接池失败: {e}", exc_info=True)
            raise
    
    async def close(self):
        """关闭连接池"""
        if self.pool:
            await self.pool.close()
            logger.info("数据库连接池已关闭")
            self.pool = None
    
    def validate_sql_safety(self, sql: str) -> Tuple[bool, Optional[str]]:
        """
        验证SQL安全性
        
        Args:
            sql: SQL语句
            
        Returns:
            (is_safe, error_message)
        """
        # 1. 检查SQL是否为空
        if not sql or not sql.strip():
            return False, "SQL语句不能为空"
        
        sql_upper = sql.upper()
        
        # 2. 检查禁止的关键字
        for keyword in self.FORBIDDEN_KEYWORDS:
            # 使用词边界匹配，避免误杀（如SELECT中的SELECT）
            pattern = r'\b' + keyword + r'\b'
            if re.search(pattern, sql_upper):
                return False, f"禁止使用{keyword}语句，只允许SELECT查询"
        
        # 3. 解析SQL，确保只有SELECT语句
        try:
            parsed = sqlparse.parse(sql)
            if not parsed:
                return False, "无法解析SQL语句"
            
            for statement in parsed:
                # 获取语句类型
                stmt_type = statement.get_type()
                if stmt_type != 'SELECT':
                    return False, f"只允许SELECT查询，检测到{stmt_type}语句"
                
        except Exception as e:
            return False, f"SQL解析失败: {str(e)}"
        
        # 4. 检查是否包含子查询中的修改操作
        # 简单检查：去掉注释后看是否还有禁止关键字
        sql_no_comments = sqlparse.format(
            sql,
            strip_comments=True
        ).upper()
        
        for keyword in self.FORBIDDEN_KEYWORDS:
            if keyword in sql_no_comments:
                return False, f"SQL中不能包含{keyword}关键字"
        
        return True, None
    
    async def execute_query(
        self,
        sql: str,
        params: Optional[List] = None
    ) -> Dict[str, Any]:
        """
        执行SQL查询
        
        Args:
            sql: SQL语句
            params: 查询参数
            
        Returns:
            {
                "success": bool,
                "data": List[Dict] or None,
                "row_count": int,
                "error_type": str (如果失败),
                "error_message": str (如果失败),
                "hint": str (如果有),
                "fix_suggestions": List[str]
            }
        """
        # 1. 安全验证
        is_safe, error_msg = self.validate_sql_safety(sql)
        if not is_safe:
            return {
                "success": False,
                "error_type": "security_error",
                "error_message": error_msg,
                "sql": sql,
                "fix_suggestions": [
                    "只允许执行SELECT查询",
                    "请移除任何修改数据的操作"
                ]
            }
        
        # 2. 检查连接池
        if not self.pool:
            return {
                "success": False,
                "error_type": "connection_error",
                "error_message": "数据库连接池未初始化",
                "fix_suggestions": ["请先调用connect()方法"]
            }
        
        # 3. 执行查询
        try:
            async with self.pool.acquire() as conn:
                # 添加LIMIT限制（如果没有）
                limited_sql = self._add_limit_if_needed(sql)
                
                start_time = datetime.now()
                
                if params:
                    rows = await conn.fetch(limited_sql, *params)
                else:
                    rows = await conn.fetch(limited_sql)
                
                execution_time = (datetime.now() - start_time).total_seconds()
                
                # 转换为字典列表
                data = [dict(row) for row in rows]
                
                logger.info(
                    f"查询成功: {len(data)}行, "
                    f"耗时{execution_time:.3f}秒"
                )
                
                return {
                    "success": True,
                    "data": data,
                    "row_count": len(data),
                    "execution_time": execution_time,
                    "sql": limited_sql
                }
                
        except asyncpg.exceptions.UndefinedColumnError as e:
            # 列不存在错误
            return self._format_column_error(e, sql)
            
        except asyncpg.exceptions.UndefinedTableError as e:
            # 表不存在错误
            return self._format_table_error(e, sql)
            
        except asyncpg.exceptions.PostgresSyntaxError as e:
            # 语法错误
            return self._format_syntax_error(e, sql)
            
        except asyncpg.exceptions.DataError as e:
            # 数据类型错误
            return self._format_data_error(e, sql)
            
        except asyncpg.exceptions.QueryCanceledError:
            return {
                "success": False,
                "error_type": "timeout",
                "error_message": f"查询超时（超过{self.QUERY_TIMEOUT}秒）",
                "sql": sql,
                "fix_suggestions": [
                    "简化查询逻辑",
                    "添加WHERE条件减少数据量",
                    "添加适当的索引"
                ]
            }
            
        except Exception as e:
            logger.error(f"查询执行失败: {e}", exc_info=True)
            return {
                "success": False,
                "error_type": "execution_error",
                "error_message": str(e),
                "sql": sql,
                "fix_suggestions": [
                    "检查SQL语法",
                    "确认表和列名正确",
                    "查看完整错误信息"
                ]
            }
    
    def _add_limit_if_needed(self, sql: str) -> str:
        """如果SQL没有LIMIT子句，自动添加"""
        sql_upper = sql.upper()
        
        # 检查是否已有LIMIT
        if 'LIMIT' in sql_upper:
            return sql
        
        # 添加LIMIT
        return f"{sql.rstrip(';')} LIMIT {self.MAX_RESULT_ROWS}"
    
    def _format_column_error(
        self,
        error: asyncpg.exceptions.UndefinedColumnError,
        sql: str
    ) -> Dict[str, Any]:
        """格式化列不存在错误"""
        error_msg = str(error)
        
        # 提取列名
        match = re.search(r'column "([^"]+)" does not exist', error_msg)
        wrong_column = match.group(1) if match else "unknown"
        
        return {
            "success": False,
            "error_type": "column_not_found",
            "error_message": f'列 "{wrong_column}" 不存在',
            "hint": "请使用 sql_db_schema 工具查看可用的列",
            "sql": sql,
            "wrong_column": wrong_column,
            "fix_suggestions": [
                "检查列名拼写是否正确",
                "使用 sql_db_schema 查看表结构",
                f"列名可能需要加双引号: \"{wrong_column}\""
            ]
        }
    
    def _format_table_error(
        self,
        error: asyncpg.exceptions.UndefinedTableError,
        sql: str
    ) -> Dict[str, Any]:
        """格式化表不存在错误"""
        error_msg = str(error)
        
        # 提取表名
        match = re.search(r'relation "([^"]+)" does not exist', error_msg)
        wrong_table = match.group(1) if match else "unknown"
        
        return {
            "success": False,
            "error_type": "table_not_found",
            "error_message": f'表 "{wrong_table}" 不存在',
            "hint": "请使用 sql_db_list_tables 工具查看可用的表",
            "sql": sql,
            "wrong_table": wrong_table,
            "fix_suggestions": [
                "检查表名拼写是否正确",
                "使用 sql_db_list_tables 查看所有表",
                "确认表是否在正确的schema中"
            ]
        }
    
    def _format_syntax_error(
        self,
        error: asyncpg.exceptions.PostgresSyntaxError,
        sql: str
    ) -> Dict[str, Any]:
        """格式化SQL语法错误"""
        return {
            "success": False,
            "error_type": "syntax_error",
            "error_message": f"SQL语法错误: {str(error)}",
            "sql": sql,
            "fix_suggestions": [
                "检查SQL语法",
                "确认关键字拼写正确",
                "检查括号是否匹配",
                "检查逗号和引号"
            ]
        }
    
    def _format_data_error(
        self,
        error: asyncpg.exceptions.DataError,
        sql: str
    ) -> Dict[str, Any]:
        """格式化数据类型错误"""
        return {
            "success": False,
            "error_type": "data_type_error",
            "error_message": f"数据类型错误: {str(error)}",
            "sql": sql,
            "fix_suggestions": [
                "检查数据类型是否匹配",
                "使用类型转换: ::integer, ::text 等",
                "检查日期格式: YYYY-MM-DD"
            ]
        }
    
    async def get_tables_info(self) -> List[Dict[str, Any]]:
        """
        获取所有表信息（含注释和行数）
        
        Returns:
            [
                {
                    "name": "table_name",
                    "comment": "table comment",
                    "row_count": 100,
                    "columns_count": 10
                },
                ...
            ]
        """
        if not self.pool:
            raise RuntimeError("数据库连接池未初始化")
        
        sql = """
        SELECT 
            c.relname AS name,
            pg_catalog.obj_description(c.oid, 'pg_class') AS comment,
            c.reltuples::bigint AS row_count,
            (SELECT count(*) FROM information_schema.columns 
             WHERE table_name = c.relname AND table_schema = n.nspname) AS columns_count
        FROM pg_catalog.pg_class c
        LEFT JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
        WHERE c.relkind = 'r'
          AND n.nspname = 'public'
        ORDER BY c.relname;
        """
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(sql)
            return [dict(row) for row in rows]
    
    async def get_table_schema(
        self,
        table_name: str,
        include_samples: bool = True,
        sample_limit: int = 3
    ) -> Dict[str, Any]:
        """
        获取表的详细schema信息
        
        Args:
            table_name: 表名
            include_samples: 是否包含示例数据
            sample_limit: 示例数据行数
            
        Returns:
            {
                "table_name": str,
                "comment": str,
                "columns": [...],
                "primary_keys": [...],
                "foreign_keys": [...],
                "indexes": [...],
                "sample_data": [...] (如果include_samples=True)
            }
        """
        if not self.pool:
            raise RuntimeError("数据库连接池未初始化")
        
        async with self.pool.acquire() as conn:
            # 1. 获取表注释
            table_comment_sql = """
            SELECT pg_catalog.obj_description(c.oid, 'pg_class') AS comment
            FROM pg_catalog.pg_class c
            LEFT JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
            WHERE c.relname = $1 AND n.nspname = 'public';
            """
            table_comment = await conn.fetchval(table_comment_sql, table_name)
            
            # 2. 获取列信息
            columns_sql = """
            SELECT 
                a.attname AS name,
                pg_catalog.format_type(a.atttypid, a.atttypmod) AS type,
                a.attnotnull AS not_null,
                pg_catalog.col_description(a.attrelid, a.attnum) AS comment,
                pg_get_expr(d.adbin, d.adrelid) AS default_value
            FROM pg_catalog.pg_attribute a
            LEFT JOIN pg_catalog.pg_attrdef d ON (a.attrelid, a.attnum) = (d.adrelid, d.adnum)
            WHERE a.attrelid = $1::regclass
              AND a.attnum > 0
              AND NOT a.attisdropped
            ORDER BY a.attnum;
            """
            columns = await conn.fetch(columns_sql, table_name)
            
            # 3. 获取主键
            pk_sql = """
            SELECT a.attname
            FROM pg_index i
            JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
            WHERE i.indrelid = $1::regclass AND i.indisprimary;
            """
            primary_keys = [row['attname'] for row in await conn.fetch(pk_sql, table_name)]
            
            # 4. 获取外键
            fk_sql = """
            SELECT
                kcu.column_name,
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
              ON tc.constraint_name = kcu.constraint_name
            JOIN information_schema.constraint_column_usage AS ccu
              ON ccu.constraint_name = tc.constraint_name
            WHERE tc.constraint_type = 'FOREIGN KEY'
              AND tc.table_name = $1;
            """
            foreign_keys = [dict(row) for row in await conn.fetch(fk_sql, table_name)]
            
            # 5. 获取索引
            indexes_sql = """
            SELECT
                i.relname AS index_name,
                a.attname AS column_name,
                ix.indisunique AS is_unique
            FROM pg_class t
            JOIN pg_index ix ON t.oid = ix.indrelid
            JOIN pg_class i ON i.oid = ix.indexrelid
            JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = ANY(ix.indkey)
            WHERE t.relname = $1
              AND NOT ix.indisprimary;
            """
            indexes = [dict(row) for row in await conn.fetch(indexes_sql, table_name)]
            
            result = {
                "table_name": table_name,
                "comment": table_comment,
                "columns": [dict(col) for col in columns],
                "primary_keys": primary_keys,
                "foreign_keys": foreign_keys,
                "indexes": indexes
            }
            
            # 6. 获取示例数据
            if include_samples:
                sample_sql = f"SELECT * FROM {table_name} LIMIT $1"
                sample_rows = await conn.fetch(sample_sql, sample_limit)
                result["sample_data"] = [dict(row) for row in sample_rows]
            
            return result
    
    async def get_column_samples(
        self,
        table_name: str,
        column_name: str,
        limit: int = 10
    ) -> List[Any]:
        """
        获取某列的唯一样本值
        
        Args:
            table_name: 表名
            column_name: 列名
            limit: 样本数量
            
        Returns:
            [value1, value2, ...]
        """
        if not self.pool:
            raise RuntimeError("数据库连接池未初始化")
        
        sql = f"""
        SELECT DISTINCT {column_name}
        FROM {table_name}
        WHERE {column_name} IS NOT NULL
        LIMIT $1
        """
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(sql, limit)
            return [row[0] for row in rows]

