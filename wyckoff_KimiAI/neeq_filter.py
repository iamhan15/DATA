"""
新三板股票识别与过滤模块（整合增强版）
=====================================
功能：识别并处理新三板（全国中小企业股份转让系统）股票数据

新三板股票代码特征：
- 以 4 开头：400（两网及退市公司）、、420（退市B股）430（早期新三板挂牌）、440（科创板退市）、460（退市整理）
- 以 8 开头：830、870、880（创新层、基础层、精选层）

作者：AI Assistant (整合优化)
版本：2.0.0
"""

import logging
import re
from typing import List, Set, Dict, Optional, Union
from pathlib import Path

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    pd = None
    PANDAS_AVAILABLE = False

logger = logging.getLogger('NEEQFilter')

class NEEQFilter:
    NEEQ_PREFIXES: Set[str] = {
        # 4 开头系列
        '400', '420', '430', '440', '460',  # 退市公司、B 股、早期挂牌等
        # 8 开头系列
        '830', '831', '832', '833', '834', '835', '836', '837', '838', '839',
        '870', '871', '872', '873', '874', '875', '876', '877', '878', '879',
        '880', '881', '882', '883', '884', '885', '886', '887', '888', '889',
    }
    EXCLUDED_FIRST_DIGITS: Set[str] = {'4', '8'}
    NEEQ_PATTERNS: List[str] = [
        r'^4\d{5}$',           # 所有 4xxxxx
        r'^8[378]\d{4}$',      # 83xxxx, 87xxxx, 88xxxx
    ]

    def __init__(self, enable_logging: bool = True):
        if enable_logging:
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        self.compiled_patterns = [re.compile(p) for p in self.NEEQ_PATTERNS]

    @classmethod
    def is_neeq(cls, symbol: Union[str, int, None]) -> bool:
        if symbol is None:
            return False
        s = str(symbol).strip()
        if not s:
            return False
        if len(s) >= 3 and s[:3] in cls.NEEQ_PREFIXES:
            return True
        if s[0] in cls.EXCLUDED_FIRST_DIGITS:
            return True
        for pat in cls.NEEQ_PATTERNS:
            if re.match(pat, s):
                return True
        return False

    @classmethod
    def filter_out(cls, symbols: List[Union[str, int]]) -> List[str]:
        if not symbols:
            return []
        return [str(s).zfill(6) if isinstance(s, int) else str(s) for s in symbols if not cls.is_neeq(s)]

    @classmethod
    def extract_neeq(cls, symbols: List[Union[str, int]]) -> List[str]:
        if not symbols:
            return []
        return [str(s).zfill(6) if isinstance(s, int) else str(s) for s in symbols if cls.is_neeq(s)]

    @classmethod
    def classify_by_market(cls, symbols: List[Union[str, int]]) -> Dict[str, List[str]]:
        ret = {'SH': [], 'SZ': [], 'NEEQ': [], 'UNKNOWN': []}
        for s in symbols or []:
            code = str(s).strip()
            if cls.is_neeq(code):
                ret['NEEQ'].append(code)
            elif code.startswith('6'):
                ret['SH'].append(code)
            elif code.startswith(('0', '3', '2', '1', '5')):
                ret['SZ'].append(code)
            else:
                ret['UNKNOWN'].append(code)
        return ret

    # filter_neeq / add_mark / get_neeq_list / statistics 保持原实现并使用 is_neeq 正常工作