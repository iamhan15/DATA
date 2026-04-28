#!/usr/bin/env python3
"""
威科夫全市场选股系统 - 主程序入口（整合新三板过滤）
"""

import sys
from pathlib import Path
import concurrent.futures
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))

from config import *
from wyckoff_analyzer import WyckoffAnalyzer  # 使用增强版分析引擎
from data_manager import LocalDataManager
from tdx_reader import TDXDataReader
from sync_manager import DataSyncManager
from visualizer import KLineVisualizer
from excel_report import ExcelReportGenerator
from neeq_filter import NEEQFilter

from datetime import datetime
import time

NEEQ_CONFIG = {'auto_filter': True}

def process_symbol(symbol: str, data_mgr: LocalDataManager, analyzer: WyckoffAnalyzer):
    """处理单个股票的分析"""
    try:
        info = data_mgr.get_stock_info(symbol)
        df = data_mgr.get_daily_data(symbol)
        if df is None or df.empty or len(df) < 60:
            return None
        analysis = analyzer.analyze(symbol, info, df)
        return analysis
    except Exception as e:
        print(f"分析 {symbol} 失败: {e}")
        return None

def print_header():
    """打印系统标题"""
    print("="*70)
    print("🎯 威科夫全市场选股系统 - 模块化终极版")
    print("="*70)
    print("功能模块:")
    print("  📊 本地数据管理 (Parquet 存储)")
    print("  📈 通达信/CSV 数据导入")
    print("  🔄 自动数据同步")
    print("  🔍 威科夫分析引擎")
    print("  📉 K 线可视化 (Matplotlib)")
    print("  📑 Excel 报告生成")
    print("  🔶 新三板股票自动过滤")
    print("="*70)

def print_menu():
    """打印主菜单"""
    print("\n" + "="*70)
    print("【数据管理】")
    print("  1. 创建示例数据")
    print("  2. 从 CSV 文件夹导入")
    print("  3. 从通达信导入")
    print("  4. 导入股票列表")
    print("  5. 查看数据状态")
    print("【数据同步】")
    print("  6. 启动自动同步")
    print("  7. 手动执行同步")
    print("【分析扫描】")
    print("  8. 执行威科夫扫描")
    print("  9. 生成可视化图表")
    print("  10. 生成 Excel 报告")
    print("  11. 查看历史结果")
    print("【系统】")
    print("  0. 退出")
    print("="*70)

def main():
    print_header()
    
    # 初始化模块
    print("\n🔧 初始化系统模块...")
    data_mgr = LocalDataManager(data_dir=DATA_DIR)
    analyzer = WyckoffAnalyzer(lookback=60)  # 使用增强版分析引擎，<100分析量
    visualizer = KLineVisualizer(CHART_STYLE)
    excel_gen = ExcelReportGenerator(EXCEL_TEMPLATE)
    sync_mgr = None
    
    # 显示初始状态
    summary = data_mgr.get_data_summary()
    print(f"✅ 系统就绪 | 当前数据: {summary['total_symbols']} 只股票")
    
    # 存储扫描结果供后续使用
    last_results = pd.DataFrame()
    
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
                for market in ['sh', 'sz', 'bj']:
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
            print(f"  股票总数：{summary['total_symbols']}")
            print(f"  总数据量：{summary['total_rows']:,} 条")
            print(f"  时间范围：{summary['date_range']['min'] or 'N/A'} ~ {summary['date_range']['max'] or 'N/A'}")
            
            if summary['total_symbols'] > 0:
                # 显示新三板统计
                neeq_summary = data_mgr.get_neeq_summary()
                print(f"\n🔶 新三板统计:")
                print(f"  新三板数量：{neeq_summary['neeq_count']} 只 ({neeq_summary['neeq_ratio']:.1f}%)")
                if neeq_summary['neeq_symbols_sample']:
                    print(f"  示例代码：{', '.join(neeq_summary['neeq_symbols_sample'][:5])}")
                
                print(f"\n前 10 只股票:")
                for i, symbol in enumerate(data_mgr.get_all_symbols(exclude_neeq=True)[:10], 1):
                    info = data_mgr.get_stock_info(symbol)
                    market_flag = "🔶" if NEEQFilter.is_neeq(symbol) else ""
                    print(f"  {i}. {symbol} - {info['name']} ({info.get('data_rows', 0)}条) {market_flag}")
        
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
            
            # 询问是否包含新三板
            neeq_summary = data_mgr.get_neeq_summary()
            default_exclude = "Y" if NEEQ_CONFIG.get('auto_filter', True) else "N"
            exclude_input = input(f"是否过滤新三板股票？(Y/n, 默认{default_exclude}): ").strip().upper()
            exclude_neeq = (exclude_input != 'N') if exclude_input else (default_exclude == "Y")
            
            min_score = input(f"最低评分阈值（默认{DEFAULT_MIN_SCORE}）: ").strip()
            min_score = int(min_score) if min_score else DEFAULT_MIN_SCORE
            
            workers = input(f"并行线程数（默认{DEFAULT_MAX_WORKERS}）: ").strip()
            workers = int(workers) if workers else DEFAULT_MAX_WORKERS
            
            filter_status = "排除" if exclude_neeq else "包含"
            print(f"\n🔍 开始扫描（阈值{min_score}，{workers}线程，{filter_status}新三板）...")
            
            # 获取符号列表
            symbols = data_mgr.get_all_symbols(exclude_neeq=exclude_neeq)
            if not symbols:
                print("❌ 无有效股票符号")
                continue
            
            # 并行分析
            results = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
                futures = {executor.submit(process_symbol, symbol, data_mgr, analyzer): symbol for symbol in symbols}
                for future in concurrent.futures.as_completed(futures):
                    result = future.result()
                    if result and hasattr(result, 'composite_score') and result.composite_score >= min_score:
                        results.append(result)
            
            # 转换为 DataFrame
            if results:
                results_data = []
                for r in results:
                    signals_str = f"{len(r.signals)}个信号" if r.signals else "无"
                    if r.signals:
                        main_signal = r.signals[0].description[:20] + "..." if len(r.signals[0].description) > 20 else r.signals[0].description
                        signals_str = f"{signals_str} ({main_signal})"
                    
                    key_tech = f"RSI:{r.technicals.get('rsi', 0):.1f} VOL:{r.technicals.get('volume_ratio', 1):.1f}x"
                    
                    results_data.append({
                        '代码': r.symbol,
                        '名称': r.name,
                        '行业': r.industry,
                        '威科夫阶段': str(r.phase).split('.')[-1].replace("'", "").replace(">", ""),  # 提取枚举值
                        '阶段置信度': f"{r.phase_confidence:.1%}",
                        '综合评分': r.composite_score,
                        '信号': signals_str,
                        '关键指标': key_tech,
                        '建议': r.recommendation,
                        '数据新鲜度': r.data_freshness
                    })

                results_df = pd.DataFrame(results_data)
                last_results = results_df  # 保存结果
                
                print("\n" + "="*100)
                print("🏆 TOP 20 高评分标的")
                print("="*100)
                # 设置显示选项
                pd.set_option('display.max_colwidth', 30)
                pd.set_option('display.width', 120)
                print(results_df.head(20).to_string(index=False, justify='left'))
                
                # 行业分布
                industry_counts = results_df['行业'].value_counts()
                if not industry_counts.empty:
                    print(f"\n📊 行业分布 (TOP 5):")
                    for industry, count in industry_counts.head(5).items():
                        print(f"  {industry}: {count}只")

                # 阶段分布  
                phase_counts = results_df['威科夫阶段'].value_counts()
                if not phase_counts.empty:
                    print(f"\n📈 威科夫阶段分布:")
                    for phase, count in phase_counts.items():
                        print(f"  {phase}: {count}只")
            else:
                print("❌ 无符合条件的股票")
                last_results = pd.DataFrame()
        
        elif choice == '9':
            # 生成可视化图表
            if isinstance(last_results, pd.DataFrame) and not last_results.empty:
                print(f"\n📉 正在为前{min(20, len(last_results))}只股票生成K线图...")
                try:
                    plotted = visualizer.batch_plot_results(
                        last_results.to_dict('records'), 
                        data_mgr, 
                        max_plots=20,
                        output_dir=Path("./charts")
                    )
                    if plotted > 0:
                        print(f"✅ 已生成 {plotted} 张图表，保存到 ./charts/")
                    else:
                        print("⚠️  未生成任何图表")
                except Exception as e:
                    print(f"❌ 图表生成失败：{e}")
            else:
                print("❌ 无扫描结果，请先执行扫描（选项8）")
        
        elif choice == '10':
            # 生成Excel报告
            if isinstance(last_results, pd.DataFrame) and not last_results.empty:
                print(f"\n📑 正在生成Excel报告...")
                
                results_list = last_results.to_dict('records')
                
                output_file = excel_gen.generate_report(results_list, data_mgr)
                if output_file:
                    print(f"✅ Excel 报告已生成：{output_file}")
                else:
                    print("❌ Excel 报告生成失败，请检查日志")
            else:
                print("❌ 无扫描结果，请先执行扫描（选项 8）")
        
        elif choice == '11':
            # 查看历史结果
            scan_files = list(RESULTS_DIR.glob("wyckoff_scan_*.json"))
            
            if not scan_files:
                print("❌ 暂无历史扫描结果")
                continue
            
            print(f"\n📁 历史扫描结果（共{len(scan_files)}个）:")
            for i, file in enumerate(sorted(scan_files, reverse=True)[:10], 1):
                stat = file.stat()
                mtime = datetime.fromtimestamp(stat.st_mtime)
                print(f"  {i}. {file.name} ({mtime.strftime('%Y-%m-%d %H:%M')})")
            
            # 查看最新结果
            if scan_files:
                latest = max(scan_files, key=lambda f: f.stat().st_mtime)
                print(f"\n📊 最新结果预览:")
                try:
                    import json
                    with open(latest, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if isinstance(data, list) and len(data) > 0:
                            print(f"  股票数量：{len(data)}")
                            if len(data) > 0:
                                print(f"  最高评分：{max(s.get('综合评分', 0) for s in data)}")
                                print(f"  平均评分：{sum(s.get('综合评分', 0) for s in data) / len(data):.1f}")
                except Exception as e:
                    print(f"  ⚠️ 读取失败：{e}")
        
        else:
            print("❌ 无效输入，请重新选择")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 程序已中断")
    except Exception as e:
        print(f"\n❌ 发生错误：{e}")
        import traceback
        traceback.print_exc()