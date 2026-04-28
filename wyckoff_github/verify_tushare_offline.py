# -*- coding: utf-8 -*-
"""
Tushare 离线数据拉取模块 - 简单验证脚本

快速验证模块是否可以正常工作
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def check_dependencies():
    """检查依赖是否已安装"""
    print("=" * 60)
    print("检查依赖")
    print("=" * 60)
    
    dependencies = {
        'tushare': 'Tushare API 客户端',
        'pandas': '数据处理',
        'pyarrow': 'Parquet 文件支持'
    }
    
    all_ok = True
    for package, description in dependencies.items():
        try:
            mod = __import__(package)
            version = getattr(mod, '__version__', 'unknown')
            print(f"✓ {package:15} {version:15} - {description}")
        except ImportError as e:
            print(f"✗ {package:15} 未安装           - {description}")
            print(f"  请运行: pip install {package}")
            all_ok = False
    
    return all_ok


def check_token():
    """检查 Tushare Token 是否配置"""
    print("\n" + "=" * 60)
    print("检查 Tushare Token")
    print("=" * 60)
    
    import os
    
    # 尝试加载 .env 文件
    try:
        from dotenv import load_dotenv
        load_dotenv()
        print("✓ 已加载 .env 文件")
    except ImportError:
        print("⚠ python-dotenv 未安装，将仅检查环境变量")
    
    # 尝试从环境变量获取
    token = os.getenv("TUSHARE_TOKEN", "").strip()
    
    if token:
        print(f"✓ TUSHARE_TOKEN 已配置 (长度: {len(token)})")
        print(f"  Token 前缀: {token[:10]}...")
        return True
    else:
        print("✗ TUSHARE_TOKEN 未配置")
        print("\n请设置环境变量:")
        print("  Windows: $env:TUSHARE_TOKEN=\"your_token\"")
        print("  Linux/Mac: export TUSHARE_TOKEN=\"your_token\"")
        print("\n或在 .env 文件中配置:")
        print("  TUSHARE_TOKEN=your_token_here")
        print("\n或在 Streamlit Settings 页面中配置")
        return False


def test_module_import():
    """测试模块导入"""
    print("\n" + "=" * 60)
    print("测试模块导入")
    print("=" * 60)
    
    try:
        from scripts.tushare_offline_fetcher import TushareOfflineFetcher, TushareRateLimiter
        print("✓ TushareOfflineFetcher 导入成功")
        print("✓ TushareRateLimiter 导入成功")
        return True
    except ImportError as e:
        print(f"✗ 模块导入失败: {e}")
        return False


def test_rate_limiter():
    """测试限流器"""
    print("\n" + "=" * 60)
    print("测试限流器")
    print("=" * 60)
    
    try:
        from scripts.tushare_offline_fetcher import TushareRateLimiter
        import time
        
        limiter = TushareRateLimiter(max_calls_per_minute=5, max_calls_per_day=100)
        
        print("创建限流器（每分钟5次限制）...")
        
        # 测试3次调用
        start = time.time()
        for i in range(3):
            limiter.wait_for_rate_limit()
            print(f"  调用 {i+1} ✓")
        
        elapsed = time.time() - start
        print(f"3次调用耗时: {elapsed:.2f} 秒")
        print("✓ 限流器工作正常")
        
        return True
        
    except Exception as e:
        print(f"✗ 限流器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_data_directory():
    """检查数据目录"""
    print("\n" + "=" * 60)
    print("检查数据目录")
    print("=" * 60)
    
    data_dir = Path("data/local_parquet_hist")
    
    if data_dir.exists():
        print(f"✓ 数据目录存在: {data_dir}")
        
        # 统计现有文件
        parquet_files = list(data_dir.glob("*.parquet"))
        if parquet_files:
            print(f"✓ 已有 {len(parquet_files)} 个 Parquet 文件")
            
            # 显示前5个文件
            for f in parquet_files[:5]:
                print(f"  - {f.name}")
            if len(parquet_files) > 5:
                print(f"  ... 还有 {len(parquet_files) - 5} 个文件")
        else:
            print("  暂无数据文件（这是正常的，首次运行后会生成）")
    else:
        print(f"✗ 数据目录不存在，将自动创建")
        data_dir.mkdir(parents=True, exist_ok=True)
        print(f"✓ 已创建目录: {data_dir}")
    
    return True


def show_usage_examples():
    """显示使用示例"""
    print("\n" + "=" * 60)
    print("使用示例")
    print("=" * 60)
    
    examples = [
        ("拉取单只股票", "python scripts/tushare_offline_fetcher.py --symbols 600519 --days 365"),
        ("拉取多只股票", "python scripts/tushare_offline_fetcher.py --symbols 600519 000001 300750 --days 365"),
        ("拉取所有股票", "python scripts/tushare_offline_fetcher.py --all --days 365"),
        ("查看数据摘要", "python scripts/tushare_offline_fetcher.py --summary"),
        ("强制更新", "python scripts/tushare_offline_fetcher.py --symbols 600519 --days 365 --force"),
    ]
    
    for desc, cmd in examples:
        print(f"\n{desc}:")
        print(f"  {cmd}")


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("Tushare 离线数据拉取模块 - 验证工具")
    print("=" * 60)
    
    results = []
    
    # 1. 检查依赖
    results.append(("依赖检查", check_dependencies()))
    
    # 2. 检查 Token
    results.append(("Token 配置", check_token()))
    
    # 3. 测试模块导入
    results.append(("模块导入", test_module_import()))
    
    # 4. 测试限流器
    results.append(("限流器", test_rate_limiter()))
    
    # 5. 检查数据目录
    results.append(("数据目录", check_data_directory()))
    
    # 显示结果汇总
    print("\n" + "=" * 60)
    print("验证结果汇总")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{status} - {name}")
    
    print(f"\n总计: {passed}/{total} 检查通过")
    
    if passed == total:
        print("\n🎉 所有检查通过！模块可以正常使用。")
        show_usage_examples()
        return 0
    else:
        print(f"\n⚠️  {total - passed} 个检查失败，请根据上述提示修复。")
        return 1


if __name__ == "__main__":
    exit(main())