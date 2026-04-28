"""
本地数据管理模块
"""

import pandas as pd
import numpy as np
import json
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Dict, List
import logging

logger = logging.getLogger('DataManager')

class NEEQFilter:
    """全国中小企业股份转让系统(NEEQ) 代码过滤器"""
    @staticmethod
    def filter_out(symbols: List[str]) -> List[str]:
        # 常见NEEQ代码以'8'开头，或其他定制规则可补充
        return [s for s in symbols if not str(s).startswith('8')]

class LocalDataManager:
    """本地数据管理器"""
    
    def __init__(self, data_dir: Path = Path("./market_data")):
        self.data_dir = data_dir
        self.data_dir.mkdir(exist_ok=True)
        
        self.daily_dir = self.data_dir / "daily"
        self.list_dir = self.data_dir / "lists"
        self.meta_dir = self.data_dir / "meta"
        
        for d in [self.daily_dir, self.list_dir, self.meta_dir]:
            d.mkdir(exist_ok=True)
        
        self.meta_file = self.meta_dir / "data_index.json"
        self.data_index = self._load_index()
        self.stock_list = None
        self._load_stock_list()
        
        logger.info(f"数据管理器初始化: {len(self.data_index)} 只股票")
    
    def _load_index(self) -> Dict:
        if self.meta_file.exists():
            try:
                with open(self.meta_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"加载索引失败: {e}")
                return {}
        return {}
    
    def _save_index(self):
        try:
            temp_file = self.meta_file.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(self.data_index, f, ensure_ascii=False, indent=2)
            temp_file.replace(self.meta_file)
        except Exception as e:
            logger.error(f"保存索引失败: {e}")
    
    def _load_stock_list(self):
        list_file = self.list_dir / "stock_list.csv"
        if list_file.exists():
            try:
                self.stock_list = pd.read_csv(list_file, dtype={'symbol': str})
            except:
                self.stock_list = pd.DataFrame(columns=['symbol', 'name', 'industry', 'market'])
        else:
            self.stock_list = pd.DataFrame(columns=['symbol', 'name', 'industry', 'market'])
    
    def _standardize_dataframe(self, df: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """标准化数据框"""
        if df.empty:
            return df
        
        # 列名映射
        column_map = {
            '日期': 'date', 'trade_date': 'date', 'Date': 'date',
            '开盘': 'open', 'Open': 'open', '开盘价': 'open',
            '收盘': 'close', 'Close': 'close', '收盘价': 'close',
            '最高': 'high', 'High': 'high', '最高价': 'high',
            '最低': 'low', 'Low': 'low', '最低价': 'low',
            '成交量': 'volume', 'Volume': 'volume', 'vol': 'volume',
            '成交额': 'amount', 'Amount': 'amount',
            '换手率': 'turnover', 'Turnover': 'turnover'
        }
        
        # 大小写不敏感匹配
        rename_dict = {}
        for col in df.columns:
            if col in column_map:
                rename_dict[col] = column_map[col]
            else:
                col_lower = col.lower()
                for k, v in column_map.items():
                    if k.lower() == col_lower:
                        rename_dict[col] = v
                        break
        
        if rename_dict:
            df = df.rename(columns=rename_dict)
        
        # 检查必要列
        required = ['date', 'open', 'high', 'low', 'close', 'volume']
        missing = [c for c in required if c not in df.columns]
        
        if missing:
            if 'volume' in missing and 'amount' in df.columns and 'close' in df.columns:
                df['volume'] = df['amount'] / df['close']
                missing.remove('volume')
            
            if missing:
                logger.warning(f"{symbol} 缺少列: {missing}")
                return pd.DataFrame()
        
        # 日期处理
        if 'date' in df.columns:
            try:
                df['date'] = pd.to_datetime(df['date'])
            except:
                try:
                    df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')
                except:
                    return pd.DataFrame()
            df.set_index('date', inplace=True)
        
        # 数值转换
        for col in ['open', 'high', 'low', 'close', 'volume', 'amount']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # 清洗
        df = df.dropna(subset=['open', 'high', 'low', 'close'])
        df = df[(df['high'] >= df['low']) & (df['close'] > 0)]
        
        return df.sort_index()
    
    def _save_daily_data(self, symbol: str, df: pd.DataFrame, source: str = "unknown"):
        """保存日线数据"""
        file_path = self.daily_dir / f"{symbol}.parquet"
        
        try:
            df.to_parquet(file_path, compression='gzip', engine='pyarrow')
            
            self.data_index[symbol] = {
                'file': str(file_path.name),
                'rows': len(df),
                'start_date': str(df.index[0]),
                'end_date': str(df.index[-1]),
                'source': source,
                'updated_at': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"保存 {symbol} 失败: {e}")
            raise
    
    def import_from_csv_folder(self, csv_folder: Path) -> int:
        """从CSV文件夹导入"""
        if not csv_folder.exists():
            logger.error(f"文件夹不存在: {csv_folder}")
            return 0
        
        csv_files = list(csv_folder.glob("*.csv"))
        logger.info(f"发现 {len(csv_files)} 个CSV文件")
        
        imported = 0
        for i, csv_file in enumerate(csv_files, 1):
            try:
                symbol = csv_file.stem
                df = pd.read_csv(csv_file)
                df = self._standardize_dataframe(df, symbol)
                
                if not df.empty and len(df) >= 20:
                    self._save_daily_data(symbol, df, source=f"csv:{csv_file.name}")
                    imported += 1
                    
                    if i % 100 == 0:
                        logger.info(f"进度: {i}/{len(csv_files)}, 已导入 {imported}")
                        
            except Exception as e:
                logger.debug(f"导入 {csv_file.name} 失败: {e}")
        
        if imported > 0:
            self._save_index()
        
        logger.info(f"CSV导入完成: {imported}/{len(csv_files)} 只")
        return imported
    
    def create_sample_data(self, symbols: List[str] = None) -> int:
        """创建示例数据"""
        if symbols is None:
            symbols = ['000001', '000002', '600519', '000858', '002594', '300750', '601012', '601318']
        
        created = 0
        
        for i, symbol in enumerate(symbols):
            try:
                dates = pd.date_range(end=datetime.now(), periods=120, freq='B')
                np.random.seed(i)
                
                returns = np.random.randn(120) * 0.02
                prices = 100 * np.exp(np.cumsum(returns))
                prices = np.maximum(prices, 10)
                
                df = pd.DataFrame({
                    'date': dates,
                    'open': prices * (1 + np.random.randn(120) * 0.01),
                    'high': prices * (1 + abs(np.random.randn(120)) * 0.02),
                    'low': prices * (1 - abs(np.random.randn(120)) * 0.02),
                    'close': prices,
                    'volume': np.random.randint(1000000, 10000000, 120),
                    'amount': np.random.randint(10000000, 100000000, 120)
                })
                
                df.set_index('date', inplace=True)
                df['high'] = df[['open', 'close', 'high']].max(axis=1)
                df['low'] = df[['open', 'close', 'low']].min(axis=1)
                
                self._save_daily_data(symbol, df, source="sample")
                created += 1
                
            except Exception as e:
                logger.error(f"创建 {symbol} 失败: {e}")
        
        if created > 0:
            self._save_index()
        
        logger.info(f"创建 {created} 只示例股票")
        return created
    
    def get_daily_data(self, symbol: str, days: int = 120) -> pd.DataFrame:
        """读取日线数据"""
        if symbol not in self.data_index:
            return pd.DataFrame()
        
        try:
            info = self.data_index[symbol]
            file_path = self.daily_dir / info['file']
            
            if not file_path.exists():
                del self.data_index[symbol]
                self._save_index()
                return pd.DataFrame()
            
            df = pd.read_parquet(file_path, engine='pyarrow')
            
            if len(df) > days:
                df = df.tail(days)
            
            return df
            
        except Exception as e:
            logger.error(f"读取 {symbol} 失败: {e}")
            return pd.DataFrame()
    
    def get_all_symbols(self, exclude_neeq: bool = True) -> List[str]:
        symbols = sorted(self.data_index.keys()) if hasattr(self, 'data_index') else []
        if exclude_neeq:
            symbols = NEEQFilter.filter_out(symbols)
        return symbols
    
    def get_stock_info(self, symbol: str) -> Dict:
        info = {'symbol': symbol, 'name': symbol, 'industry': '未知', 'market': '未知'}
        
        if self.stock_list is not None and not self.stock_list.empty:
            matches = self.stock_list[self.stock_list['symbol'] == symbol]
            if not matches.empty:
                row = matches.iloc[0]
                info['name'] = row.get('name', symbol)
                info['industry'] = row.get('industry', '未知')
                info['market'] = row.get('market', '未知')
        
        if symbol in self.data_index:
            idx = self.data_index[symbol]
            info['data_rows'] = idx.get('rows', 0)
            info['data_range'] = f"{idx.get('start_date', '?')} ~ {idx.get('end_date', '?')}"
            info['data_source'] = idx.get('source', 'unknown')
        
        return info
    
    def get_data_summary(self) -> Dict:
        return {
            'total_symbols': len(self.data_index),
            'total_rows': sum(info.get('rows', 0) for info in self.data_index.values()),
            'date_range': {
                'min': min((info.get('start_date', '9999-12-31') for info in self.data_index.values()), default=None),
                'max': max((info.get('end_date', '1900-01-01') for info in self.data_index.values()), default=None)
            } if self.data_index else {'min': None, 'max': None}
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
            
            df = df[['symbol', 'name', 'industry', 'market']]
            df.to_csv(self.list_dir / "stock_list.csv", index=False, encoding='utf-8-sig')
            self.stock_list = df
            
            logger.info(f"股票列表导入: {len(df)} 只")
            return True
            
        except Exception as e:
            logger.error(f"导入股票列表失败: {e}")
            return False
