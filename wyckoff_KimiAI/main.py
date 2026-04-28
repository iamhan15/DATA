#!/usr/bin/env python3
"""
威科夫全市场选股系统 - 主程序入口
"""

import sys
from pathlib import Path

# 添加模块路径
sys.path.insert(0, str(Path(__file__).parent))

from config import *
from data_manager import LocalDataManager
from tdx_reader import TDXDataReader
from sync_manager import DataSyncManager
from wyckoff_analyzer import WyckoffAnalyzer
from visualizer import KLineVisualizer
from excel_report import ExcelReportGenerator
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd

from datetime import datetime
import time

def print_header():
    """打印系统标题"""
    print("="*70)
    print("🎯 威科夫全市场选股系统 - 模块化终极版")
    print("="*70)
    print("功能模块:")
    print("  📊 本地数据管理 (Parquet存储)")
    print("  📈 通达信/CSV数据导入")
    print("  🔄 自动数据同步")
    print("  🔍 威科夫分析引擎")
    print("  📉 K线可视化 (Matplotlib)")
    print("  📑 Excel报告生成")
    print("="*70)

def print_menu():
    """打印主菜单"""
    print("\n" + "="*70)
    print("【数据管理】")
    print("  1. 创建示例数据")
    print("  2. 从CSV文件夹导入")
    print("  3. 从通达信导入")
    print("  4. 导入股票列表")
    print("  5. 查看数据状态")
    print("【数据同步】")
    print("  6. 启动自动同步")
    print("  7. 手动执行同步")
    print("【分析扫描】")
    print("  8. 执行威科夫扫描")
    print("  9. 生成可视化图表")
    print("  10. 生成Excel报告")
    print("  11. 查看历史结果")
    print("【系统】")
    print("  0. 退出")
    print("="*70)

def process_symbol(symbol: str, data_mgr: LocalDataManager, analyzer: WyckoffAnalyzer):
    """处理单个股票符号"""
    try:
        info = data_mgr.get_stock_info(symbol)
        df = data_mgr.get_daily_data(symbol)
        if df is None or df.empty or len(df) < LOOKBACK_DAYS:
            return None
        return analyzer.analyze(symbol, info, df)
    except Exception as e:
        print(f"分析 {symbol} 失败: {e}")
        return None

def main():
    print_header()
    
    # 初始化模块
    print("\n🔧 初始化系统模块...")
    data_mgr = LocalDataManager(data_dir=DATA_DIR)
    analyzer = WyckoffAnalyzer(lookback=LOOKBACK_DAYS)
    visualizer = KLineVisualizer(CHART_STYLE)
    excel_gen = ExcelReportGenerator(EXCEL_TEMPLATE)
    sync_mgr = None
    
    # 显示初始状态
    summary = data_mgr.get_data_summary()
    print(f"✅ 系统就绪 | 当前数据: {summary['total_symbols']} 只股票")
    
    # 存储扫描结果供后续使用
    last_results = pd.DataFrame()

    try:
        while True:
            print_menu()
            
            choice = input("\n请选择操作 (0-11): ").strip()
            
            if choice == '0':
                print("👋 感谢使用，再见！")
                if sync_mgr:
                    sync_mgr.stop_auto_sync()
                break
            
            elif choice == '1':
                # 创建示例数据
                symbols_input = input("输入股票代码（逗号分隔，留空使用默认8只）: ").strip()
                symbols = [s.strip() for s in symbols_input.split(',')] if symbols_input else None
                
                count = data_mgr.create_sample_data(symbols)
                print(f"✅ 创建了 {count} 只示例股票")
            
            elif choice == '2':
                # CSV导入
                folder = input("CSV文件夹路径: ").strip()
                folder_path = Path(folder)
                if folder_path.exists():
                    count = data_mgr.import_from_csv_folder(folder_path)
                    print(f"✅ 导入了 {count} 只股票")
                else:
                    print(f"❌ 文件夹不存在: {folder}")
            
            elif choice == '3':
                # 通达信导入
                tdx_path = input("通达信路径（留空自动查找）: ").strip()
                reader = TDXDataReader(Path(tdx_path) if tdx_path else None)
                
                if not reader.tdx_path:
                    auto_path = reader.find_tdx_installation()
                    if auto_path:
                        reader.tdx_path = auto_path
                
                if reader.tdx_path:
                    total_imported = 0
                    for market in ['sh', 'sz']:
                        vipdoc = reader.tdx_path / "Vipdoc" / market / "lday"
                        if vipdoc.exists():
                            count = reader.import_from_tdx(data_mgr, vipdoc, market)
                            total_imported += count
                            print(f"✅ {market.upper()}: {count} 只")
                    print(f"\n📊 通达信导入总计: {total_imported} 只")
                else:
                    print("❌ 未找到通达信安装路径")
            
            elif choice == '4':
                # 导入股票列表
                csv_file = input("股票列表CSV文件路径: ").strip()
                if Path(csv_file).exists():
                    success = data_mgr.import_stock_list(Path(csv_file))
                    if success:
                        print("✅ 股票列表导入成功")
                else:
                    print(f"❌ 文件不存在: {csv_file}")
            
            elif choice == '5':
                # 查看数据状态
                summary = data_mgr.get_data_summary()
                print(f"\n📊 数据状态:")
                print(f"  股票总数: {summary['total_symbols']}")
                print(f"  总数据量: {summary['total_rows']:,} 条")
                print(f"  时间范围: {summary['date_range']['min'] or 'N/A'} ~ {summary['date_range']['max'] or 'N/A'}")
                
                if summary['total_symbols'] > 0:
                    print(f"\n前10只股票:")
                    for i, symbol in enumerate(data_mgr.get_all_symbols()[:10], 1):
                        info = data_mgr.get_stock_info(symbol)
                        print(f"  {i}. {symbol} - {info['name']} ({info.get('data_rows', 0)}条)")
            
            elif choice == '6':
                # 启动自动同步
                if sync_mgr is None:
                    sync_mgr = DataSyncManager(data_mgr)
                
                sync_mgr.start_auto_sync()
                print("✅ 自动同步已启动（每24小时）")
                print("⚠️  按Ctrl+C停止同步并返回菜单")
                
                try:
                    while True:
                        time.sleep(1)
                except KeyboardInterrupt:
                    print("\n🛑 停止同步")
                    sync_mgr.stop_auto_sync()
            
            elif choice == '7':
                # 手动同步
                if sync_mgr is None:
                    sync_mgr = DataSyncManager(data_mgr)
                
                result = sync_mgr.run_sync()
                print(f"\n同步结果: 更新{result['updated']} 不变{result['unchanged']} 失败{result['failed']}")
            
            elif choice == '8':
                # 执行威科夫扫描
                summary = data_mgr.get_data_summary()
                if summary['total_symbols'] == 0:
                    print("❌ 无数据，请先导入")
                    continue
                
                min_score = int(input(f"最低评分阈值（默认{DEFAULT_MIN_SCORE}）: ").strip() or DEFAULT_MIN_SCORE)
                workers = int(input(f"并行线程数（默认{DEFAULT_MAX_WORKERS}）: ").strip() or DEFAULT_MAX_WORKERS)

                symbols = data_mgr.get_all_symbols(exclude_neeq=True)
                if not symbols:
                    print("❌ 没有可用股票代码")
                    continue

                print(f"\n🔍 开始扫描 {len(symbols)} 只股票（{workers}线程）...")
                results = []
                with ThreadPoolExecutor(max_workers=workers) as executor:
                    futs = {executor.submit(process_symbol, s, data_mgr, analyzer): s for s in symbols}
                    for fut in as_completed(futs):
                        r = fut.result()
                        if r and getattr(r, "composite_score", 0) >= min_score:
                            results.append(r)

                if not results:
                    print("❌ 无符合条件的股票")
                    last_results = pd.DataFrame()
                else:
                    # 统一转成 DataFrame
                    last_results = pd.DataFrame([{
                        "代码": x.symbol,
                        "名称": x.name,
                        "行业": x.industry,
                        "威科夫阶段": x.phase.value,
                        "阶段置信度": x.phase_confidence,
                        "评分": x.composite_score,
                        "推荐": x.recommendation
                    } for x in results])
                    print("\n🏆 扫描完成，结果前20：")
                    print(last_results.sort_values("评分", ascending=False).head(20).to_string(index=False))

            elif choice == '9':
                # 生成可视化图表
                if last_results.empty:
                    print("❌ 无扫描结果，请先执行选项8")
                else:
                    # K线图绘制
                    print("生成K线图...")
                    visualizer.batch_plot_results(last_results.to_dict("records"), data_mgr, max_plots=20, output_dir=Path("./charts"))

            elif choice == '10':
                # 生成Excel报告
                if last_results.empty:
                    print("❌ 无扫描结果，请先执行选项8")
                else:
                    output_file = excel_gen.generate_report(last_results.to_dict("records"), data_mgr)
                    print(f"✅ Excel报告已生成：{output_file}")

            elif choice == '11':
                # 查看历史结果
                print("查看历史结果...")
                # 这里可以添加历史结果的查看逻辑

            else:
                print("❌ 无效选择，请重新输入")

    except KeyboardInterrupt:
        print("\n🛑 程序被用户中断")
    except Exception as e:
        print(f"程序出错: {e}")

if __name__ == "__main__":
    main()
