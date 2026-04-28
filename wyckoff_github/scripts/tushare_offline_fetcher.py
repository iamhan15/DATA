# -*- coding: utf-8 -*-
"""
Tushare 离线数据拉取模块

功能：
1. 按照 Tushare 限流规则（每分钟50次，每天8000次）拉取股票非复权日线行情
2. 将数据保存到本地 Parquet 格式作为离线数据源
3. 支持增量更新和全量更新
4. 提供断点续传功能

使用示例：
    from scripts.tushare_offline_fetcher import TushareOfflineFetcher
    
    fetcher = TushareOfflineFetcher()
    # 全量拉取所有股票最近一年的数据
    fetcher.fetch_all_stocks(days=365)
    
    # 或者拉取指定股票列表
    symbols = ["600519", "000001", "300750"]
    fetcher.fetch_symbols(symbols, days=365)
"""

import os
import time
import json
import pandas as pd
from datetime import date, timedelta
from pathlib import Path
from typing import List, Optional, Dict
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TushareRateLimiter:
    """Tushare API 限流器"""
    
    def __init__(self, max_calls_per_minute: int = 49, max_calls_per_day: int = 7999):
        self.max_calls_per_minute = max_calls_per_minute
        self.max_calls_per_day = max_calls_per_day
        
        # 记录调用时间
        self.minute_calls: list[float] = []
        self.day_calls: list[float] = []
        
        # 文件路径用于持久化计数
        self.state_file = Path("data/tushare_rate_limit_state.json")
        self._load_state()
    
    def _load_state(self):
        """从文件加载状态"""
        try:
            if self.state_file.exists():
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    self.minute_calls = state.get('minute_calls', [])
                    self.day_calls = state.get('day_calls', [])
        except Exception as e:
            logger.warning(f"加载限流状态失败: {e}")
    
    def _save_state(self):
        """保存状态到文件"""
        try:
            state = {
                'minute_calls': self.minute_calls[-100:],  # 只保留最近的调用记录
                'day_calls': self.day_calls[-1000:]  # 只保留最近的调用记录
            }
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(state, f)
        except Exception as e:
            logger.warning(f"保存限流状态失败: {e}")
    
    def wait_for_rate_limit(self):
        """等待直到可以发起新的API调用"""
        now = time.time()
        
        # 清理过期的调用记录
        self.minute_calls = [t for t in self.minute_calls if now - t < 60]
        self.day_calls = [t for t in self.day_calls if now - t < 86400]  # 24小时
        
        # 检查分钟限制
        while len(self.minute_calls) >= self.max_calls_per_minute:
            sleep_time = 60 - (now - self.minute_calls[0]) + 0.1
            if sleep_time > 0:
                logger.info(f"达到每分钟限制，等待 {sleep_time:.2f} 秒")
                time.sleep(sleep_time)
            now = time.time()
            self.minute_calls = [t for t in self.minute_calls if now - t < 60]
        
        # 检查日限制
        while len(self.day_calls) >= self.max_calls_per_day:
            sleep_time = 86400 - (now - self.day_calls[0]) + 0.1
            if sleep_time > 0:
                logger.info(f"达到每日限制，等待 {sleep_time:.2f} 秒")
                time.sleep(sleep_time)
            now = time.time()
            self.day_calls = [t for t in self.day_calls if now - t < 86400]
        
        # 记录本次调用
        self.minute_calls.append(now)
        self.day_calls.append(now)
        
        # 定期保存状态
        if len(self.minute_calls) % 10 == 0:
            self._save_state()


class TushareOfflineFetcher:
    """Tushare 离线数据拉取器"""
    
    def __init__(self, token: Optional[str] = None):
        """
        初始化拉取器
        
        Args:
            token: Tushare token，如果不提供则从环境变量或session中获取
        """
        self.token = token or self._get_token()
        if not self.token:
            raise ValueError("未找到 Tushare token，请设置 TUSHARE_TOKEN 环境变量或在 Streamlit session 中配置")
        
        self.rate_limiter = TushareRateLimiter(max_calls_per_minute=49, max_calls_per_day=7999)
        self.pro = self._init_pro_api()
        
        # 数据保存目录
        self.data_dir = Path("data/local_parquet_hist")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # 统计信息
        self.stats = {
            'total_symbols': 0,
            'success_count': 0,
            'failed_count': 0,
            'skipped_count': 0,
            'start_time': None,
            'end_time': None
        }
    
    def _get_token(self) -> Optional[str]:
        """获取 Tushare token"""
        # 尝试加载 .env 文件
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            pass  # python-dotenv 未安装，继续尝试其他方式
        
        # 优先尝试从 streamlit session 中获取用户配置
        try:
            import streamlit as st
            token = (st.session_state.get("tushare_token") or "").strip()
            if token:
                return token
        except Exception:
            pass
        
        # 如果 session 中没有，再尝试从环境变量获取
        token = os.getenv("TUSHARE_TOKEN", "").strip()
        return token if token else None
    
    def _init_pro_api(self):
        """初始化 Tushare Pro API"""
        try:
            import tushare as ts
            ts.set_token(self.token)
            pro = ts.pro_api()
            logger.info("Tushare Pro API 初始化成功")
            return pro
        except ImportError:
            raise ImportError("请安装 tushare: pip install tushare")
        except Exception as e:
            raise RuntimeError(f"Tushare Pro API 初始化失败: {e}")
    
    def get_stock_list(self) -> List[Dict[str, str]]:
        """获取A股股票列表"""
        try:
            logger.info("正在获取股票列表...")
            self.rate_limiter.wait_for_rate_limit()
            
            df = self.pro.stock_basic(
                exchange="",
                list_status="L",
                fields="ts_code,symbol,name"
            )
            
            if df is None or df.empty:
                raise RuntimeError("获取股票列表失败")
            
            stocks = []
            for _, row in df.iterrows():
                stocks.append({
                    'code': str(row['symbol']),
                    'name': str(row['name']),
                    'ts_code': str(row['ts_code'])
                })
            
            logger.info(f"获取到 {len(stocks)} 只股票")
            return stocks
            
        except Exception as e:
            logger.error(f"获取股票列表失败: {e}")
            raise
    
    def fetch_single_stock(self, symbol: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """
        拉取单只股票的历史数据
        
        Args:
            symbol: 股票代码 (如: 600519)
            start_date: 开始日期 (格式: YYYYMMDD)
            end_date: 结束日期 (格式: YYYYMMDD)
            
        Returns:
            DataFrame 或 None
        """
        try:
            # 转换股票代码格式
            if symbol.startswith('6'):
                ts_code = f"{symbol}.SH"
            elif symbol.startswith(('0', '3')):
                ts_code = f"{symbol}.SZ"
            else:
                ts_code = symbol
            
            logger.debug(f"拉取 {symbol} ({ts_code}) 数据: {start_date} 至 {end_date}")
            
            # 等待限流
            self.rate_limiter.wait_for_rate_limit()
            
            # 调用 Tushare API 获取非复权数据
            df = self.pro.daily(
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date
            )
            
            if df is None or df.empty:
                logger.warning(f"{symbol} 无数据返回")
                return None
            
            # 数据标准化处理
            df = df.rename(columns={
                'trade_date': 'date',
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'vol': 'volume',
                'amount': 'amount',
                'pct_chg': 'pct_chg'
            })
            
            # 转换日期格式
            df['date'] = pd.to_datetime(df['date'])
            
            # 选择需要的列
            columns_needed = ['date', 'open', 'high', 'low', 'close', 'volume', 'amount', 'pct_chg']
            df = df[columns_needed]
            
            # 按日期排序
            df = df.sort_values('date').reset_index(drop=True)
            
            return df
            
        except Exception as e:
            logger.error(f"拉取 {symbol} 数据失败: {e}")
            return None
    
    def save_stock_data(self, symbol: str, df: pd.DataFrame):
        """
        保存股票数据到本地 Parquet 文件（兼容现有格式）
        
        Args:
            symbol: 股票代码
            df: 数据 DataFrame
        """
        if df is None or df.empty:
            return
        
        file_path = self.data_dir / f"{symbol}.parquet"
        
        try:
            # 如果文件已存在，合并新旧数据
            if file_path.exists():
                existing_df = pd.read_parquet(file_path)
                
                # 兼容处理：确保日期格式一致
                if isinstance(existing_df.index, pd.DatetimeIndex) and 'date' not in existing_df.columns:
                    existing_df = existing_df.reset_index()
                    existing_df.rename(columns={'index': 'date'}, inplace=True)
                
                combined_df = pd.concat([existing_df, df])
                # 去重并按日期排序
                combined_df = combined_df.drop_duplicates(subset=['date'], keep='last')
                combined_df = combined_df.sort_values('date').reset_index(drop=True)
                df = combined_df
            
            # 保存为 Parquet 格式（date 作为列，与现有格式兼容）
            df.to_parquet(file_path, index=False)
            logger.debug(f"保存 {symbol} 数据到 {file_path} ({len(df)} 条记录)")
            
        except Exception as e:
            logger.error(f"保存 {symbol} 数据失败: {e}")
    
    def fetch_symbol(self, symbol: str, days: int = 365, force_update: bool = False):
        """
        拉取单只股票的数据并保存
        
        Args:
            symbol: 股票代码
            days: 拉取天数
            force_update: 是否强制更新（忽略已有数据）
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        
        # 检查是否已有数据
        file_path = self.data_dir / f"{symbol}.parquet"
        if file_path.exists() and not force_update:
            try:
                existing_df = pd.read_parquet(file_path)
                if not existing_df.empty:
                    last_date = existing_df['date'].max()
                    if isinstance(last_date, str):
                        last_date = pd.to_datetime(last_date)
                    
                    # 如果已有数据足够新，则跳过
                    if last_date.date() >= end_date - timedelta(days=1):
                        logger.info(f"{symbol} 数据已是最新，跳过")
                        self.stats['skipped_count'] += 1
                        return
            except Exception as e:
                logger.warning(f"检查 {symbol} 现有数据失败: {e}")
        
        # 拉取数据
        df = self.fetch_single_stock(
            symbol=symbol,
            start_date=start_date.strftime('%Y%m%d'),
            end_date=end_date.strftime('%Y%m%d')
        )
        
        if df is not None and not df.empty:
            self.save_stock_data(symbol, df)
            self.stats['success_count'] += 1
        else:
            self.stats['failed_count'] += 1
    
    def fetch_symbols(self, symbols: List[str], days: int = 365, force_update: bool = False):
        """
        批量拉取股票数据
        
        Args:
            symbols: 股票代码列表
            days: 拉取天数
            force_update: 是否强制更新
        """
        self.stats['total_symbols'] = len(symbols)
        self.stats['start_time'] = time.time()
        
        logger.info(f"开始批量拉取 {len(symbols)} 只股票的数据，时间范围: {days} 天")
        
        for i, symbol in enumerate(symbols, 1):
            logger.info(f"进度: [{i}/{len(symbols)}] 处理 {symbol}")
            
            try:
                self.fetch_symbol(symbol, days, force_update)
            except Exception as e:
                logger.error(f"处理 {symbol} 时发生错误: {e}")
                self.stats['failed_count'] += 1
            
            # 每处理100只股票显示一次统计信息
            if i % 100 == 0:
                self._print_progress(i)
        
        self.stats['end_time'] = time.time()
        self._print_final_stats()
    
    def fetch_all_stocks(self, days: int = 365, force_update: bool = False):
        """
        拉取所有A股股票的数据
        
        Args:
            days: 拉取天数
            force_update: 是否强制更新
        """
        logger.info("开始获取所有A股股票列表...")
        stocks = self.get_stock_list()
        symbols = [stock['code'] for stock in stocks]
        
        logger.info(f"将拉取 {len(symbols)} 只股票的数据")
        self.fetch_symbols(symbols, days, force_update)
    
    def _print_progress(self, current: int):
        """打印进度信息"""
        elapsed = time.time() - self.stats['start_time']
        rate = current / elapsed if elapsed > 0 else 0
        remaining = (self.stats['total_symbols'] - current) / rate if rate > 0 else 0
        
        logger.info(
            f"进度: {current}/{self.stats['total_symbols']} | "
            f"成功: {self.stats['success_count']} | "
            f"失败: {self.stats['failed_count']} | "
            f"跳过: {self.stats['skipped_count']} | "
            f"速率: {rate:.2f} 股/秒 | "
            f"预计剩余: {remaining/60:.1f} 分钟"
        )
    
    def _print_final_stats(self):
        """打印最终统计信息"""
        total_time = self.stats['end_time'] - self.stats['start_time']
        
        logger.info("=" * 60)
        logger.info("拉取完成统计:")
        logger.info(f"总股票数: {self.stats['total_symbols']}")
        logger.info(f"成功: {self.stats['success_count']}")
        logger.info(f"失败: {self.stats['failed_count']}")
        logger.info(f"跳过: {self.stats['skipped_count']}")
        logger.info(f"总耗时: {total_time/60:.2f} 分钟")
        logger.info(f"平均速率: {self.stats['total_symbols']/total_time:.2f} 股/秒")
        logger.info(f"API调用次数: {len(self.rate_limiter.day_calls)}")
        logger.info("=" * 60)
    
    def get_data_summary(self) -> Dict:
        """获取本地数据摘要信息"""
        summary = {
            'total_files': 0,
            'total_records': 0,
            'date_range': {},
            'symbols': []
        }
        
        parquet_files = list(self.data_dir.glob("*.parquet"))
        summary['total_files'] = len(parquet_files)
        
        for file_path in parquet_files:
            try:
                df = pd.read_parquet(file_path)
                
                # 兼容处理：如果 date 在索引中，转换为列
                if 'date' not in df.columns:
                    if isinstance(df.index, pd.DatetimeIndex):
                        df = df.reset_index()
                        df.rename(columns={'index': 'date'}, inplace=True)
                    else:
                        # 尝试寻找其他可能的日期列名
                        date_cols = [c for c in df.columns if 'date' in c.lower() or '日期' in c]
                        if date_cols:
                            df.rename(columns={date_cols[0]: 'date'}, inplace=True)
                        else:
                            logger.warning(f"读取 {file_path.name} 失败: 缺少日期信息")
                            continue
                
                if not df.empty:
                    symbol = file_path.stem
                    records = len(df)
                    
                    # 确保日期是 datetime 类型
                    df['date'] = pd.to_datetime(df['date'])
                    min_date = df['date'].min()
                    max_date = df['date'].max()
                    
                    summary['total_records'] += records
                    summary['symbols'].append({
                        'symbol': symbol,
                        'records': records,
                        'min_date': str(min_date.date()) if hasattr(min_date, 'date') else str(min_date),
                        'max_date': str(max_date.date()) if hasattr(max_date, 'date') else str(max_date)
                    })
                    
                    # 更新日期范围
                    if symbol not in summary['date_range']:
                        summary['date_range'][symbol] = {
                            'min': str(min_date.date()) if hasattr(min_date, 'date') else str(min_date),
                            'max': str(max_date.date()) if hasattr(max_date, 'date') else str(max_date)
                        }
                        
            except Exception as e:
                logger.warning(f"读取 {file_path.name} 失败: {e}")
        
        return summary


def main():
    """主函数 - 命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Tushare 离线数据拉取工具')
    parser.add_argument('--symbols', nargs='+', help='要拉取的股票代码列表')
    parser.add_argument('--all', action='store_true', help='拉取所有A股股票')
    parser.add_argument('--days', type=int, default=365, help='拉取天数 (默认: 365)')
    parser.add_argument('--force', action='store_true', help='强制更新，忽略已有数据')
    parser.add_argument('--summary', action='store_true', help='显示本地数据摘要')
    
    args = parser.parse_args()
    
    try:
        fetcher = TushareOfflineFetcher()
        
        if args.summary:
            summary = fetcher.get_data_summary()
            print("\n本地数据摘要:")
            print(f"总文件数: {summary['total_files']}")
            print(f"总记录数: {summary['total_records']}")
            print(f"股票数量: {len(summary['symbols'])}")
            return
        
        if args.all:
            fetcher.fetch_all_stocks(days=args.days, force_update=args.force)
        elif args.symbols:
            fetcher.fetch_symbols(args.symbols, days=args.days, force_update=args.force)
        else:
            parser.print_help()
            
    except Exception as e:
        logger.error(f"执行失败: {e}")
        raise


if __name__ == "__main__":
    main()
