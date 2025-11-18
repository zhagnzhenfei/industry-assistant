#!/usr/bin/env python3
"""
记忆模块清理验证脚本
验证mem0依赖是否完全移除，自定义记忆功能是否正常工作
"""
import sys
import os
sys.path.append('app')

def test_memory_imports():
    """测试记忆模块导入"""
    print("=" * 50)
    print("🔍 测试记忆模块导入")
    print("=" * 50)

    try:
        # 测试新的配置类
        from configs.memory_config import MemoryConfig
        print("✅ MemoryConfig 导入成功")

        # 测试记忆服务模块
        from services.memory import CustomMemoryService, MemoryServiceFactory, get_memory_service
        print("✅ 记忆服务模块导入成功")

        # 测试路由模块
        from router.memory_router import router
        print("✅ memory_router 导入成功")

        return True
    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 其他错误: {e}")
        return False

def test_no_mem0_dependencies():
    """测试是否还有mem0依赖"""
    print("\n" + "=" * 50)
    print("🔍 检查残留的mem0依赖")
    print("=" * 50)

    # 检查是否还能导入mem0
    try:
        import mem0
        print("⚠️  mem0包仍然存在，但应该不再被使用")
        return False
    except ImportError:
        print("✅ mem0包已不存在")
        return True

def test_configuration():
    """测试配置功能"""
    print("\n" + "=" * 50)
    print("🔍 测试配置功能")
    print("=" * 50)

    try:
        from configs.memory_config import MemoryConfig

        # 测试配置加载
        config = MemoryConfig.get_memory_config()
        print(f"✅ 配置加载成功，启用状态: {config['enabled']}")

        # 测试配置验证
        is_valid = MemoryConfig.validate_config(config)
        print(f"✅ 配置验证结果: {is_valid}")

        return True
    except Exception as e:
        print(f"❌ 配置测试失败: {e}")
        return False

def test_memory_service():
    """测试记忆服务"""
    print("\n" + "=" * 50)
    print("🔍 测试记忆服务")
    print("=" * 50)

    try:
        from services.memory import get_memory_service

        # 测试服务获取
        service = get_memory_service()
        print(f"✅ 记忆服务获取成功: {type(service)}")

        if service:
            print("✅ 记忆服务已启用")
        else:
            print("ℹ️  记忆服务未启用（这是正常的，如果ENABLE_MEMORY=false）")

        return True
    except Exception as e:
        print(f"❌ 记忆服务测试失败: {e}")
        return False

def test_api_routes():
    """测试API路由"""
    print("\n" + "=" * 50)
    print("🔍 测试API路由")
    print("=" * 50)

    try:
        from router.memory_router import router

        # 检查路由信息
        print(f"✅ 记忆路由前缀: {router.prefix}")
        print(f"✅ 记忆路由标签: {router.tags}")
        print(f"✅ 路由数量: {len(router.routes)}")

        return True
    except Exception as e:
        print(f"❌ API路由测试失败: {e}")
        return False

def main():
    """主函数"""
    print("🚀 记忆模块清理验证")
    print("验证mem0依赖是否完全移除，自定义记忆功能是否正常")

    # 运行所有测试
    tests = [
        ("模块导入测试", test_memory_imports),
        ("mem0依赖检查", test_no_mem0_dependencies),
        ("配置功能测试", test_configuration),
        ("记忆服务测试", test_memory_service),
        ("API路由测试", test_api_routes),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name}异常: {e}")
            results.append((test_name, False))

    # 显示结果总结
    print("\n" + "=" * 50)
    print("📊 测试结果总结")
    print("=" * 50)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name}: {status}")

    print(f"\n总体结果: {passed}/{total} 测试通过")

    if passed == total:
        print("🎉 所有测试通过！mem0依赖清理成功。")
        return 0
    else:
        print("⚠️  部分测试失败，需要进一步检查。")
        return 1

if __name__ == "__main__":
    exit(main())