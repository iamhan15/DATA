"""
市场筛选器模块（整合新三板过滤）
"""

from pathlib import Path
import pandas as pd
import logging
from datetime import datetime
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Optional
from dataclasses import dataclass

from config import *
from data_manager import LocalDataManager
from wyckoff_analyzer import WyckoffAnalyzer, StockAnalysis
### from neeq_filter import NEEQFilter

logger = logging.getLogger('WyckoffPro')


class MarketScreener:
    """全市场威科夫扫描器"""
    
    def __init__(self, local_mgr: LocalDataManager, analyzer: WyckoffAnalyzer):
        self.local = local_mgr
        self.analyzer = analyzer
        self.results_dir = Path("./scan_results")
        self.results_dir.mkdir(exist_ok=True)
        # 初始化新三板过滤器
        self.neeq_filter = NEEQFilter(enable_logging=False)
    
    def scan_all_optimized(self, min_score: int = 60, max_workers: int = 4, exclude_neeq: bool = True) -> pd.DataFrame:
        """全市场扫描
        
        Args:
            min_score: 最低评分阈值
            max_workers: 最大工作线程数
            exclude_neeq: 是否排除新三板股票（默认 True）
        """
        logger.info("="*70)
        logger.info("🚀 启动全市场威科夫扫描")
        logger.info("="*70)
        
        start = time.time()
        
        # 根据参数决定是否排除新三板
        symbols = self.local.get_all_symbols(exclude_neeq=exclude_neeq)
        if not symbols:
            logger.error("❌ 无数据可扫描")
            return pd.DataFrame()
        
        logger.info(f"📊 扫描标的：{len(symbols)} 只")
        
        # 统计新三板数量
        if not exclude_neeq:
            neeq_symbols = self.neeq_filter.extract_neeq(symbols)
            logger.info(f"   其中新三板：{len(neeq_symbols)} 只")
        
        # 获取股票信息
        stock_infos = {}
        if self.local.stock_list is not None and not self.local.stock_list.empty:
            for _, row in self.local.stock_list.iterrows():
                stock_infos[row['symbol']] = {
                    'name': row['name'],
                    'industry': row.get('industry', '未知')
                }
        
        # 并行分析
        results = []
        
        def analyze_symbol(symbol):
            try:
                df = self.local.get_daily_data(symbol, days=120)
                if df.empty or len(df) < 60:
                    return None
                
                info = stock_infos.get(symbol, {
                    'name': symbol,
                    'industry': '未知'
                })
                
                analysis = self.analyzer.analyze(symbol, info, df)
                return analysis
                
            except Exception as e:
                logger.debug(f"分析 {symbol} 失败：{e}")
                return None
        
        logger.info(f"🔬 开始分析（{max_workers}线程）...")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(analyze_symbol, s): s for s in symbols}
            
            for i, future in enumerate(as_completed(futures), 1):
                result = future.result()
                if result:
                    results.append(result)
                
                if i % 500 == 0:
                    logger.info(f"  进度：{i}/{len(symbols)} ({len(results)}有效)")
        
        # 过滤高评分
        high_score = [r for r in results if r.composite_score >= min_score]
        high_score.sort(key=lambda x: x.composite_score, reverse=True)
        
        elapsed = time.time() - start
        
        logger.info("="*70)
        logger.info(f"✅ 扫描完成！耗时：{elapsed:.2f}秒 ({len(symbols)/elapsed:.0f}只/秒)")
        logger.info(f"📈 高评分标的：{len(high_score)} 只 (阈值：{min_score})")
        if high_score:
            top5_names = ', '.join([r.name for r in high_score[:5]])
            logger.info(f"🏆 TOP5: {top5_names}")
            
            # 如果包含新三板，显示新三板中的高评分股票
            if not exclude_neeq:
                neeq_high_score = [r for r in high_score if NEEQFilter.is_neeq(r.symbol)]
                if neeq_high_score:
                    logger.info(f"🔶 新三板高评分：{len(neeq_high_score)} 只")
                    logger.info(f"   新三板 TOP3: {', '.join([r.name for r in neeq_high_score[:3]])}")
        logger.info("="*70)
        
        return self._save_and_return(high_score)
    
    def _save_and_return(self, results: List[StockAnalysis]) -> pd.DataFrame:
        """保存并返回结果"""
        if not results:
            return pd.DataFrame()
        
        data = []
        for r in results:
            data.append({
                '代码': r.symbol,
                '名称': r.name,
                '行业': r.industry,
                '当前价': r.technicals['current_price'],
                '威科夫阶段': r.phase.value,
                '评分': r.composite_score,
                '支撑位': r.technicals['support'],
                '阻力位': r.technicals['resistance'],
                'RS(%)': round(r.technicals['rs'], 2),
                '数据新鲜度': r.data_freshness,
                '建议': r.recommendation,
                '最新信号': r.signals[0].event.value if r.signals else '无'
            })
        
        df = pd.DataFrame(data)
        
        # 保存
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        csv_file = self.results_dir / f"wyckoff_scan_{timestamp}.csv"
        df.to_csv(csv_file, index=False, encoding='utf-8-sig')
        
        json_data = []
        for r in results:
            json_data.append({
                'symbol': r.symbol,
                'name': r.name,
                'phase': r.phase.value,
                'score': r.composite_score,
                'technicals': r.technicals,
                'signals': [{'event': s.event.value, 'date': s.date, 'confidence': s.confidence} for s in r.signals],
                'recommendation': r.recommendation
            })
        
        json_file = self.results_dir / f"wyckoff_scan_{timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
        
        # 软链接
        latest_csv = self.results_dir / "latest_scan.csv"
        if latest_csv.exists():
            latest_csv.unlink()
        latest_csv.symlink_to(csv_file.name)
        
        logger.info(f"💾 结果已保存：{csv_file}")
        
        return df