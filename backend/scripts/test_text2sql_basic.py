"""
Text2SQL基础测试脚本
测试MCP PostgreSQL工具和Text2SQL智能体的基本功能
"""
import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.database.mcp_postgres_client import MCPPostgresClient
from app.services.agent_orchestration.text2sql_tool import query_database_simple


async def test_mcp_client():
    """测试MCP客户端基础功能"""
    print("="*70)
    print("测试1: MCP PostgreSQL客户端")
    print("="*70)
    
    client = MCPPostgresClient()
    
    # 测试1.1：健康检查
    print("\n1.1 健康检查...")
    is_healthy = await client.health_check()
    if is_healthy:
        print("✅ MCP服务健康")
    else:
        print("❌ MCP服务不可用，请确保mcp-service正在运行")
        return False
    
    # 测试1.2：列出表
    print("\n1.2 列出所有表...")
    tables = await client.list_tables()
    if tables:
        print(f"✅ 找到{len(tables)}张表:")
        for table in tables:
            print(f"   - {table['name']}: {table.get('comment', '无注释')} ({table.get('row_count', 0)}行)")
    else:
        print("❌ 未找到任何表")
        return False
    
    # 测试1.3：获取表结构
    print("\n1.3 获取companies表结构...")
    schema = await client.get_schemas(["companies"])
    if schema:
        print("✅ Schema获取成功")
        print(schema[:500] + "..." if len(schema) > 500 else schema)
    else:
        print("❌ Schema获取失败")
    
    # 测试1.4：执行SQL查询
    print("\n1.4 执行SQL查询...")
    result = await client.execute_query("SELECT name, industry FROM companies LIMIT 3")
    if result.get("success"):
        print(f"✅ 查询成功，返回{result.get('row_count', 0)}行")
        for row in result.get("data", []):
            print(f"   {row}")
    else:
        print(f"❌ 查询失败: {result.get('error_message')}")
    
    # 测试1.5：安全验证（尝试危险SQL）
    print("\n1.5 测试安全验证...")
    result = await client.execute_query("DELETE FROM companies")
    if not result.get("success") and result.get("error_type") == "security_error":
        print("✅ 安全验证有效，危险SQL被阻止")
    else:
        print("❌ 安全验证失败")
    
    # 测试1.6：错误处理（列名错误）
    print("\n1.6 测试错误处理...")
    result = await client.execute_query("SELECT compny_name FROM companies")
    if not result.get("success"):
        print(f"✅ 错误处理正常")
        print(f"   错误类型: {result.get('error_type')}")
        print(f"   错误信息: {result.get('error_message')}")
        print(f"   修正建议: {result.get('fix_suggestions')}")
    else:
        print("❌ 应该检测到列名错误")
    
    return True


async def test_text2sql_agent():
    """测试Text2SQL智能体"""
    print("\n" + "="*70)
    print("测试2: Text2SQL智能体")
    print("="*70)
    
    # 测试用例
    test_cases = [
        {
            "question": "数据库中有多少家公司？",
            "expected_keywords": ["COUNT", "companies"]
        },
        {
            "question": "列出所有互联网行业的公司",
            "expected_keywords": ["companies", "industry", "互联网"]
        },
        {
            "question": "2024年发布了多少篇研报？",
            "expected_keywords": ["research_reports", "2024", "COUNT"]
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n测试 2.{i}: {test_case['question']}")
        print("-" * 60)
        
        try:
            result = await query_database_simple(test_case['question'])
            
            if result.get("success"):
                print("✅ 查询成功")
                print(f"   SQL: {result.get('generated_sql', 'N/A')}")
                print(f"   结果行数: {len(result.get('final_results', []))}")
                
                # 检查SQL是否包含预期关键词
                sql = result.get('generated_sql', '').upper()
                missing_keywords = [
                    kw for kw in test_case.get('expected_keywords', [])
                    if kw.upper() not in sql
                ]
                
                if missing_keywords:
                    print(f"   ⚠️  警告: SQL可能不完全正确，缺少关键词: {missing_keywords}")
                
            else:
                print(f"❌ 查询失败")
                error = result.get("last_error", {})
                print(f"   错误: {error.get('error_message', 'N/A')}")
                print(f"   尝试次数: {result.get('current_attempt', 1) - 1}")
                
        except Exception as e:
            print(f"❌ 异常: {e}")


async def test_error_recovery():
    """测试错误恢复机制"""
    print("\n" + "="*70)
    print("测试3: SQL错误自动修正")
    print("="*70)
    
    # 这个测试需要Text2SQL能够处理拼写错误
    print("\n提示: 此测试需要LLM能够理解错误信息并修正SQL")
    print("如果LLM配置正确，应该能自动修正拼写错误。\n")
    
    # 暂时跳过，因为需要完整的错误反馈机制
    print("⏭️  暂时跳过（需要完整的LangGraph错误反馈机制）")


async def main():
    """主测试函数"""
    print("\n" + "="*70)
    print("🧪 Text2SQL 测试套件")
    print("="*70)
    print("\n前置条件检查:")
    print("  1. PostgreSQL数据库已创建并初始化")
    print("  2. MCP服务正在运行 (http://localhost:8000)")
    print("  3. 环境变量已设置\n")
    
    input("按Enter键开始测试...")
    
    # 测试1：MCP客户端
    mcp_ok = await test_mcp_client()
    
    if not mcp_ok:
        print("\n❌ MCP客户端测试失败，跳过后续测试")
        print("\n💡 请检查:")
        print("  - MCP服务是否运行: http://localhost:8000/health")
        print("  - PostgreSQL是否可连接")
        print("  - 环境变量是否正确")
        return
    
    # 测试2：Text2SQL智能体
    await test_text2sql_agent()
    
    # 测试3：错误恢复
    await test_error_recovery()
    
    print("\n" + "="*70)
    print("✅ 测试完成！")
    print("="*70)
    print("\n📊 总结:")
    print("  - MCP客户端: ✅ 正常")
    print("  - Text2SQL基础功能: 查看上述结果")
    print("  - 错误恢复: 待实现\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n测试中断")
    except Exception as e:
        print(f"\n\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

