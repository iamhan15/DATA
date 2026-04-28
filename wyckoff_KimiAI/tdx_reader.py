"""
通达信数据读取模块
"""

import pandas as pd
import struct
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger('TDXReader')

class TDXDataReader:
    """通达信数据读取器"""
    
    def __init__(self, tdx_path: Optional[Path] = None):
        self.tdx_path = tdx_path
        self.day_format = struct.Struct('<IIIIIfII')
    
    def find_tdx_installation(self) -> Optional[Path]:
        """自动查找通达信安装路径"""
        possible_paths = [
            Path("C:/zd_pazq_hy"), Path("C:/new_tdx64"),
            Path("D:/new_tdx"), Path("D:/tdx"),
            Path.home() / "AppData/Roaming/通达信",
        ]
        
        for path in possible_paths:
            if path.exists() and (path / "Vipdoc").exists():
                logger.info(f"找到通达信: {path}")
                return path
        
        return None
    
    def read_day_file(self, day_file: Path) -> pd.DataFrame:
        """读取.day文件"""
        try:
            if not day_file.exists():
                return pd.DataFrame()
            
            with open(day_file, 'rb') as f:
                data = f.read()
            
            record_size = self.day_format.size
            num_records = len(data) // record_size
            
            records = []
            for i in range(num_records):
                offset = i * record_size
                record = data[offset:offset + record_size]
                
                date, open_p, high, low, close, amount, vol, _ = self.day_format.unpack(record)
                
                records.append({
                    'date': f"{date//10000:04d}-{(date%10000)//100:02d}-{date%100:02d}",
                    'open': open_p / 100.0,
                    'high': high / 100.0,
                    'low': low / 100.0,
                    'close': close / 100.0,
                    'amount': amount / 10000.0,
                    'volume': vol
                })
            
            df = pd.DataFrame(records)
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)
            
            return df.sort_index()
            
        except Exception as e:
            logger.error(f"读取失败 {day_file}: {e}")
            return pd.DataFrame()
    
    def import_from_tdx(self, data_manager, vipdoc_path: Optional[Path] = None, market: str = "sh") -> int:
        """从通达信导入"""
        if not vipdoc_path and self.tdx_path:
            vipdoc_path = self.tdx_path / "Vipdoc" / market / "lday"
        
        if not vipdoc_path or not vipdoc_path.exists():
            logger.error(f"通达信目录不存在: {vipdoc_path}")
            return 0
        
        day_files = list(vipdoc_path.glob("*.day"))
        logger.info(f"{market}: 发现 {len(day_files)} 个.day文件")
        
        imported = 0
        for day_file in day_files:
            try:
                symbol = day_file.stem[2:] if day_file.stem.startswith(('sh', 'sz')) else day_file.stem
                
                df = self.read_day_file(day_file)
                
                if not df.empty and len(df) >= 20:
                    data_manager._save_daily_data(symbol, df, source=f"tdx:{market}")
                    imported += 1
                    
                    if imported % 100 == 0:
                        logger.info(f"已导入 {imported}...")
                        
            except Exception as e:
                logger.debug(f"导入 {day_file.name} 失败: {e}")
        
        if imported > 0:
            data_manager._save_index()
        
        logger.info(f"通达信导入完成: {imported} 只")
        return imported
