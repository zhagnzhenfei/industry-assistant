import requests
import json
from openai import OpenAI
import os
import time
import re
import asyncio
from typing import Dict, Any, AsyncGenerator, List, Optional
from urllib.parse import urlparse # For deduplication based on domain or path
from collections import Counter # For basic data analysis
import logging # Use logging for better error/info messages

# --- Configuration ---
# Note: Replace placeholders with your actual API keys or use environment variables
SEARCH_API_KEY = os.getenv("BOCHAAI_API_KEY", "Bearer sk-392ef5953eaa4c43be43e6daab4e82a4") # Example: Use env var or default
LLM_API_KEY = os.getenv("DASHSCOPE_API_KEY", "sk-f02db5a079ab41588b1cab09ad2777a2")      # Example: Use env var or default
LLM_BASE_URL = os.getenv("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Helper function for serializing python objects to JSON
def serialize_event(event_data: Dict[str, Any]) -> str:
    """
    将事件数据序列化为JSON字符串，处理特殊类型如集合和异常
    
    Args:
        event_data: 包含事件数据的字典
        
    Returns:
        序列化的JSON字符串
    """
    def json_serializer(obj):
        """处理非JSON可序列化类型的自定义转换器"""
        if isinstance(obj, set):
            return list(obj)
        if isinstance(obj, Exception):
            return str(obj)
        raise TypeError(f"Type {type(obj)} not serializable")
    
    try:
        return json.dumps(event_data, default=json_serializer, ensure_ascii=False)
    except Exception as e:
        # 如果序列化失败，返回错误消息
        logging.error(f"Failed to serialize event: {e}, event data: {event_data}")
        return json.dumps({"type": "error", "content": f"Failed to serialize event: {e}"})

# --- ResearchService Class ---
class ResearchService:
    """研究服务类，包装深度研究工作流以便于 API 集成"""
    
    def __init__(self, search_api_key: Optional[str] = None, llm_api_key: Optional[str] = None, llm_base_url: Optional[str] = None):
        """
        初始化研究服务
        
        Args:
            search_api_key: 搜索 API 密钥，默认使用环境变量
            llm_api_key: LLM API 密钥，默认使用环境变量
            llm_base_url: LLM API 基础 URL，默认使用环境变量
        """
        self.search_api_key = search_api_key or SEARCH_API_KEY
        self.llm_api_key = llm_api_key or LLM_API_KEY
        self.llm_base_url = llm_base_url or LLM_BASE_URL
    
    async def research_stream(self, query: str, max_iterations: int = 3) -> AsyncGenerator[str, None]:
        """
        执行研究流程并以流式方式返回结果
        
        Args:
            query: 用户的研究问题
            max_iterations: 最大迭代次数
            
        Yields:
            序列化为JSON字符串的事件数据
        """
        # 初始化工作流程变量
        memory = [] # Stores {'subquery': str, 'url': str, 'name': str, 'summary': str, 'snippet': str}
        processed_urls = set()
        current_subqueries = []
        all_subqueries_history = set()
        llm_system_prompt = f"你是一位专门的行业的资深研究助理。请仔细遵循指示并以要求的格式回答。"
        
        # 发送初始消息
        yield serialize_event({"type": "status", "content": "开始研究", "query": query})
        
        # 1. 迭代过程
        for iteration in range(max_iterations):
            yield serialize_event({"type": "status", "content": f"开始第 {iteration + 1} 次迭代"})
            
            # 1.1 规划阶段
            if iteration == 0:
                yield serialize_event({"type": "status", "content": "规划子问题..."})
                
                plan_prompt = f"""
                请将以下用户的主要研究问题分解为具体的、可搜索的子问题列表，以全面覆盖该主题。
                请严格按照以下 JSON 格式输出，不要包含任何额外的解释或评论：
                {{
                  "subqueries": [
                    "子问题1",
                    "子问题2",
                    "子问题3"
                  ]
                }}

                用户主要问题："{query}"
                """
                
                # 转为异步调用 
                llm_response = await self._run_sync(qwen_llm, 
                    plan_prompt,
                    response_format={"type": "json_object"},
                    system_message_content=llm_system_prompt
                )
                
                if not llm_response:
                    yield serialize_event({"type": "status", "content": "子问题生成失败，使用原始问题继续..."})
                    current_subqueries = [query]
                else:
                    try:
                        plan_result = json.loads(llm_response)
                        current_subqueries = plan_result.get('subqueries', [])
                        if not current_subqueries or not isinstance(current_subqueries, list):
                            yield serialize_event({"type": "status", "content": "子问题格式无效，使用原始问题继续..."})
                            current_subqueries = [query]
                        else:
                            yield serialize_event({"type": "subqueries", "content": current_subqueries})
                    except Exception as e:
                        yield serialize_event({"type": "error", "content": f"解析子问题时出错: {str(e)}"})
                        current_subqueries = [query]
            
            elif not current_subqueries:
                yield serialize_event({"type": "status", "content": "没有新的子问题生成，结束迭代..."})
                break
                
            # 1.2 过滤子问题
            subqueries_to_search = [q for q in current_subqueries if q and q not in all_subqueries_history]
            if not subqueries_to_search and iteration > 0:
                yield serialize_event({"type": "status", "content": "所有子问题已搜索完毕，进入反思阶段..."})
            
            # 1.3 执行搜索
            new_results_count = 0
            for subquery in subqueries_to_search:
                if not subquery: continue
                yield serialize_event({"type": "search", "content": f"搜索: {subquery}"})
                
                all_subqueries_history.add(subquery)
                search_results = await self._run_sync(websearch, subquery)
                await asyncio.sleep(1.2)  # 异步延时
                
                # 1.4 整合结果
                for result in search_results:
                    url = result.get('url')
                    if url and url not in processed_urls:
                        processed_urls.add(url)
                        summary = result.get('summary', '') or result.get('snippet', '')
                        if summary:
                            memory.append({
                                "subquery": subquery,
                                "url": url,
                                "name": result.get('name', 'N/A'),
                                "summary": summary,
                                "snippet": result.get('snippet', ''),
                                "siteName": result.get('siteName', 'N/A'),
                                "siteIcon": result.get('siteIcon', 'N/A')
                            })
                            new_results_count += 1
                            # 每添加一个结果就立即返回一个事件，但不改变memory结构
                            yield serialize_event({
                                "type": "search_result_item", 
                                "result": memory[-1]  # 返回刚刚添加到memory的最后一项
                            })
                
                yield serialize_event({"type": "search_results", "subquery": subquery, "count": new_results_count})
            
            # 1.5 准备反思
            memory_context_for_llm = ""
            if memory:
                context_items = []
                token_estimate = 0
                max_tokens_estimate = 20000
                for item in reversed(memory):
                    item_text = f"  - 子问题 '{item['subquery']}': {item['summary']}... (来源: {item['url']})\n"
                    token_estimate += len(item_text) / 2
                    if token_estimate > max_tokens_estimate:
                        yield serialize_event({"type": "status", "content": "内存上下文太大，已截断以适应模型限制"})
                        break
                    context_items.append(item_text)
                memory_context_for_llm = "".join(reversed(context_items))
            else:
                memory_context_for_llm = "当前没有收集到任何信息。"
            
            # 1.6 执行反思
            yield serialize_event({"type": "status", "content": "反思收集的信息..."})
            
            reflection_prompt = f"""
            作为研究评估员，请评估为回答以下用户原始问题而收集的信息摘要。

            用户原始问题："{query}"

            目前收集到的信息摘要（可能部分截断）：
            {memory_context_for_llm}

            请评估：
            1.  `can_answer`: 这些信息是否**足够全面**地回答用户的原始问题？(true/false)
            2.  `irrelevant_urls`: 当前摘要中，是否有与回答原始问题**明显无关或关联不大**的条目？（仅列出这些条目的来源 URL 列表，如果没有则为空列表 []）
            3.  `new_subqueries`: 基于当前信息和原始问题，还需要提出哪些**具体的、新的**子问题来**填补关键信息空白**或**深化理解**？（如果信息已足够，则返回空列表 []）

            请严格按照以下 JSON 格式进行响应，不要包含任何额外的解释或评论：
            {{
                "can_answer": boolean,
                "irrelevant_urls": ["url1", "url2", ...],
                "new_subqueries": ["新问题1", "新问题2", ...]
            }}
            """
            
            llm_response = await self._run_sync(qwen_llm,
                reflection_prompt,
                response_format={"type": "json_object"},
                system_message_content=llm_system_prompt
            )
            
            can_answer = False
            current_subqueries = []
            
            if not llm_response:
                yield serialize_event({"type": "status", "content": "反思阶段出错"})
            else:
                try:
                    reflection_result = json.loads(llm_response)
                    can_answer = reflection_result.get('can_answer', False)
                    irrelevant_urls = set(reflection_result.get('irrelevant_urls', []))
                    current_subqueries = reflection_result.get('new_subqueries', [])
                    
                    # 验证类型和过滤处理
                    if not isinstance(can_answer, bool):
                        can_answer = False
                    if not isinstance(irrelevant_urls, (set, list)):
                        irrelevant_urls = set()
                    else:
                        irrelevant_urls = set(irrelevant_urls)
                        
                    if not isinstance(current_subqueries, list):
                        current_subqueries = []
                    else:
                        current_subqueries = [q for q in current_subqueries if isinstance(q, str) and q.strip()]
                    
                    yield serialize_event({"type": "reflection", "can_answer": can_answer, "new_subqueries_count": len(current_subqueries)})
                    
                    if irrelevant_urls:
                        original_memory_size = len(memory)
                        memory = [item for item in memory if item['url'] not in irrelevant_urls]
                        # Convert the set to a list for proper JSON serialization
                        yield serialize_event({"type": "pruning", "from": original_memory_size, "to": len(memory), "removed_urls": list(irrelevant_urls)})
                    
                    if can_answer:
                        yield serialize_event({"type": "status", "content": "收集到的信息足够回答问题，结束迭代"})
                        break
                    
                    if current_subqueries:
                        yield serialize_event({"type": "new_subqueries", "content": current_subqueries})
                    else:
                        yield serialize_event({"type": "status", "content": "信息不足，但未生成新的子问题"})
                        
                except Exception as e:
                    yield serialize_event({"type": "error", "content": f"处理反思结果时出错: {str(e)}"})
            
            # 1.7 最大迭代检查
            if iteration == max_iterations - 1:
                yield serialize_event({"type": "status", "content": "达到最大迭代次数"})
        
        # 2. 后处理阶段
        if not memory:
            yield serialize_event({"type": "error", "content": "未能收集到任何信息"})
            yield serialize_event({"type": "final_answer", "content": "未能生成报告，因为没有收集到相关信息。"})
            return
        
        # 3. 数据分析阶段
        needs_analysis = len(memory) >= 5
        analysis_summary = ""
        
        if needs_analysis:
            yield serialize_event({"type": "status", "content": "开始数据分析..."})
            texts_for_analysis = [item['summary'] for item in memory]
            
            # 捕获数据分析输出
            analysis_result = await self._run_sync(simple_data_analyzer, texts_for_analysis)
            analysis_summary = analysis_result
            
            yield serialize_event({"type": "analysis", "content": analysis_summary})
        
        # 4. 最终合成
        yield serialize_event({"type": "status", "content": "开始生成最终报告..."})
        
        # 为每个内存项添加编号
        for index, item in enumerate(memory):
            item['reference_id'] = index + 1  # 从1开始编号
        
        # 添加日志验证id字段已添加
        logging.info(f"已为{len(memory)}个参考资料添加ID，第一个资料ID: {memory[0]['reference_id'] if memory else 'N/A'}")
        
        # 返回带编号的所有搜索结果
        yield serialize_event({
            "type": "reference_materials", 
            "content": memory
        })
        
        final_memory_context = "\n\n".join([
            f"引用编号 {item['reference_id']}\n来源 URL: {item['url']}\n相关子问题: {item['subquery']}\n标题: {item['name']}\n内容摘要: {item['summary']}"
            for item in memory
        ])
        
        analysis_section = ""
        if analysis_summary and "未在收集的信息中发现足够的可量化数据进行分析" not in analysis_summary:
            analysis_section = f"\n\n补充数据分析摘要:\n{analysis_summary}\n"
        
        synthesis_prompt = f"""
        您是一位专业的行业研究员。您的任务是基于以下收集到的信息，为用户生成一份全面、结构清晰、客观中立的中文研究报告，以回答他们的原始问题。

        用户的原始问题是："{query}"

        以下是收集到的相关信息：
        --- 开始收集的信息 ---
        {final_memory_context}
        --- 结束收集的信息 ---
        {analysis_section}
        请严格遵守以下要求撰写报告：
        1.  **完全基于**上面提供的"收集到的信息"来撰写，不得添加任何外部知识、个人观点或未经证实的信息。
        2.  清晰、有条理地组织报告内容，直接回答用户的原始问题。可适当使用标题和小标题。
        3.  在报告中**必须**引用信息来源。当您使用某条信息时，请在其后用特殊格式注明引用编号：##引用编号$$。例如：安责险的保费规模近年来持续增长 ##2$$。
        4.  如果提供了"补充数据分析摘要"，请将分析结果（如趋势、统计数据、关键词）自然地融入报告内容中，并指明这是基于所提供数据的分析。
        5.  语言专业、客观、简洁。避免使用模糊或主观性强的词语。
        6.  如果收集到的信息存在矛盾之处，请客观地指出，例如："来源 A 指出... ##1$$，而来源 B 则认为... ##2$$"。
        7.  如果信息不足以回答问题的某些方面，请在报告中说明，例如："关于XXX的具体数据，在收集到的信息中未能找到明确说明。"

        请开始撰写您的研究报告：
        """
        
        # 5. 使用 DeepSeek 生成报告
        yield serialize_event({"type": "thinking_start"})
        
        # 使用异步方式处理流式输出
        client = OpenAI(
            api_key=self.llm_api_key,
            base_url=self.llm_base_url,
        )
        
        reasoning_content = ""
        answer_content = ""
        is_answering = False
        
        stream = await self._run_sync(
            lambda: client.chat.completions.create(
                model="deepseek-r1",
                messages=[
                    {'role': 'system', 'content': 'You are an expert research assistant synthesizing information into a final report, citing sources meticulously.'},
                    {'role': 'user', 'content': synthesis_prompt}
                ],
                stream=True
            )
        )
        
        # 处理流式响应
        async for chunk in self._process_stream(stream):
            # 处理 chunk...
            if not getattr(chunk, 'choices', None):
                continue
                
            delta = chunk.choices[0].delta
            
            if not hasattr(delta, 'reasoning_content'):
                continue
                
            if not getattr(delta, 'reasoning_content', None) and not getattr(delta, 'content', None):
                continue
                
            if not getattr(delta, 'reasoning_content', None) and not is_answering:
                is_answering = True
                yield serialize_event({"type": "thinking_end"})
                yield serialize_event({"type": "answer_start"})
                
            if getattr(delta, 'reasoning_content', None):
                reasoning_content += delta.reasoning_content
                yield serialize_event({"type": "thinking", "content": delta.reasoning_content})
            elif getattr(delta, 'content', None):
                answer_content += delta.content
                yield serialize_event({"type": "answer", "content": delta.content})
        
        yield serialize_event({"type": "answer_end"})
        # yield serialize_event({"type": "final_answer", "content": answer_content})
        yield serialize_event({"type": "complete"})
    
    @staticmethod
    async def _run_sync(func, *args, **kwargs):
        """运行同步函数，并使其异步化"""
        return await asyncio.to_thread(func, *args, **kwargs)
    
    @staticmethod
    async def _process_stream(stream):
        """处理流式响应"""
        for chunk in stream:
            yield chunk
            await asyncio.sleep(0)  # 让出控制权给事件循环

# --- Core Functions ---

def websearch(query, count=5):
    """Performs a web search using the bochaai API."""
    url = "https://api.bochaai.com/v1/web-search"
    payload = json.dumps({
        "query": query,
        "summary": True,
        "count": count,
        "page": 1
    })
    headers = {
        'Authorization': SEARCH_API_KEY,
        'Content-Type': 'application/json'
    }

    try:
        response = requests.post(url, headers=headers, data=payload, timeout=25) # Increased timeout slightly
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.Timeout:
        logging.error(f"Web search request timed out for query: '{query}'")
        return []
    except requests.exceptions.RequestException as e:
        logging.error(f"Error during web search request for '{query}': {e}")
        return []
    except json.JSONDecodeError as e:
        logging.error(f"Error decoding JSON for web search '{query}': {e}. Response text: {response.text[:500]}...") # Log snippet of text
        return []
    except Exception as e:
        logging.error(f"Unexpected error during web search for '{query}': {e}", exc_info=True) # Log stack trace
        return []

    webpages_data = data.get('data', {}).get('webPages', {})
    value_list = webpages_data.get('value')

    if value_list is None or not isinstance(value_list, list):
        logging.warning(f"Could not find 'value' list or it's not a list in response for '{query}'.")
        return []

    filtered_results = [
        item for item in value_list
        if item.get('url') and (item.get('snippet') or item.get('summary'))
    ]
    return filtered_results

def qwen_llm(prompt, model="qwen-max", response_format=None, system_message_content="You are a helpful assistant."):
    """Calls the Qwen LLM (non-streaming), optionally enforcing JSON output."""
    logging.info(f"Calling Qwen LLM (model: {model}) for: {prompt[:100]}...")
    try:
        client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)

        completion_args = {
            "model": model,
            "messages": [
                {'role': 'system', 'content': system_message_content},
                {'role': 'user', 'content': prompt}
            ],
            "temperature": 0.2, # Keep temperature low for structured tasks
        }
        if response_format:
            completion_args["response_format"] = response_format
            logging.info("Requesting JSON format from LLM.")

        completion = client.chat.completions.create(**completion_args)
        content = completion.choices[0].message.content
        logging.info("LLM call successful.")
        return content
    except Exception as e:
        logging.error(f"Error calling Qwen LLM: {e}", exc_info=True)
        return None

# --- Data Analysis Function ---

def simple_data_analyzer(text_data):
    """
    Performs very basic data analysis on extracted text snippets.
    Tries to find numerical data points and provides simple statistics.
    Input: A list of strings (relevant snippets/summaries from memory).
    Output: A string summarizing basic findings or indicating lack of data.
    """
    print("\n" + "=" * 20 + " Data Analysis " + "=" * 20 + "\n")
    numbers = []
    percentages = []
    keywords = Counter()
    # Regex patterns
    # Capture numbers potentially followed by currency units (improved capture)
    currency_pattern = re.compile(r'(\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?)\s*(?:元|万|亿|人民币|美元)')
    percentage_pattern = re.compile(r'(\d+(?:\.\d+)?)\s*%') # Added optional space before %
    # Keywords relevant to 安责险
    relevant_keywords = ['安责险', '保费', '赔付', '事故', '费率', '覆盖率', '企业', '风险', '安全生产', '保额', '投保', '监管', '政策']

    full_text = " ".join(text_data)
    logging.info(f"Performing basic analysis on {len(text_data)} text snippets.")

    # Extract numbers associated with currency
    currency_values = currency_pattern.findall(full_text)
    # Directly iterate over the found strings, no unpacking needed
    numbers.extend([float(val.replace(',', '')) for val in currency_values if val])
    logging.info(f"Found {len(numbers)} potential numerical/currency values.")

    # Extract percentages
    perc_values = percentage_pattern.findall(full_text)
    percentages.extend([float(p) for p in perc_values])
    logging.info(f"Found {len(percentages)} percentage values.")

    # Keyword counts
    lower_full_text = full_text.lower() # Lowercase once for efficiency
    for keyword in relevant_keywords:
        count = lower_full_text.count(keyword.lower())
        if count > 0:
            keywords[keyword] += count
    logging.info(f"Keyword counts: {keywords.most_common(5)}")

    # --- Summary Generation ---
    analysis_summary = "数据分析摘要:\n"
    found_data = False
    if numbers:
        found_data = True
        try:
            analysis_summary += f"- 发现 {len(numbers)} 个数值 (可能是金额). 平均值: {sum(numbers)/len(numbers):.2f}, 最小值: {min(numbers):.2f}, 最大值: {max(numbers):.2f}\n"
        except ZeroDivisionError:
             analysis_summary += f"- 发现 {len(numbers)} 个数值 (可能是金额), 但无法计算统计数据。\n"
    else:
        analysis_summary += "- 未明确发现可用于统计分析的货币数值。\n"

    if percentages:
        found_data = True
        try:
            analysis_summary += f"- 发现 {len(percentages)} 个百分比值. 平均值: {sum(percentages)/len(percentages):.2f}%, 最小值: {min(percentages):.2f}%, 最大值: {max(percentages):.2f}%\n"
        except ZeroDivisionError:
             analysis_summary += f"- 发现 {len(percentages)} 个百分比值, 但无法计算统计数据。\n"
    else:
        analysis_summary += "- 未发现明确的百分比值。\n"

    if keywords:
        found_data = True
        analysis_summary += "- 主要关键词频率: " + ", ".join([f"{k}({v})" for k, v in keywords.most_common(5)]) + "\n"
    else:
        analysis_summary += "- 未发现相关的关键词。\n"

    print(analysis_summary)
    print("=" * 20 + " End of Data Analysis " + "=" * 20 + "\n")
    return analysis_summary if found_data else "未在收集的信息中发现足够的可量化数据进行分析。"