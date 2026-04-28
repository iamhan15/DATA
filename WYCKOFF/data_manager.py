"""
本地数据管理模块（整合新三板过滤）
"""

import pandas as pd
import numpy as np
import json
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import logging

from neeq_filter import NEEQFilter

logger = logging.getLogger('DataManager')

class LocalDataManager:
    """本地数据管理器"""
    
    def __init__(self, data_dir: Path = Path("./market_data")):
        self.data_dir = Path(data_dir)
        self.daily_dir = self.data_dir / "daily"
        self.index_path = self.data_dir / "index.json"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.daily_dir.mkdir(parents=True, exist_ok=True)
        self.data_index = self._load_index()
        
        # 初始化新三板过滤器
        self.neeq_filter = NEEQFilter(enable_logging=False)
               
        logger.info(f"数据管理器初始化：{len(self.data_index)} 只股票")
    
    def is_neeq_stock(self, symbol: str) -> bool:
        """判断是否为新三板股票（使用专业过滤器）"""
        return NEEQFilter.is_neeq(symbol)
    
    def filter_neeq_stocks(self, symbols: List[str]) -> List[str]:
        """过滤掉新三板股票"""
        if not symbols:
            return []
        
        filtered = self.neeq_filter.filter_out(symbols)
        removed_count = len(symbols) - len(filtered)
        
        if removed_count > 0:
            logger.info(f"过滤掉 {removed_count} 只新三板股票")
        
        return filtered
    
    def get_all_symbols(self, exclude_neeq: bool = True) -> List[str]:
        symbols = sorted(self.data_index.keys())
        if exclude_neeq:
            symbols = NEEQFilter.filter_out(symbols)
        return symbols
    
    def get_stock_info(self, symbol: str) -> Dict:
        symbol = str(symbol).strip()
        if not symbol:
            return {"name": "", "industry": "", "rows": 0}
        return self.data_index.get(symbol, {"name": symbol, "industry": "未知", "rows": 0})

    def get_daily_data(self, symbol: str) -> pd.DataFrame:
        symbol = str(symbol).strip()
        path = self.daily_dir / f"{symbol}.parquet"
        if not path.exists():
            return pd.DataFrame()
        df = pd.read_parquet(path)
        if "date" in df.columns:
            df = df.set_index("date")
        return df.sort_index()

    def _load_index(self) -> Dict:
        """加载数据索引"""
        if self.index_path.exists():
            try:
                with open(self.index_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"加载索引失败：{e}")
                return {}
        return {}
    
    def _save_index(self):
        """保存数据索引"""
        try:
            with open(self.index_path, 'w', encoding='utf-8') as f:
                json.dump(self.data_index, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存索引失败：{e}")
    
    def _save_daily_data(self, symbol: str, df: pd.DataFrame, source: str = "unknown") -> bool:
        symbol = str(symbol).strip()
        if not symbol or df is None or df.empty:
            return False

        df = df.copy()
        if 'date' in df.columns:
            df.set_index('date', inplace=True)
        df.sort_index(inplace=True)

        self.daily_dir.mkdir(parents=True, exist_ok=True)
        file_path = self.daily_dir / f"{symbol}.parquet"
        try:
            df.to_parquet(file_path)
        except Exception as e:
            logger.error(f"写入日线数据失败 {file_path}: {e}", exc_info=True)
            raise
        self.data_index[symbol] = {
            "name": symbol,
            "source": source,
            "rows": len(df),
            "updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        return True

    def get_data_summary(self) -> Dict:
        return {
            'total_symbols': len(self.data_index),
            'total_rows': sum(info.get('rows', 0) for info in self.data_index.values()),
            'date_range': {'min': None, 'max': None}
        }

    def get_neeq_summary(self) -> Dict:
        all_symbols = list(self.data_index.keys())
        neeq_symbols = [s for s in all_symbols if NEEQFilter.is_neeq(s)]
        return {
            'neeq_count': len(neeq_symbols),
            'neeq_ratio': len(neeq_symbols) / len(all_symbols) if all_symbols else 0,
            'neeq_symbols_sample': neeq_symbols[:5]
        }

    def import_stock_list(self, csv_file: Path) -> bool:
        """导入股票列表"""
        try:
            df = pd.read_csv(csv_file, dtype={'symbol': str})
            
            column_map = {
                '代码': 'symbol', 'symbol': 'symbol',
                '名称': 'name', 'name': 'name',
                '行业': 'industry', 'industry': 'industry',
                '市场': 'market', 'market': 'market'
            }
            df = df.rename(columns={k: v for k, v in column_map.items() if k in df.columns})
            
            if 'symbol' not in df.columns:
                logger.error("股票列表缺少symbol列")
                return False
            
            for col in ['name', 'industry', 'market']:
                if col not in df.columns:
                    df[col] = '未知'
            
            if 'market' not in df.columns:
                df['market'] = df['symbol'].apply(lambda x: 'SH' if str(x).startswith('6') else 'SZ')
            
            if '评分' in df.columns:
                df['评分'] = pd.to_numeric(df['评分'], errors='coerce').fillna(0)
            
            df = df[['symbol', 'name', 'industry', 'market']]
            
            # 保存到索引（如果需要）
            for _, row in df.iterrows():
                symbol = row['symbol']
                self.data_index[symbol] = {
                    "name": row['name'],
                    "industry": row['industry'],
                    "rows": 0,  # 初始为0，实际数据导入时更新
                    "source": "list_import",
                    "updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }
            
            self._save_index()  # 保存索引
            
            logger.info(f"股票列表导入: {len(df)} 只")
            return True
            
        except Exception as e:
            logger.error(f"导入股票列表失败: {e}")
            return False
