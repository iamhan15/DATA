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
            Path("C:/zd_pazq_hy"), Path("C:/tdx"),
            Path("D:/new_tdx"), Path("D:/tdx"),
            Path.home() / "AppData/Roaming/zd_pazq_hy",
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

        # 兼容大小写和旧目录
        if vipdoc_path and vipdoc_path.name.lower() == "vipdoc":
            vipdoc_path = vipdoc_path / market / "lday"
        if vipdoc_path and not vipdoc_path.exists():
            alt = vipdoc_path.parent / f"{market}lday"
            if alt.exists():
                vipdoc_path = alt

        if not vipdoc_path or not vipdoc_path.exists():
            logger.error(f"通达信目录不存在: {vipdoc_path}")
            return 0

        day_files = list(vipdoc_path.glob("*.day")) + list(vipdoc_path.glob("*.DAY"))
        logger.info(f"{market}: 发现 {len(day_files)} 个.day文件 ({vipdoc_path})")

        imported = 0
        for day_file in day_files:
            try:
                symbol = day_file.stem
                if symbol.startswith(('sh', 'sz', 'bj')):
                    symbol = symbol[2:]
                df = self.read_day_file(day_file)

                if df.empty:
                    logger.warning(f"{day_file.name} 解析到空数据，跳过")
                    continue
                if len(df) < 20:
                    logger.warning(f"{day_file.name} 数据行数太少 ({len(df)})，跳过")
                    continue

                try:
                    data_manager._save_daily_data(symbol, df, source=f"tdx:{market}")
                    imported += 1
                except Exception as e:
                    logger.error(f"保存{symbol}失败：{e}", exc_info=True)

            except Exception as e:
                logger.error(f"读取{day_file.name}失败：{e}", exc_info=True)

        if imported > 0:
            data_manager._save_index()

        logger.info(f"通达信导入完成: {imported} 只")
        return imported
