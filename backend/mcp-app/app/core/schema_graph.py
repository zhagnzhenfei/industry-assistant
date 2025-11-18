"""
数据库Schema图构建器
使用NetworkX构建表和列的图结构，支持智能子图查找
"""
import networkx as nx
import logging
from typing import List, Dict, Any, Set
import re

logger = logging.getLogger(__name__)


class SchemaGraph:
    """数据库Schema的图表示"""
    
    def __init__(self):
        """初始化Schema图"""
        self.graph = nx.DiGraph()
        self._built = False
    
    async def build_from_db(self, db_manager):
        """
        从数据库构建Schema图
        
        Args:
            db_manager: DatabaseManager实例
        """
        logger.info("开始构建Schema图...")
        
        try:
            # 1. 获取所有表信息
            tables = await db_manager.get_tables_info()
            
            # 2. 为每个表构建节点和边
            for table in tables:
                table_name = table['name']
                
                # 添加表节点
                self.graph.add_node(
                    table_name,
                    type='table',
                    comment=table.get('comment') or '',
                    row_count=table.get('row_count', 0),
                    columns_count=table.get('columns_count', 0)
                )
                
                # 获取表的详细schema
                schema = await db_manager.get_table_schema(
                    table_name,
                    include_samples=False
                )
                
                # 添加列节点
                for col in schema['columns']:
                    col_id = f"{table_name}.{col['name']}"
                    self.graph.add_node(
                        col_id,
                        type='column',
                        table=table_name,
                        column=col['name'],
                        data_type=col['type'],
                        comment=col.get('comment') or '',
                        not_null=col.get('not_null', False)
                    )
                    
                    # 添加边：表 -> 列
                    self.graph.add_edge(
                        table_name,
                        col_id,
                        relationship='has_column'
                    )
                
                # 添加外键关系边
                for fk in schema['foreign_keys']:
                    from_col_id = f"{table_name}.{fk['column_name']}"
                    to_col_id = f"{fk['foreign_table_name']}.{fk['foreign_column_name']}"
                    
                    self.graph.add_edge(
                        from_col_id,
                        to_col_id,
                        relationship='foreign_key'
                    )
                    
                    # 同时添加表级别的关系
                    self.graph.add_edge(
                        table_name,
                        fk['foreign_table_name'],
                        relationship='references'
                    )
            
            self._built = True
            logger.info(
                f"Schema图构建完成: "
                f"{len([n for n, d in self.graph.nodes(data=True) if d.get('type') == 'table'])}个表, "
                f"{len([n for n, d in self.graph.nodes(data=True) if d.get('type') == 'column'])}个列"
            )
            
        except Exception as e:
            logger.error(f"构建Schema图失败: {e}", exc_info=True)
            raise
    
    def find_relevant_subgraph(
        self,
        keywords: List[str],
        max_hops: int = 1
    ) -> nx.DiGraph:
        """
        根据关键词提取相关子图
        
        Args:
            keywords: 关键词列表
            max_hops: 最大跳数（邻居扩展深度）
            
        Returns:
            子图
        """
        if not self._built:
            raise RuntimeError("Schema图尚未构建，请先调用build_from_db")
        
        if not keywords:
            logger.warning("关键词列表为空，返回空子图")
            return nx.DiGraph()
        
        relevant_nodes = set()
        
        # 1. 找出所有匹配的节点
        for node, data in self.graph.nodes(data=True):
            for keyword in keywords:
                if self._semantic_match(keyword, node, data):
                    relevant_nodes.add(node)
                    logger.debug(f"匹配节点: {node} (关键词: {keyword})")
                    break
        
        # 2. 扩展邻居节点
        expanded_nodes = set(relevant_nodes)
        for node in relevant_nodes:
            # 获取指定跳数内的所有邻居
            neighbors = self._get_neighbors_within_hops(node, max_hops)
            expanded_nodes.update(neighbors)
        
        logger.info(
            f"找到{len(relevant_nodes)}个直接匹配节点, "
            f"扩展后共{len(expanded_nodes)}个节点"
        )
        
        # 3. 创建子图
        if not expanded_nodes:
            return nx.DiGraph()
        
        subgraph = self.graph.subgraph(expanded_nodes).copy()
        
        return subgraph
    
    def _semantic_match(
        self,
        keyword: str,
        node: str,
        data: Dict[str, Any]
    ) -> bool:
        """
        语义匹配：检查关键词是否匹配节点
        
        Args:
            keyword: 关键词
            node: 节点ID
            data: 节点数据
            
        Returns:
            是否匹配
        """
        keyword_lower = keyword.lower()
        
        # 1. 匹配节点ID
        if keyword_lower in node.lower():
            return True
        
        # 2. 匹配节点注释
        comment = data.get('comment', '')
        if comment and keyword_lower in comment.lower():
            return True
        
        # 3. 对于表节点，匹配表名（去掉下划线）
        if data.get('type') == 'table':
            table_name_no_underscore = node.replace('_', '')
            keyword_no_space = keyword.replace(' ', '').replace('_', '')
            if keyword_no_space.lower() in table_name_no_underscore.lower():
                return True
        
        # 4. 对于列节点，匹配列名
        if data.get('type') == 'column':
            column_name = data.get('column', '')
            if keyword_lower in column_name.lower():
                return True
        
        # 5. 模糊匹配（拼音、缩写等）
        # 如"公司"匹配"company"
        if self._fuzzy_match(keyword_lower, node.lower(), comment.lower()):
            return True
        
        return False
    
    def _fuzzy_match(
        self,
        keyword: str,
        node: str,
        comment: str
    ) -> bool:
        """
        模糊匹配
        
        支持：
        - 部分匹配
        - 缩写匹配
        """
        # 部分匹配（至少3个字符）
        if len(keyword) >= 3:
            # 检查关键词是否是节点或注释的子串
            if keyword in node or keyword in comment:
                return True
        
        # TODO: 可以添加更多模糊匹配规则
        # - 拼音匹配
        # - 同义词匹配
        # - 缩写匹配
        
        return False
    
    def _get_neighbors_within_hops(
        self,
        node: str,
        max_hops: int
    ) -> Set[str]:
        """
        获取指定跳数内的所有邻居节点
        
        Args:
            node: 起始节点
            max_hops: 最大跳数
            
        Returns:
            邻居节点集合
        """
        if max_hops <= 0:
            return {node}
        
        neighbors = {node}
        current_level = {node}
        
        for _ in range(max_hops):
            next_level = set()
            for n in current_level:
                # 获取所有相邻节点（包括前驱和后继）
                predecessors = set(self.graph.predecessors(n))
                successors = set(self.graph.successors(n))
                next_level.update(predecessors)
                next_level.update(successors)
            
            neighbors.update(next_level)
            current_level = next_level - neighbors
            
            if not current_level:
                break
        
        return neighbors
    
    def get_tables_from_subgraph(self, subgraph: nx.DiGraph) -> List[str]:
        """
        从子图中提取所有表名
        
        Args:
            subgraph: 子图
            
        Returns:
            表名列表
        """
        tables = [
            node
            for node, data in subgraph.nodes(data=True)
            if data.get('type') == 'table'
        ]
        return sorted(tables)
    
    def get_related_tables(
        self,
        table_name: str,
        include_referenced: bool = True,
        include_referencing: bool = True
    ) -> List[str]:
        """
        获取与指定表相关的表
        
        Args:
            table_name: 表名
            include_referenced: 是否包含被引用的表（通过外键）
            include_referencing: 是否包含引用此表的表
            
        Returns:
            相关表列表
        """
        if not self._built:
            raise RuntimeError("Schema图尚未构建")
        
        if table_name not in self.graph:
            return []
        
        related = set()
        
        # 获取通过外键关系相关的表
        for _, target, data in self.graph.out_edges(table_name, data=True):
            if data.get('relationship') == 'references':
                if include_referenced:
                    related.add(target)
        
        for source, _, data in self.graph.in_edges(table_name, data=True):
            if data.get('relationship') == 'references':
                if include_referencing:
                    related.add(source)
        
        return sorted(list(related))
    
    def to_dict(self) -> Dict[str, Any]:
        """
        将图转换为字典格式
        
        Returns:
            {
                "nodes": [...],
                "edges": [...]
            }
        """
        return nx.node_link_data(self.graph)
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取Schema图统计信息
        
        Returns:
            统计信息字典
        """
        table_nodes = [
            n for n, d in self.graph.nodes(data=True)
            if d.get('type') == 'table'
        ]
        column_nodes = [
            n for n, d in self.graph.nodes(data=True)
            if d.get('type') == 'column'
        ]
        
        fk_edges = [
            e for e in self.graph.edges(data=True)
            if e[2].get('relationship') == 'foreign_key'
        ]
        
        return {
            "total_nodes": self.graph.number_of_nodes(),
            "total_edges": self.graph.number_of_edges(),
            "table_count": len(table_nodes),
            "column_count": len(column_nodes),
            "foreign_key_count": len(fk_edges),
            "built": self._built
        }

