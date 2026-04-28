"""
数据自动同步模块
"""

import pandas as pd
import requests
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional
import time
import threading
import schedule
import logging

logger = logging.getLogger('SyncManager')

class DataSyncManager:
    """数据自动同步管理器"""
    
    def __init__(self, data_manager, config: Optional[Dict] = None):
        self.local = data_manager
        self.config = config or {
            'sync_interval_hours': 24,
            'update_days': 5,
            'max_workers': 2
        }
        self.is_running = False
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'Mozilla/5.0'})
    
    def start_auto_sync(self):
        """启动自动同步"""
        if self.is_running:
            return
        
        self.is_running = True
        self.run_sync()
        
        schedule.every(self.config['sync_interval_hours']).hours.do(self.run_sync)
        
        def scheduler():
            while self.is_running:
                schedule.run_pending()
                time.sleep(60)
        
        threading.Thread(target=scheduler, daemon=True).start()
        logger.info(f"自动同步已启动，间隔: {self.config['sync_interval_hours']}小时")
    
    def stop_auto_sync(self):
        self.is_running = False
    
    def run_sync(self, symbols: List[str] = None) -> Dict:
        """执行同步"""
        logger.info("="*70)
        logger.info("启动数据同步")
        logger.info("="*70)
        
        start = time.time()
        
        if symbols is None:
            symbols = self._get_sync_candidates()
        
        logger.info(f"计划同步: {len(symbols)} 只")
        
        updated = failed = unchanged = 0
        
        for i, symbol in enumerate(symbols, 1):
            try:
                result = self._sync_single(symbol)
                if result == 'updated':
                    updated += 1
                elif result == 'unchanged':
                    unchanged += 1
                else:
                    failed += 1
                
                if i % 50 == 0:
                    logger.info(f"进度: {i}/{len(symbols)} (更{updated} 不{unchanged} 败{failed})")
                    time.sleep(1)
                    
            except Exception as e:
                failed += 1
                logger.debug(f"同步 {symbol} 失败: {e}")
        
        elapsed = time.time() - start
        
        logger.info(f"同步完成: 更{updated} 不{unchanged} 败{failed}, 耗时{elapsed:.1f}秒")
        
        return {'updated': updated, 'failed': failed, 'unchanged': unchanged}
    
    def _get_sync_candidates(self) -> List[str]:
        candidates = []
        
        for symbol in self.local.get_all_symbols():
            df = self.local.get_daily_data(symbol, days=5)
            
            if df.empty:
                candidates.append(symbol)
                continue
            
            last_date = df.index[-1]
            days_stale = (datetime.now() - last_date).days
            
            if days_stale >= 2:
                candidates.append(symbol)
        
        return candidates
    
    def _sync_single(self, symbol: str) -> str:
        try:
            new_data = self._fetch_eastmoney(symbol)
            
            if new_data.empty:
                return 'failed'
            
            existing = self.local.get_daily_data(symbol, days=10000)
            
            if existing.empty:
                combined = new_data
            else:
                last_existing = existing.index[-1]
                new_records = new_data[new_data.index > last_existing]
                
                if len(new_records) == 0:
                    return 'unchanged'
                
                combined = pd.concat([existing, new_records])
                combined = combined[~combined.index.duplicated(keep='last')]
                combined = combined.sort_index()
            
            self.local._save_daily_data(symbol, combined, source="sync")
            return 'updated'
            
        except Exception as e:
            return 'failed'
    
    def _fetch_eastmoney(self, symbol: str) -> pd.DataFrame:
        try:
            secid = f"0.{symbol}" if symbol.startswith('6') else f"1.{symbol}"
            url = "http://push2his.eastmoney.com/api/qt/stock/kline/get"
            
            end = datetime.now()
            start = end - timedelta(days=self.config['update_days'] + 5)
            
            params = {
                'secid': secid,
                'fields1': 'f1,f2,f3,f4,f5,f6',
                'fields2': 'f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61',
                'klt': '101', 'fqt': '1',
                'beg': start.strftime("%Y%m%d"),
                'end': end.strftime("%Y%m%d"),
                '_': int(time.time()*1000)
            }
            
            response = self.session.get(url, params=params, timeout=10)
            data = response.json()
            
            if 'data' not in data or 'klines' not in data['data']:
                return pd.DataFrame()
            
            klines = data['data']['klines']
            parsed = []
            
            for line in klines:
                parts = line.split(',')
                if len(parts) >= 6:
                    parsed.append({
                        'date': parts[0],
                        'open': float(parts[1]),
                        'close': float(parts[2]),
                        'high': float(parts[3]),
                        'low': float(parts[4]),
                        'volume': float(parts[5]),
                        'amount': float(parts[6]) if len(parts) > 6 else 0
                    })
            
            df = pd.DataFrame(parsed)
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)
            
            return df
            
        except Exception as e:
            return pd.DataFrame()
