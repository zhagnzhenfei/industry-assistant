# Open Deep Research - Supervisor 详细文档

## 📋 概述

Supervisor（研究监督者）是 Open Deep Research 系统中的核心组件，负责制定研究策略、分解研究任务并协调多个子研究者进行并行研究。它充当整个研究过程的"大脑"，确保研究任务能够高效、有序地完成。

## 🎯 核心功能

### 主要职责
- **研究策略制定**：分析研究摘要，制定研究计划
- **任务分解**：将复杂研究问题分解为可管理的子任务
- **任务委托**：将具体研究任务分配给子研究者
- **进度监控**：评估研究进展和结果质量
- **流程控制**：决定何时结束研究阶段

### 在工作流中的位置
```
用户输入 → 澄清问题 → 研究规划 → [Supervisor] → 工具执行 → 研究完成 → 最终报告
```

## 🔧 核心工具

Supervisor 使用三个核心工具来执行其功能：

### 1. ConductResearch - 研究任务委托工具

**定义**：
```python
class ConductResearch(BaseModel):
    """Call this tool to conduct research on a specific topic."""
    research_topic: str = Field(
        description="The topic to research. Should be a single topic, and should be described in high detail (at least a paragraph).",
    )
```

**功能**：
- 将具体的研究任务分配给子研究者
- 支持任务分解和并行执行
- 每个调用会创建一个独立的研究者实例

**使用场景**：
- 将研究问题分解为多个子主题
- 为每个子主题创建独立的研究任务
- 支持并行研究提高效率

### 2. ResearchComplete - 研究完成标记工具

**定义**：
```python
class ResearchComplete(BaseModel):
    """Call this tool to indicate that the research is complete."""
```

**功能**：
- 标记研究阶段已经完成
- 触发从研究阶段到报告生成阶段的转换
- 基于收集到的信息判断是否足够

**使用场景**：
- 当收集到足够信息时标记研究完成
- 当达到最大迭代次数时强制完成
- 当研究任务无法继续时结束研究

### 3. think_tool - 战略思考工具

**定义**：
```python
def think_tool(reflection: str) -> str:
    """Tool for strategic reflection on research progress and decision-making.
    
    Use this tool after each search to analyze results and plan next steps systematically.
    This creates a deliberate pause in the research workflow for quality decision-making.
    """
```

**功能**：
- 在研究开始前制定研究策略
- 分析已收集的信息和发现
- 决定下一步的研究方向
- 确保研究方向的正确性

**使用时机**：
- 研究开始前：制定研究策略
- 任务分解前：分析如何分解任务
- 结果评估后：判断是否需要更多研究

## 🔄 工作流程

### 1. 初始化阶段

```python
async def supervisor(state: SupervisorState, config: RunnableConfig) -> Command[Literal["supervisor_tools"]]:
    # Step 1: 配置监督者模型和工具
    configurable = Configuration.from_runnable_config(config)
    research_model_config = {
        "model": configurable.research_model,
        "max_tokens": configurable.research_model_max_tokens,
        "api_key": get_api_key_for_model(configurable.research_model, config),
        "tags": ["langsmith:nostream"]
    }
    
    # 可用工具：研究委托、完成标记、战略思考
    lead_researcher_tools = [ConductResearch, ResearchComplete, think_tool]
```

### 2. 模型配置

```python
# 配置模型并绑定工具
research_model = (
    configurable_model
    .bind_tools(lead_researcher_tools)                                    # 绑定工具
    .with_retry(stop_after_attempt=configurable.max_structured_output_retries)  # 重试逻辑
    .with_config(research_model_config)                                   # 应用配置
)
```

### 3. 生成响应

```python
# 获取当前监督者消息历史
supervisor_messages = state.get("supervisor_messages", [])

# 调用模型生成响应
response = await research_model.ainvoke(supervisor_messages)
```

### 4. 状态更新

```python
# 更新状态并返回命令
return Command(
    goto="supervisor_tools",                    # 下一步执行supervisor_tools
    update={
        "supervisor_messages": [response],      # 添加新的响应消息
        "research_iterations": state.get("research_iterations", 0) + 1  # 增加迭代计数
    }
)
```

## 🛠️ 工具执行处理

### supervisor_tools 函数

```python
async def supervisor_tools(state: SupervisorState, config: RunnableConfig) -> Command[Literal["supervisor", "__end__"]]:
```

**主要功能**：
1. **退出条件检查**：检查是否达到最大迭代次数或研究完成
2. **工具调用处理**：处理 think_tool 和 ConductResearch 调用
3. **并行研究执行**：同时执行多个研究任务
4. **结果聚合**：收集和整理研究结果

### 工具调用处理流程

#### 1. think_tool 处理
```python
# 处理战略思考工具调用
think_tool_calls = [
    tool_call for tool_call in most_recent_message.tool_calls 
    if tool_call["name"] == "think_tool"
]

for tool_call in think_tool_calls:
    reflection_content = tool_call["args"]["reflection"]
    all_tool_messages.append(ToolMessage(
        content=f"Reflection recorded: {reflection_content}",
        name="think_tool",
        tool_call_id=tool_call["id"]
    ))
```

#### 2. ConductResearch 处理
```python
# 处理研究任务委托
conduct_research_calls = [
    tool_call for tool_call in most_recent_message.tool_calls 
    if tool_call["name"] == "ConductResearch"
]

if conduct_research_calls:
    # 限制并发研究单元数量
    allowed_conduct_research_calls = conduct_research_calls[:configurable.max_concurrent_research_units]
    
    # 并行执行研究任务
    research_tasks = [
        researcher_subgraph.ainvoke({
            "researcher_messages": [
                HumanMessage(content=tool_call["args"]["research_topic"])
            ],
            "research_topic": tool_call["args"]["research_topic"]
        }, config) 
        for tool_call in allowed_conduct_research_calls
    ]
    
    tool_results = await asyncio.gather(*research_tasks)
```

## ⚙️ 配置参数

### 关键配置项

```python
class Configuration(BaseModel):
    # 研究配置
    max_concurrent_research_units: int = Field(default=5)  # 最大并发研究单元数
    max_researcher_iterations: int = Field(default=6)      # 最大研究迭代次数
    max_react_tool_calls: int = Field(default=10)          # 单次研究最大工具调用次数
    
    # 模型配置
    research_model: str = Field(default="openai:gpt-4.1")  # 研究模型
    research_model_max_tokens: int = Field(default=10000)  # 研究模型最大token数
    
    # 重试配置
    max_structured_output_retries: int = Field(default=3)  # 结构化输出重试次数
```

### 配置说明

- **max_concurrent_research_units**：控制同时执行的研究任务数量，防止资源耗尽
- **max_researcher_iterations**：限制监督者的最大迭代次数，避免无限循环
- **max_react_tool_calls**：限制单个研究者的工具调用次数
- **research_model**：指定用于研究监督的模型
- **max_structured_output_retries**：处理模型输出失败的重试次数

## 🎯 使用策略

### 工具调用顺序

1. **研究开始前**：
   ```
   think_tool("分析研究任务，制定研究策略")
   ```

2. **任务分解**：
   ```
   ConductResearch(research_topic="具体的研究子任务1")
   ConductResearch(research_topic="具体的研究子任务2")
   ```

3. **结果评估**：
   ```
   think_tool("评估收集到的信息，判断是否足够")
   ```

4. **完成决策**：
   ```
   ResearchComplete()  # 如果信息足够
   # 或者继续 ConductResearch()  # 如果还需要更多信息
   ```

### 最佳实践

1. **战略思考优先**：在调用 ConductResearch 前使用 think_tool 制定策略
2. **结果评估**：每次 ConductResearch 后使用 think_tool 评估结果
3. **并行处理**：合理利用并发研究单元提高效率
4. **质量控制**：通过迭代次数限制避免过度研究

## 🔍 错误处理

### 常见错误场景

1. **Token限制超出**：
   ```python
   if is_token_limit_exceeded(e, configurable.research_model):
       return Command(
           goto=END,
           update={
               "notes": get_notes_from_tool_calls(supervisor_messages),
               "research_brief": state.get("research_brief", "")
           }
       )
   ```

2. **并发限制超出**：
   ```python
   # 处理溢出研究调用
   for overflow_call in overflow_conduct_research_calls:
       all_tool_messages.append(ToolMessage(
           content=f"Error: Did not run this research as you have already exceeded the maximum number of concurrent research units.",
           name="ConductResearch",
           tool_call_id=overflow_call["id"]
       ))
   ```

3. **迭代次数超出**：
   ```python
   exceeded_allowed_iterations = research_iterations > configurable.max_researcher_iterations
   if exceeded_allowed_iterations:
       return Command(goto=END, update={...})
   ```

## 💡 设计亮点

1. **异步处理**：使用 async/await 提高性能
2. **配置驱动**：所有行为都可通过配置调整
3. **工具绑定**：动态绑定可用工具
4. **重试机制**：处理结构化输出失败
5. **状态管理**：正确更新和传递状态
6. **命令模式**：使用 Command 控制执行流程
7. **并行处理**：支持多个研究任务同时执行
8. **质量控制**：通过思考工具确保研究质量

## 🔄 与其他组件的交互

### 输入
- **SupervisorState**：包含消息历史和研究上下文
- **RunnableConfig**：运行时配置和模型设置

### 输出
- **Command**：指示下一步执行 supervisor_tools
- **状态更新**：新的消息和迭代计数

### 交互组件
- **researcher_subgraph**：子研究者图，执行具体研究任务
- **Configuration**：配置管理，控制行为参数
- **think_tool**：战略思考工具
- **ConductResearch**：研究任务委托工具
- **ResearchComplete**：研究完成标记工具

## 🏗️ 图构建器架构

### 三个核心图构建器

#### 1. **supervisor_builder** - 监督者子图

```python
# Supervisor Subgraph Construction
supervisor_builder = StateGraph(SupervisorState, config_schema=Configuration)

# Add supervisor nodes for research management
supervisor_builder.add_node("supervisor", supervisor)           # Main supervisor logic
supervisor_builder.add_node("supervisor_tools", supervisor_tools)  # Tool execution handler

# Define supervisor workflow edges
supervisor_builder.add_edge(START, "supervisor")  # Entry point to supervisor

# Compile supervisor subgraph for use in main workflow
supervisor_subgraph = supervisor_builder.compile()
```

**功能**：
- **研究管理**：管理研究任务的分配和协调
- **工具调用**：处理监督者的工具调用（ConductResearch、ResearchComplete、think_tool）
- **迭代控制**：控制研究迭代次数和完成条件

**工作流程**：
```
START → supervisor → supervisor_tools → supervisor → ... → END
```

**状态**：`SupervisorState`
- `supervisor_messages`：监督者消息历史
- `research_brief`：研究摘要
- `research_iterations`：研究迭代次数
- `notes`：研究笔记
- `raw_notes`：原始笔记

#### 2. **researcher_builder** - 研究者子图

```python
# Researcher Subgraph Construction
researcher_builder = StateGraph(
    ResearcherState, 
    output=ResearcherOutputState, 
    config_schema=Configuration
)

# Add researcher nodes for research execution and compression
researcher_builder.add_node("researcher", researcher)                 # Main researcher logic
researcher_builder.add_node("researcher_tools", researcher_tools)     # Tool execution handler
researcher_builder.add_node("compress_research", compress_research)   # Research compression

# Define researcher workflow edges
researcher_builder.add_edge(START, "researcher")           # Entry point to researcher
researcher_builder.add_edge("compress_research", END)      # Exit point after compression

# Compile researcher subgraph for parallel execution by supervisor
researcher_subgraph = researcher_builder.compile()
```

**功能**：
- **具体研究**：执行具体的研究任务
- **工具调用**：使用搜索工具、MCP工具、think_tool
- **结果压缩**：将研究结果压缩为结构化摘要

**工作流程**：
```
START → researcher → researcher_tools → researcher → ... → compress_research → END
```

**状态**：`ResearcherState`
- `researcher_messages`：研究者消息历史
- `tool_call_iterations`：工具调用迭代次数
- `research_topic`：研究主题
- `compressed_research`：压缩的研究结果
- `raw_notes`：原始笔记

**输出**：`ResearcherOutputState`
- `compressed_research`：压缩的研究结果
- `raw_notes`：原始笔记

#### 3. **deep_researcher_builder** - 主工作流图

```python
# Main Deep Researcher Graph Construction
deep_researcher_builder = StateGraph(
    AgentState, 
    input=AgentInputState, 
    config_schema=Configuration
)

# Add main workflow nodes for the complete research process
deep_researcher_builder.add_node("clarify_with_user", clarify_with_user)           # User clarification phase
deep_researcher_builder.add_node("write_research_brief", write_research_brief)     # Research planning phase
deep_researcher_builder.add_node("research_supervisor", supervisor_subgraph)       # Research execution phase
deep_researcher_builder.add_node("final_report_generation", final_report_generation)  # Report generation phase

# Define main workflow edges for sequential execution
deep_researcher_builder.add_edge(START, "clarify_with_user")                       # Entry point
deep_researcher_builder.add_edge("research_supervisor", "final_report_generation") # Research to report
deep_researcher_builder.add_edge("final_report_generation", END)                   # Final exit point

# Compile the complete deep researcher workflow
deep_researcher = deep_researcher_builder.compile()
```

**功能**：
- **完整流程**：从用户输入到最终报告的完整工作流
- **阶段管理**：管理澄清、规划、研究、报告四个阶段
- **子图集成**：集成监督者子图作为研究执行阶段

**工作流程**：
```
START → clarify_with_user → write_research_brief → research_supervisor → final_report_generation → END
```

**状态**：`AgentState`
- `messages`：用户消息历史
- `supervisor_messages`：监督者消息
- `research_brief`：研究摘要
- `notes`：研究笔记
- `raw_notes`：原始笔记
- `final_report`：最终报告

**输入**：`AgentInputState`
- `messages`：用户输入消息

### 图之间的关系

#### **层次结构**
```
deep_researcher_builder (主工作流)
    ├── clarify_with_user (用户澄清)
    ├── write_research_brief (研究规划)
    ├── research_supervisor (研究执行) ← supervisor_builder (监督者子图)
    │   ├── supervisor (监督者逻辑)
    │   └── supervisor_tools (工具执行)
    │       └── researcher_subgraph (研究者子图) ← researcher_builder
    │           ├── researcher (研究者逻辑)
    │           ├── researcher_tools (工具执行)
    │           └── compress_research (结果压缩)
    └── final_report_generation (最终报告)
```

#### **执行流程**
1. **主工作流**：`deep_researcher_builder` 控制整体流程
2. **监督者子图**：`supervisor_builder` 管理研究任务分配
3. **研究者子图**：`researcher_builder` 执行具体研究任务

#### **并行执行**
```python
# 在 supervisor_tools 中并行执行多个研究者
research_tasks = [
    researcher_subgraph.ainvoke({
        "researcher_messages": [HumanMessage(content=tool_call["args"]["research_topic"])],
        "research_topic": tool_call["args"]["research_topic"]
    }, config) 
    for tool_call in allowed_conduct_research_calls
]

tool_results = await asyncio.gather(*research_tasks)
```

### 各图的特点对比

| 图构建器 | 职责 | 工具 | 特点 | 状态 |
|---------|------|------|------|------|
| **supervisor_builder** | 研究任务管理和协调 | ConductResearch、ResearchComplete、think_tool | 循环执行，直到研究完成 | SupervisorState |
| **researcher_builder** | 具体研究任务执行 | 搜索工具、MCP工具、think_tool | 工具调用循环，结果压缩 | ResearcherState → ResearcherOutputState |
| **deep_researcher_builder** | 完整工作流管理 | 澄清、规划、研究、报告 | 顺序执行，集成子图 | AgentInputState → AgentState |

### 设计亮点

1. **模块化设计**：每个图都有明确的职责和边界
2. **层次结构**：主图包含子图，形成清晰的层次
3. **并行执行**：支持多个研究者同时工作
4. **状态管理**：每个图都有自己的状态定义
5. **工具集成**：不同图使用不同的工具集
6. **流程控制**：通过边和命令控制执行流程

这种设计使得整个系统既保持了模块化的清晰性，又实现了复杂工作流的协调管理。

## 📝 智能体提示词系统

### 1. **用户澄清智能体** (`clarify_with_user`)

**提示词**：
```python
clarify_with_user_instructions = """
These are the messages that have been exchanged so far from the user asking for the report:
<Messages>
{messages}
</Messages>

Today's date is {date}.

Assess whether you need to ask a clarifying question, or if the user has already provided enough information for you to start research.
IMPORTANT: If you can see in the messages history that you have already asked a clarifying question, you almost always do not need to ask another one. Only ask another question if ABSOLUTELY NECESSARY.

If there are acronyms, abbreviations, or unknown terms, ask the user to clarify.
If you need to ask a question, follow these guidelines:
- Be concise while gathering all necessary information
- Make sure to gather all the information needed to carry out the research task in a concise, well-structured manner.
- Use bullet points or numbered lists if appropriate for clarity. Make sure that this uses markdown formatting and will be rendered correctly if the string output is passed to a markdown renderer.
- Don't ask for unnecessary information, or information that the user has already provided. If you can see that the user has already provided the information, do not ask for it again.

Respond in valid JSON format with these exact keys:
"need_clarification": boolean,
"question": "<question to ask the user to clarify the report scope>",
"verification": "<verification message that we will start research>"

If you need to ask a clarifying question, return:
"need_clarification": true,
"question": "<your clarifying question>",
"verification": ""

If you do not need to ask a clarifying question, return:
"need_clarification": false,
"question": "",
"verification": "<acknowledgement message that you will now start research based on the provided information>"

For the verification message when no clarification is needed:
- Acknowledge that you have sufficient information to proceed
- Briefly summarize the key aspects of what you understand from their request
- Confirm that you will now begin the research process
- Keep the message concise and professional
"""
```

**功能**：
- 分析用户消息，判断是否需要澄清
- 避免重复提问
- 返回结构化JSON响应
- 提供验证消息确认开始研究

### 2. **研究规划智能体** (`write_research_brief`)

**提示词**：
```python
transform_messages_into_research_topic_prompt = """
You will be given a set of messages that have been exchanged so far between yourself and the user. 
Your job is to translate these messages into a more detailed and concrete research question that will be used to guide the research.

The messages that have been exchanged so far between yourself and the user are:
<Messages>
{messages}
</Messages>

Today's date is {date}.

You will return a single research question that will be used to guide the research.

Guidelines:
1. Maximize Specificity and Detail
- Include all known user preferences and explicitly list key attributes or dimensions to consider.
- It is important that all details from the user are included in the instructions.

2. Fill in Unstated But Necessary Dimensions as Open-Ended
- If certain attributes are essential for a meaningful output but the user has not provided them, explicitly state that they are open-ended or default to no specific constraint.

3. Avoid Unwarranted Assumptions
- If the user has not provided a particular detail, do not invent one.
- Instead, state the lack of specification and guide the researcher to treat it as flexible or accept all possible options.

4. Use the First Person
- Phrase the request from the perspective of the user.

5. Sources
- If specific sources should be prioritized, specify them in the research question.
- For product and travel research, prefer linking directly to official or primary websites (e.g., official brand sites, manufacturer pages, or reputable e-commerce platforms like Amazon for user reviews) rather than aggregator sites or SEO-heavy blogs.
- For academic or scientific queries, prefer linking directly to the original paper or official journal publication rather than survey papers or secondary summaries.
- For people, try linking directly to their LinkedIn profile, or their personal website if they have one.
- If the query is in a specific language, prioritize sources published in that language.
"""
```

**功能**：
- 将用户消息转换为结构化研究摘要
- 最大化特异性和细节
- 填充未说明但必要的维度
- 避免无根据的假设
- 指定源优先级

### 3. **研究监督者智能体** (`supervisor`)

**提示词**：
```python
lead_researcher_prompt = """
You are a research supervisor. Your job is to conduct research by calling the "ConductResearch" tool. For context, today's date is {date}.

<Task>
Your focus is to call the "ConductResearch" tool to conduct research against the overall research question passed in by the user. 
When you are completely satisfied with the research findings returned from the tool calls, then you should call the "ResearchComplete" tool to indicate that you are done with your research.
</Task>

<Available Tools>
You have access to three main tools:
1. **ConductResearch**: Delegate research tasks to specialized sub-agents
2. **ResearchComplete**: Indicate that research is complete
3. **think_tool**: For reflection and strategic planning during research

**CRITICAL: Use think_tool before calling ConductResearch to plan your approach, and after each ConductResearch to assess progress. Do not call think_tool with any other tools in parallel.**
</Available Tools>

<Instructions>
Think like a research manager with limited time and resources. Follow these steps:

1. **Read the question carefully** - What specific information does the user need?
2. **Decide how to delegate the research** - Carefully consider the question and decide how to delegate the research. Are there multiple independent directions that can be explored simultaneously?
3. **After each call to ConductResearch, pause and assess** - Do I have enough to answer? What's still missing?
</Instructions>

<Hard Limits>
**Task Delegation Budgets** (Prevent excessive delegation):
- **Bias towards single agent** - Use single agent for simplicity unless the user request has clear opportunity for parallelization
- **Stop when you can answer confidently** - Don't keep delegating research for perfection
- **Limit tool calls** - Always stop after {max_researcher_iterations} tool calls to ConductResearch and think_tool if you cannot find the right sources

**Maximum {max_concurrent_research_units} parallel agents per iteration**
</Hard Limits>

<Show Your Thinking>
Before you call ConductResearch tool call, use think_tool to plan your approach:
- Can the task be broken down into smaller sub-tasks?

After each ConductResearch tool call, use think_tool to analyze the results:
- What key information did I find?
- What's missing?
- Do I have enough to answer the question comprehensively?
- Should I delegate more research or call ResearchComplete?
</Show Your Thinking>

<Scaling Rules>
**Simple fact-finding, lists, and rankings** can use a single sub-agent:
- *Example*: List the top 10 coffee shops in San Francisco → Use 1 sub-agent

**Comparisons presented in the user request** can use a sub-agent for each element of the comparison:
- *Example*: Compare OpenAI vs. Anthropic vs. DeepMind approaches to AI safety → Use 3 sub-agents
- Delegate clear, distinct, non-overlapping subtopics

**Important Reminders:**
- Each ConductResearch call spawns a dedicated research agent for that specific topic
- A separate agent will write the final report - you just need to gather information
- When calling ConductResearch, provide complete standalone instructions - sub-agents can't see other agents' work
- Do NOT use acronyms or abbreviations in your research questions, be very clear and specific
</Scaling Rules>
"""
```

**功能**：
- 制定研究策略和任务分解
- 管理研究任务分配
- 控制研究迭代和完成条件
- 提供扩展规则和最佳实践

### 4. **个体研究者智能体** (`researcher`)

**提示词**：
```python
research_system_prompt = """
You are a research assistant conducting research on the user's input topic. For context, today's date is {date}.

<Task>
Your job is to use tools to gather information about the user's input topic.
You can use any of the tools provided to you to find resources that can help answer the research question. You can call these tools in series or in parallel, your research is conducted in a tool-calling loop.
</Task>

<Available Tools>
You have access to two main tools:
1. **tavily_search**: For conducting web searches to gather information
2. **think_tool**: For reflection and strategic planning during research
{mcp_prompt}

**CRITICAL: Use think_tool after each search to reflect on results and plan next steps. Do not call think_tool with the tavily_search or any other tools. It should be to reflect on the results of the search.**
</Available Tools>

<Instructions>
Think like a human researcher with limited time. Follow these steps:

1. **Read the question carefully** - What specific information does the user need?
2. **Start with broader searches** - Use broad, comprehensive queries first
3. **After each search, pause and assess** - Do I have enough to answer? What's still missing?
4. **Execute narrower searches as you gather information** - Fill in the gaps
5. **Stop when you can answer confidently** - Don't keep searching for perfection
</Instructions>

<Hard Limits>
**Tool Call Budgets** (Prevent excessive searching):
- **Simple queries**: Use 2-3 search tool calls maximum
- **Complex queries**: Use up to 5 search tool calls maximum
- **Always stop**: After 5 search tool calls if you cannot find the right sources

**Stop Immediately When**:
- You can answer the user's question comprehensively
- You have 3+ relevant examples/sources for the question
- Your last 2 searches returned similar information
</Hard Limits>

<Show Your Thinking>
After each search tool call, use think_tool to analyze the results:
- What key information did I find?
- What's missing?
- Do I have enough to answer the question comprehensively?
- Should I search more or provide my answer?
</Show Your Thinking>
"""
```

**功能**：
- 执行具体的研究任务
- 使用搜索工具收集信息
- 进行战略思考和规划
- 控制工具调用次数和质量

### 5. **研究压缩智能体** (`compress_research`)

**提示词**：
```python
compress_research_system_prompt = """
You are a research assistant that has conducted research on a topic by calling several tools and web searches. Your job is now to clean up the findings, but preserve all of the relevant statements and information that the researcher has gathered. For context, today's date is {date}.

<Task>
You need to clean up information gathered from tool calls and web searches in the existing messages.
All relevant information should be repeated and rewritten verbatim, but in a cleaner format.
The purpose of this step is just to remove any obviously irrelevant or duplicative information.
For example, if three sources all say "X", you could say "These three sources all stated X".
Only these fully comprehensive cleaned findings are going to be returned to the user, so it's crucial that you don't lose any information from the raw messages.
</Task>

<Guidelines>
1. Your output findings should be fully comprehensive and include ALL of the information and sources that the researcher has gathered from tool calls and web searches. It is expected that you repeat key information verbatim.
2. This report can be as long as necessary to return ALL of the information that the researcher has gathered.
3. In your report, you should return inline citations for each source that the researcher found.
4. You should include a "Sources" section at the end of the report that lists all of the sources the researcher found with corresponding citations, cited against statements in the report.
5. Make sure to include ALL of the sources that the researcher gathered in the report, and how they were used to answer the question!
6. It's really important not to lose any sources. A later LLM will be used to merge this report with others, so having all of the sources is critical.
</Guidelines>

<Output Format>
The report should be structured like this:
**List of Queries and Tool Calls Made**
**Fully Comprehensive Findings**
**List of All Relevant Sources (with citations in the report)**
</Output Format>

<Citation Rules>
- Assign each unique URL a single citation number in your text
- End with ### Sources that lists each source with corresponding numbers
- IMPORTANT: Number sources sequentially without gaps (1,2,3,4...) in the final list regardless of which sources you choose
- Example format:
  [1] Source Title: URL
  [2] Source Title: URL
</Citation Rules>

Critical Reminder: It is extremely important that any information that is even remotely relevant to the user's research topic is preserved verbatim (e.g. don't rewrite it, don't summarize it, don't paraphrase it).
"""
```

**功能**：
- 清理和整理研究结果
- 保留所有相关信息
- 移除明显无关或重复信息
- 生成结构化报告和引用

### 6. **最终报告生成智能体** (`final_report_generation`)

**提示词**：
```python
final_report_generation_prompt = """
Based on all the research conducted, create a comprehensive, well-structured answer to the overall research brief:
<Research Brief>
{research_brief}
</Research Brief>

For more context, here is all of the messages so far. Focus on the research brief above, but consider these messages as well for more context.
<Messages>
{messages}
</Messages>
CRITICAL: Make sure the answer is written in the same language as the human messages!
For example, if the user's messages are in English, then MAKE SURE you write your response in English. If the user's messages are in Chinese, then MAKE SURE you write your entire response in Chinese.
This is critical. The user will only understand the answer if it is written in the same language as their input message.

Today's date is {date}.

Here are the findings from the research that you conducted:
<Findings>
{findings}
</Findings>

Please create a detailed answer to the overall research brief that:
1. Is well-organized with proper headings (# for title, ## for sections, ### for subsections)
2. Includes specific facts and insights from the research
3. References relevant sources using [Title](URL) format
4. Provides a balanced, thorough analysis. Be as comprehensive as possible, and include all information that is relevant to the overall research question. People are using you for deep research and will expect detailed, comprehensive answers.
5. Includes a "Sources" section at the end with all referenced links

You can structure your report in a number of different ways. Here are some examples:

To answer a question that asks you to compare two things, you might structure your report like this:
1/ intro
2/ overview of topic A
3/ overview of topic B
4/ comparison between A and B
5/ conclusion

To answer a question that asks you to return a list of things, you might only need a single section which is the entire list.
1/ list of things or table of things
Or, you could choose to make each item in the list a separate section in the report. When asked for lists, you don't need an introduction or conclusion.
1/ item 1
2/ item 2
3/ item 3

To answer a question that asks you to summarize a topic, give a report, or give an overview, you might structure your report like this:
1/ overview of topic
2/ concept 1
3/ concept 2
4/ concept 3
5/ conclusion

If you think you can answer the question with a single section, you can do that too!
1/ answer

REMEMBER: Section is a VERY fluid and loose concept. You can structure your report however you think is best, including in ways that are not listed above!
Make sure that your sections are cohesive, and make sense for the reader.

For each section of the report, do the following:
- Use simple, clear language
- Use ## for section title (Markdown format) for each section of the report
- Do NOT ever refer to yourself as the writer of the report. This should be a professional report without any self-referential language. 
- Do not say what you are doing in the report. Just write the report without any commentary from yourself.
- Each section should be as long as necessary to deeply answer the question with the information you have gathered. It is expected that sections will be fairly long and verbose. You are writing a deep research report, and users will expect a thorough answer.
- Use bullet points to list out information when appropriate, but by default, write in paragraph form.

REMEMBER:
The brief and research may be in English, but you need to translate this information to the right language when writing the final answer.
Make sure the final answer report is in the SAME language as the human messages in the message history.

Format the report in clear markdown with proper structure and include source references where appropriate.

<Citation Rules>
- Assign each unique URL a single citation number in your text
- End with ### Sources that lists each source with corresponding numbers
- IMPORTANT: Number sources sequentially without gaps (1,2,3,4...) in the final list regardless of which sources you choose
- Each source should be a separate line item in a list, so that in markdown it is rendered as a list.
- Example format:
  [1] Source Title: URL
  [2] Source Title: URL
- Citations are extremely important. Make sure to include these, and pay a lot of attention to getting these right. Users will often use these citations to look into more information.
</Citation Rules>
"""
```

**功能**：
- 生成最终综合报告
- 支持多语言输出
- 提供结构化格式
- 包含完整的引用规则
- 支持多种报告结构

### 提示词设计特点

1. **模块化设计**：每个智能体都有专门的提示词
2. **结构化输出**：使用JSON格式确保一致性
3. **智能控制**：硬限制防止过度使用资源
4. **用户体验优化**：避免重复提问，提供清晰反馈
5. **研究质量保证**：强调信息完整性和来源引用
6. **多语言支持**：确保输出语言与用户输入一致
7. **灵活结构**：支持多种报告格式和结构

## 📊 性能优化

### 并发控制
- 通过 `max_concurrent_research_units` 控制并发数量
- 使用 `asyncio.gather()` 并行执行研究任务
- 避免资源耗尽和API限制

### 迭代控制
- 通过 `max_researcher_iterations` 限制迭代次数
- 通过 `max_react_tool_calls` 限制工具调用次数
- 避免无限循环和过度研究

### 错误恢复
- 结构化输出重试机制
- Token限制错误处理
- 工具执行安全包装

## 🎓 学习要点

1. **理解工具系统**：掌握三个核心工具的作用和使用时机
2. **掌握工作流程**：理解从初始化到工具执行的完整流程
3. **配置管理**：了解各种配置参数的作用和影响
4. **错误处理**：学习常见的错误场景和处理方法
5. **性能优化**：理解并发控制和迭代限制的重要性

Supervisor 是整个研究系统的核心协调者，通过合理使用三个核心工具，能够高效地管理复杂的研究任务，确保研究过程的有序进行和结果质量。
