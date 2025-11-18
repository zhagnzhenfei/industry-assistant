"""
测试PostgreSQL MCP工具
直接测试mcp-service提供的PostgreSQL工具
"""
import asyncio
import httpx
import json


BASE_URL = "http://localhost:8000/api/v1"
SERVER_ID = "postgres-server"


async def test_health():
    """测试服务健康状态"""
    print("="*70)
    print("测试：MCP服务健康检查")
    print("="*70)
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8000/health")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ 服务健康")
                print(f"   工具数量: {data.get('tools_count')}")
                print(f"   服务器数量: {data.get('servers_count')}")
                return True
            else:
                print(f"❌ 健康检查失败: {response.status_code}")
                return False
    except Exception as e:
        print(f"❌ 无法连接到MCP服务: {e}")
        print("   请确保MCP服务正在运行: cd mcp-app && python -m app.main")
        return False


async def test_list_servers():
    """测试获取服务器列表"""
    print("\n" + "="*70)
    print("测试：获取MCP服务器列表")
    print("="*70)
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/servers")
            response.raise_for_status()
            
            data = response.json()
            servers = data.get("servers", [])
            
            print(f"✅ 找到{len(servers)}个服务器")
            
            # 查找PostgreSQL服务器
            postgres_server = None
            for server in servers:
                print(f"   - {server['id']}: {server['name']} ({server.get('status')})")
                if server['id'] == SERVER_ID:
                    postgres_server = server
            
            if postgres_server:
                print(f"\n✅ PostgreSQL服务器已注册")
                print(f"   状态: {postgres_server.get('status')}")
                print(f"   工具数量: {postgres_server.get('tools_count')}")
                return True
            else:
                print(f"\n❌ 未找到PostgreSQL服务器")
                return False
                
    except Exception as e:
        print(f"❌ 获取服务器列表失败: {e}")
        return False


async def test_list_tools():
    """测试获取PostgreSQL工具列表"""
    print("\n" + "="*70)
    print("测试：获取PostgreSQL工具列表")
    print("="*70)
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/servers/{SERVER_ID}/tools")
            response.raise_for_status()
            
            tools = response.json()
            
            print(f"✅ 找到{len(tools)}个工具:")
            for tool in tools:
                print(f"   - {tool['name']}: {tool['description'][:60]}...")
            
            return len(tools) >= 6
            
    except Exception as e:
        print(f"❌ 获取工具列表失败: {e}")
        return False


async def call_tool(tool_name: str, arguments: dict):
    """调用MCP工具"""
    url = f"{BASE_URL}/servers/{SERVER_ID}/tools/{tool_name}/call"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            url,
            json={"arguments": arguments}
        )
        response.raise_for_status()
        return response.json()


async def test_list_tables_tool():
    """测试sql_db_list_tables工具"""
    print("\n" + "="*70)
    print("测试：sql_db_list_tables工具")
    print("="*70)
    
    try:
        result = await call_tool("sql_db_list_tables", {})
        
        # 检查响应结构
        if "data" in result:
            data = result["data"]
        else:
            data = result
        
        if data.get("success"):
            tables = data.get("tables", [])
            print(f"✅ 成功获取{len(tables)}张表:")
            
            for table in tables:
                print(f"   - {table['name']}")
                print(f"     注释: {table.get('comment', '无')}")
                print(f"     行数: {table.get('row_count', 0)}")
                print(f"     列数: {table.get('columns_count', 0)}")
            
            # 检查预期的表
            expected_tables = ['companies', 'analysts', 'research_reports', 'industries', 'report_topics']
            table_names = [t['name'] for t in tables]
            
            missing = [t for t in expected_tables if t not in table_names]
            if missing:
                print(f"\n⚠️  缺少预期的表: {missing}")
                return False
            
            return True
        else:
            print(f"❌ 工具返回失败: {data.get('error')}")
            return False
            
    except Exception as e:
        print(f"❌ 工具调用失败: {e}")
        return False


async def test_schema_tool():
    """测试sql_db_schema工具"""
    print("\n" + "="*70)
    print("测试：sql_db_schema工具")
    print("="*70)
    
    try:
        result = await call_tool(
            "sql_db_schema",
            {"table_names": ["companies"]}
        )
        
        if "data" in result:
            data = result["data"]
        else:
            data = result
        
        if data.get("success"):
            schema = data.get("schema", "")
            print(f"✅ 成功获取schema ({len(schema)}字符)")
            print("\nSchema预览:")
            print(schema[:500] + "..." if len(schema) > 500 else schema)
            
            # 检查是否包含关键信息
            checks = {
                "CREATE TABLE": "包含建表语句",
                "companies": "包含表名",
                "PRIMARY KEY": "包含主键定义",
                "sample": "包含示例数据"
            }
            
            print("\n内容检查:")
            all_ok = True
            for keyword, desc in checks.items():
                if keyword.lower() in schema.lower():
                    print(f"   ✅ {desc}")
                else:
                    print(f"   ❌ 缺少: {desc}")
                    all_ok = False
            
            return all_ok
        else:
            print(f"❌ 工具返回失败: {data.get('error')}")
            return False
            
    except Exception as e:
        print(f"❌ 工具调用失败: {e}")
        return False


async def test_query_tool():
    """测试sql_db_query工具"""
    print("\n" + "="*70)
    print("测试：sql_db_query工具")
    print("="*70)
    
    test_queries = [
        {
            "name": "简单查询",
            "sql": "SELECT name, industry FROM companies LIMIT 3",
            "should_succeed": True
        },
        {
            "name": "聚合查询",
            "sql": "SELECT industry, COUNT(*) as count FROM companies GROUP BY industry",
            "should_succeed": True
        },
        {
            "name": "安全验证（应被拒绝）",
            "sql": "DELETE FROM companies",
            "should_succeed": False
        },
        {
            "name": "列名错误（应返回错误）",
            "sql": "SELECT compny_name FROM companies",
            "should_succeed": False
        }
    ]
    
    all_passed = True
    
    for i, test in enumerate(test_queries, 1):
        print(f"\n{i}. {test['name']}")
        print(f"   SQL: {test['sql']}")
        
        try:
            result = await call_tool("sql_db_query", {"query": test['sql']})
            
            if "data" in result:
                data = result["data"]
            else:
                data = result
            
            success = data.get("success", False)
            
            if success == test['should_succeed']:
                print(f"   ✅ 结果符合预期")
                
                if success:
                    row_count = data.get("row_count", 0)
                    print(f"   返回{row_count}行数据")
                else:
                    error_type = data.get("error_type", "unknown")
                    error_msg = data.get("error_message", "N/A")
                    print(f"   错误类型: {error_type}")
                    print(f"   错误信息: {error_msg}")
                    
                    if data.get("fix_suggestions"):
                        print(f"   修正建议: {data['fix_suggestions']}")
            else:
                print(f"   ❌ 结果不符合预期")
                print(f"   预期成功: {test['should_succeed']}, 实际: {success}")
                all_passed = False
                
        except Exception as e:
            print(f"   ❌ 异常: {e}")
            all_passed = False
    
    return all_passed


async def test_query_checker():
    """测试sql_db_query_checker工具"""
    print("\n" + "="*70)
    print("测试：sql_db_query_checker工具")
    print("="*70)
    
    test_cases = [
        ("SELECT * FROM companies", True, "有效的SELECT"),
        ("DELETE FROM companies", False, "无效的DELETE")
    ]
    
    for sql, should_be_valid, desc in test_cases:
        print(f"\n测试: {desc}")
        print(f"   SQL: {sql}")
        
        try:
            result = await call_tool("sql_db_query_checker", {"query": sql})
            
            if "data" in result:
                data = result["data"]
            else:
                data = result
            
            is_valid = data.get("is_valid", False)
            
            if is_valid == should_be_valid:
                print(f"   ✅ 验证结果正确")
            else:
                print(f"   ❌ 验证结果错误")
                print(f"   预期: {should_be_valid}, 实际: {is_valid}")
                
        except Exception as e:
            print(f"   ❌ 异常: {e}")


async def main():
    """主测试函数"""
    print("\n" + "="*70)
    print("🧪 PostgreSQL MCP工具测试套件")
    print("="*70)
    print("\n测试目标: 验证mcp-service的PostgreSQL工具是否正常工作\n")
    
    # 测试1：健康检查
    if not await test_health():
        print("\n❌ 服务不可用，终止测试")
        return
    
    # 测试2：服务器列表
    if not await test_list_servers():
        print("\n❌ PostgreSQL服务器未注册，终止测试")
        return
    
    # 测试3：工具列表
    if not await test_list_tools():
        print("\n❌ 工具列表有问题")
        return
    
    # 测试4：各个工具功能
    await test_list_tables_tool()
    await test_schema_tool()
    await test_query_tool()
    await test_query_checker()
    
    print("\n" + "="*70)
    print("✅ 所有测试完成！")
    print("="*70)
    print("\n📊 总结:")
    print("  - MCP服务: ✅")
    print("  - PostgreSQL服务器: ✅")
    print("  - 工具功能: 查看上述结果")
    print("\n下一步: 运行 test_text2sql_basic.py 测试Text2SQL智能体")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n测试中断")
    except Exception as e:
        print(f"\n\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

