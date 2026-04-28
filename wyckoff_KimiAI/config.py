"""
全局配置文件
"""

import logging
from pathlib import Path
from datetime import datetime

# 路径配置
DATA_DIR = Path("./market_data")
RESULTS_DIR = Path("./scan_results")
LOGS_DIR = Path("./logs")

# 创建目录
for d in [DATA_DIR, RESULTS_DIR, LOGS_DIR]:
    d.mkdir(exist_ok=True)

# 日志配置
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_FILE = LOGS_DIR / f"wyckoff_{datetime.now().strftime('%Y%m%d')}.log"

logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# 分析参数
LOOKBACK_DAYS = 120
MIN_DATA_POINTS = 60
DEFAULT_MIN_SCORE = 60
DEFAULT_MAX_WORKERS = 4

# 评分阈值
SCORE_THRESHOLDS = {
    'excellent': 80,    # 强烈关注
    'good': 70,         # 关注
    'watch': 60,        # 观察
    'ignore': 60        # 以下忽略
}

# 可视化配置
CHART_STYLE = {
    'figure_size': (14, 10),
    'dpi': 150,
    'up_color': '#ef4444',      # 红色（A股涨）
    'down_color': '#22c55e',   # 绿色（A股跌）
    'volume_color': '#3b82f6',  # 蓝色
    'ma20_color': '#f59e0b',    # 橙色
    'ma60_color': '#8b5cf6',    # 紫色
    'support_color': '#10b981',  # 绿色
    'resistance_color': '#ef4444' # 红色
}

# Excel配置
EXCEL_TEMPLATE = {
    'header_color': '4472C4',
    'header_font_color': 'FFFFFF',
    'excellent_color': 'C6EFCE',  # 浅绿
    'good_color': 'FFEB9C',        # 浅黄
    'warning_color': 'FFC7CE'      # 浅红
}
