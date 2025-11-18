import time
import logging
from typing import List, Optional, Dict, Any
from sqlalchemy import and_, or_

from utils.database import default_manager
from models import Assistant, AssistantKnowledgeBase, AssistantMCPService
from .mcp_service_manager import MCPServiceManager

# 配置日志
logger = logging.getLogger(__name__)


class AssistantService:
    """智能体服务类"""
    
    def __init__(self):
        self.session_factory = default_manager.session_factory
        self.mcp_manager = MCPServiceManager()
    
    async def create_assistant(
        self, 
        user_id: str, 
        name: str, 
        prompt: str, 
        description: Optional[str] = None,
        enable_knowledge_base: bool = False,
        knowledge_base: Optional[List[Any]] = None,
        mcp_services: Optional[List[Any]] = None
    ) -> Dict[str, Any]:
        """创建智能体"""
        logger.info(f"开始创建智能体: user_id={user_id}, name={name}")
        
        with self.session_factory() as session:
            try:
                # 构建增强的提示词
                mcp_server_ids = []
                if mcp_services:
                    mcp_server_ids = [mcp.mcp_server_id for mcp in mcp_services]
                    logger.info(f"配置的MCP服务: {mcp_server_ids}")
                
                # 不再预生成增强提示词，只保存用户原始提示词
                # enhanced_prompt = await self.mcp_manager.build_enhanced_prompt(prompt, mcp_server_ids)
                logger.info(f"原始提示词长度: {len(prompt)}")
                
                # 创建智能体
                assistant = Assistant(
                    user_id=user_id,
                    name=name,
                    original_prompt=prompt,  # 保存用户原始提示词
                    prompt=prompt,  # 暂时保存原始提示词，聊天时会动态生成增强版
                    description=description,
                    enable_knowledge_base=enable_knowledge_base
                )
                session.add(assistant)
                session.flush()  # 获取assistant_id
                logger.info(f"智能体创建成功: assistant_id={assistant.assistant_id}")
                
                # 关联知识库文档
                knowledge_base_data = []
                if knowledge_base:
                    for kb_item in knowledge_base:
                        kb_association = AssistantKnowledgeBase(
                            assistant_id=assistant.assistant_id,
                            document_id=kb_item.document_id
                        )
                        session.add(kb_association)
                        knowledge_base_data.append(kb_association.to_dict())
                    logger.info(f"关联知识库文档数量: {len(knowledge_base)}")
                
                # 关联MCP服务
                mcp_services_data = []
                if mcp_services:
                    for mcp_item in mcp_services:
                        mcp_association = AssistantMCPService(
                            assistant_id=assistant.assistant_id,
                            mcp_server_id=mcp_item.mcp_server_id
                        )
                        session.add(mcp_association)
                        mcp_services_data.append(mcp_association.to_dict())
                    logger.info(f"关联MCP服务数量: {len(mcp_services)}")
                
                session.commit()
                
                # 构建返回数据
                result = {
                    'assistant_id': assistant.assistant_id,
                    'user_id': assistant.user_id,
                    'name': assistant.name,
                    'prompt': assistant.prompt,
                    'description': assistant.description,
                    'is_active': assistant.is_active,
                    'enable_knowledge_base': assistant.enable_knowledge_base,
                    'created_at': assistant.created_at,
                    'updated_at': assistant.updated_at,
                    'knowledge_base': knowledge_base_data,
                    'mcp_services': mcp_services_data
                }
                
                logger.info(f"智能体创建完成: assistant_id={assistant.assistant_id}, 知识库数量={len(knowledge_base_data)}, MCP服务数量={len(mcp_services_data)}")
                
                return result
                
            except Exception as e:
                logger.error(f"创建智能体失败: {str(e)}", exc_info=True)
                session.rollback()
                raise
    
    def get_assistant_by_id(self, assistant_id: str, user_id: str) -> Optional[Assistant]:
        """根据ID获取智能体"""
        logger.debug(f"查询智能体: assistant_id={assistant_id}, user_id={user_id}")
        
        with self.session_factory() as session:
            try:
                assistant = session.query(Assistant).filter(
                    and_(
                        Assistant.assistant_id == assistant_id,
                        Assistant.user_id == user_id
                    )
                ).first()
                
                if assistant:
                    logger.debug(f"找到智能体: {assistant.name}")
                else:
                    logger.debug(f"未找到智能体: assistant_id={assistant_id}")
                
                return assistant
            except Exception as e:
                logger.error(f"查询智能体失败: {str(e)}", exc_info=True)
                raise
    
    def get_user_assistants(
        self, 
        user_id: str, 
        page: int = 1, 
        page_size: int = 10,
        search: Optional[str] = None
    ) -> Dict[str, Any]:
        """获取用户的智能体列表（支持关键词搜索）"""
        logger.info(f"获取用户智能体列表: user_id={user_id}, page={page}, page_size={page_size}, search={search}")
        
        with self.session_factory() as session:
            try:
                # 构建基础查询
                base_query = session.query(Assistant).filter(Assistant.user_id == user_id)
                
                # 添加搜索过滤条件
                if search and search.strip():
                    search_term = search.strip()
                    logger.info(f"应用搜索过滤: 关键词='{search_term}'")
                    
                    # 尝试URL解码，支持中文搜索
                    import urllib.parse
                    try:
                        decoded_search = urllib.parse.unquote(search_term, encoding='utf-8')
                        # 如果解码后内容发生变化，说明原来是URL编码的
                        if decoded_search != search_term:
                            actual_search = decoded_search
                            logger.info(f"URL解码后的搜索词: '{actual_search}'")
                        else:
                            actual_search = search_term
                    except Exception:
                        actual_search = search_term
                    
                    # 使用ILIKE进行不区分大小写的模糊匹配
                    search_filter = or_(
                        Assistant.name.ilike(f'%{actual_search}%'),
                        Assistant.description.ilike(f'%{actual_search}%')
                    )
                    base_query = base_query.filter(search_filter)
                
                # 计算总数（应用搜索过滤后的总数）
                total = base_query.count()
                
                # 分页查询
                offset = (page - 1) * page_size
                assistants = base_query.order_by(Assistant.created_at.desc()).offset(offset).limit(page_size).all()
                
                logger.info(f"查询结果: 总数={total}, 当前页数量={len(assistants)}")
                
                # 转换为字典格式
                assistant_list = []
                for assistant in assistants:
                    assistant_data = assistant.to_dict()
                    assistant_data['knowledge_base'] = []
                    assistant_data['mcp_services'] = []
                    
                    # 添加知识库信息
                    for kb_item in assistant.knowledge_base:
                        assistant_data['knowledge_base'].append(kb_item.to_dict())
                    
                    # 添加MCP服务信息
                    for mcp_item in assistant.mcp_services:
                        assistant_data['mcp_services'].append(mcp_item.to_dict())
                    
                    assistant_list.append(assistant_data)
                
                return {
                    'total': total,
                    'page': page,
                    'page_size': page_size,
                    'assistants': assistant_list
                }
            except Exception as e:
                logger.error(f"获取用户智能体列表失败: {str(e)}", exc_info=True)
                raise
    
    async def update_assistant(
        self,
        assistant_id: str,
        user_id: str,
        name: Optional[str] = None,
        prompt: Optional[str] = None,
        description: Optional[str] = None,
        is_active: Optional[bool] = None,
        enable_knowledge_base: Optional[bool] = None,
        knowledge_base: Optional[List[Any]] = None,
        mcp_services: Optional[List[Any]] = None
    ) -> Dict[str, Any]:
        """更新智能体"""
        logger.info(f"开始更新智能体: assistant_id={assistant_id}, user_id={user_id}")
        
        with self.session_factory() as session:
            try:
                # 获取智能体
                assistant = session.query(Assistant).filter(
                    and_(
                        Assistant.assistant_id == assistant_id,
                        Assistant.user_id == user_id
                    )
                ).first()
                
                if not assistant:
                    logger.warning(f"智能体不存在或无权限访问: assistant_id={assistant_id}, user_id={user_id}")
                    raise ValueError("智能体不存在或无权限访问")
                
                # 更新基本信息
                if name is not None:
                    assistant.name = name
                    logger.info(f"更新智能体名称: {name}")
                if description is not None:
                    assistant.description = description
                    logger.info(f"更新智能体描述: {description}")
                if is_active is not None:
                    assistant.is_active = is_active
                    logger.info(f"更新智能体状态: {is_active}")
                
                # 更新知识库启用状态
                if enable_knowledge_base is not None:
                    assistant.enable_knowledge_base = enable_knowledge_base
                    logger.info(f"更新知识库启用状态: {enable_knowledge_base}")
                
                # 更新用户原始提示词（如果提供了新的提示词）
                if prompt is not None:
                    assistant.original_prompt = prompt
                    # 不再预生成增强提示词，聊天时会动态生成
                    # assistant.prompt = prompt
                    logger.info(f"更新原始提示词: 新长度={len(prompt)}")
                
                # 如果更新了提示词或MCP服务，需要重新构建增强提示词
                if prompt is not None or mcp_services is not None:
                    # 使用新的或现有的原始提示词
                    if prompt is not None:
                        assistant.original_prompt = prompt
                        # 不再预生成增强提示词，聊天时会动态生成
                        # assistant.prompt = prompt
                        logger.info(f"更新原始提示词: 新长度={len(prompt)}")
                    
                    # 获取MCP服务ID列表
                    if mcp_services is not None:
                        # mcp_services是MCPServiceItem对象列表，使用点号访问属性
                        mcp_server_ids = [mcp.mcp_server_id for mcp in mcp_services]
                    else:
                        # 使用现有的MCP服务
                        mcp_server_ids = [mcp.mcp_server_id for mcp in assistant.mcp_services]
                    
                    # 不再预生成增强版提示词，聊天时会动态生成
                    # enhanced_prompt = await self.mcp_manager.build_enhanced_prompt(current_original_prompt, mcp_server_ids)
                    # assistant.prompt = enhanced_prompt
                    logger.info(f"MCP服务配置更新: 服务数量={len(mcp_server_ids)}")
                
                assistant.updated_at = int(time.time())
                
                # 更新知识库关联
                knowledge_base_data = []
                if knowledge_base is not None:
                    # 删除旧的关联
                    old_count = session.query(AssistantKnowledgeBase).filter(
                        AssistantKnowledgeBase.assistant_id == assistant_id
                    ).count()
                    session.query(AssistantKnowledgeBase).filter(
                        AssistantKnowledgeBase.assistant_id == assistant_id
                    ).delete()
                    logger.info(f"删除旧知识库关联: {old_count} 个")
                    
                    # 创建新的关联
                    for kb_item in knowledge_base:
                        kb_association = AssistantKnowledgeBase(
                            assistant_id=assistant.assistant_id,
                            document_id=kb_item.document_id
                        )
                        session.add(kb_association)
                        knowledge_base_data.append(kb_association.to_dict())
                    logger.info(f"创建新知识库关联: {len(knowledge_base)} 个")
                else:
                    # 获取现有的知识库关联
                    for kb_item in assistant.knowledge_base:
                        knowledge_base_data.append(kb_item.to_dict())
                
                # 更新MCP服务关联
                mcp_services_data = []
                if mcp_services is not None:
                    # 删除旧的关联
                    old_count = session.query(AssistantMCPService).filter(
                        AssistantMCPService.assistant_id == assistant_id
                    ).count()
                    session.query(AssistantMCPService).filter(
                        AssistantMCPService.assistant_id == assistant_id
                    ).delete()
                    logger.info(f"删除旧MCP服务关联: {old_count} 个")
                    
                    # 创建新的关联
                    for mcp_item in mcp_services:
                        mcp_association = AssistantMCPService(
                            assistant_id=assistant.assistant_id,
                            mcp_server_id=mcp_item.mcp_server_id
                        )
                        session.add(mcp_association)
                        mcp_services_data.append(mcp_association.to_dict())
                    logger.info(f"创建新MCP服务关联: {len(mcp_services)} 个")
                else:
                    # 获取现有的MCP服务关联
                    for mcp_item in assistant.mcp_services:
                        mcp_services_data.append(mcp_item.to_dict())
                
                session.commit()
                
                # 构建返回数据
                result = {
                    'assistant_id': assistant.assistant_id,
                    'user_id': assistant.user_id,
                    'name': assistant.name,
                    'prompt': assistant.prompt,
                    'description': assistant.description,
                    'is_active': assistant.is_active,
                    'enable_knowledge_base': assistant.enable_knowledge_base,
                    'created_at': assistant.created_at,
                    'updated_at': assistant.updated_at,
                    'knowledge_base': knowledge_base_data,
                    'mcp_services': mcp_services_data
                }
                
                logger.info(f"智能体更新完成: assistant_id={assistant.assistant_id}, 知识库数量={len(knowledge_base_data)}, MCP服务数量={len(mcp_services_data)}")
                return result
                
            except Exception as e:
                logger.error(f"更新智能体失败: {str(e)}", exc_info=True)
                session.rollback()
                raise
    
    def delete_assistant(self, assistant_id: str, user_id: str) -> None:
        """删除智能体"""
        logger.info(f"开始删除智能体: assistant_id={assistant_id}, user_id={user_id}")
        
        with self.session_factory() as session:
            try:
                # 检查权限
                assistant = session.query(Assistant).filter(
                    and_(
                        Assistant.assistant_id == assistant_id,
                        Assistant.user_id == user_id
                    )
                ).first()
                
                if not assistant:
                    logger.warning(f"智能体不存在或无权限访问: assistant_id={assistant_id}, user_id={user_id}")
                    raise ValueError("智能体不存在或无权限访问")
                
                # 删除智能体（关联表会通过CASCADE自动删除）
                session.delete(assistant)
                session.commit()
                logger.info(f"智能体删除成功: assistant_id={assistant_id}")
                
            except Exception as e:
                logger.error(f"删除智能体失败: {str(e)}", exc_info=True)
                session.rollback()
                raise

    def get_assistant_detail(self, assistant_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """获取智能体详细信息，包含关系数据"""
        logger.debug(f"查询智能体详情: assistant_id={assistant_id}, user_id={user_id}")
        
        with self.session_factory() as session:
            try:
                assistant = session.query(Assistant).filter(
                    and_(
                        Assistant.assistant_id == assistant_id,
                        Assistant.user_id == user_id
                    )
                ).first()
                
                if not assistant:
                    logger.debug(f"未找到智能体: assistant_id={assistant_id}")
                    return None
                
                # 获取知识库关联数据
                knowledge_base_data = []
                for kb_item in assistant.knowledge_base:
                    knowledge_base_data.append(kb_item.to_dict())
                
                # 获取MCP服务关联数据
                mcp_services_data = []
                for mcp_item in assistant.mcp_services:
                    mcp_services_data.append(mcp_item.to_dict())
                
                # 构建返回数据
                result = {
                    'assistant_id': assistant.assistant_id,
                    'user_id': assistant.user_id,
                    'name': assistant.name,
                    'prompt': assistant.original_prompt,
                    'description': assistant.description,
                    'is_active': assistant.is_active,
                    'enable_knowledge_base': assistant.enable_knowledge_base,
                    'created_at': assistant.created_at,
                    'updated_at': assistant.updated_at,
                    'knowledge_base': knowledge_base_data,
                    'mcp_services': mcp_services_data
                }
                
                logger.debug(f"找到智能体: {assistant.name}, 知识库数量={len(knowledge_base_data)}, MCP服务数量={len(mcp_services_data)}")
                return result
                
            except Exception as e:
                logger.error(f"查询智能体详情失败: {str(e)}", exc_info=True)
                raise
