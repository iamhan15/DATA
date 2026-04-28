# Tushare 离线数据拉取 - 快速开始

## 5分钟快速上手

### 1. 安装依赖

```bash
pip install tushare pandas pyarrow
```

### 2. 配置 Tushare Token

#### 方法A: 环境变量（推荐）
```bash
# Windows PowerShell
$env:TUSHARE_TOKEN="your_token_here"

# Linux/Mac
export TUSHARE_TOKEN="your_token_here"
```

#### 方法B: 在代码中设置
```python
import os
os.environ['TUSHARE_TOKEN'] = 'your_token_here'
```

### 3. 拉取数据

#### 拉取单只股票
```bash
python scripts/tushare_offline_fetcher.py --symbols 600519 --days 365
```

#### 拉取多只股票
```bash
python scripts/tushare_offline_fetcher.py --symbols 600519 000001 300750 --days 365
```

#### 拉取所有股票（需要较长时间）
```bash
python scripts/tushare_offline_fetcher.py --all --days 365
```

### 4. 查看数据摘要

```bash
python scripts/tushare_offline_fetcher.py --summary
```

输出示例：
```
本地数据摘要:
总文件数: 3
总记录数: 750
股票数量: 3
```

### 5. 在 Python 中使用数据

```python
from scripts.tushare_offline_usage_example import load_offline_stock_data, analyze_stock

# 加载数据
df = load_offline_stock_data("600519")

# 分析股票
analyze_stock("600519", days=60)
```

## 常用命令速查

### 命令行

```bash
# 拉取指定股票最近30天数据
python scripts/tushare_offline_fetcher.py --symbols 600519 --days 30

# 强制更新（忽略已有数据）
python scripts/tushare_offline_fetcher.py --symbols 600519 --days 365 --force

# 查看帮助
python scripts/tushare_offline_fetcher.py --help
```

### Python API

```python
from scripts.tushare_offline_fetcher import TushareOfflineFetcher

# 创建拉取器
fetcher = TushareOfflineFetcher()

# 拉取单只股票
fetcher.fetch_symbol("600519", days=365)

# 批量拉取
symbols = ["600519", "000001", "300750"]
fetcher.fetch_symbols(symbols, days=365)

# 获取数据摘要
summary = fetcher.get_data_summary()
print(f"总文件数: {summary['total_files']}")
```

## 数据位置

- **Parquet 文件**: `data/local_parquet_hist/{股票代码}.parquet`
- **限流状态**: `data/tushare_rate_limit_state.json`

## 读取数据

```python
import pandas as pd
from pathlib import Path

# 读取股票数据
file_path = Path("data/local_parquet_hist/600519.parquet")
df = pd.read_parquet(file_path)

# 查看数据
print(df.head())
print(df.columns)
# 列: date, open, high, low, close, volume, amount, pct_chg
```

## 常见问题

### Q1: 提示 "未找到 Tushare token"
**A**: 确保已正确设置 `TUSHARE_TOKEN` 环境变量或在 Streamlit 中配置

### Q2: 拉取速度很慢
**A**: 这是正常的，程序会遵守 Tushare 的限流规则（每分钟50次）

### Q3: 某些股票拉取失败
**A**: 可能是新股、停牌或权限不足，程序会继续处理其他股票

### Q4: 如何更新数据？
**A**: 再次运行相同的命令，程序会自动进行增量更新

### Q5: 数据文件太大怎么办？
**A**: 
- 只拉取关注的股票
- 减少拉取天数
- 定期清理不需要的股票数据

## 下一步

- 📖 查看详细文档: [docs/TUSHARE_OFFLINE_FETCHER_GUIDE.md](docs/TUSHARE_OFFLINE_FETCHER_GUIDE.md)
- 🧪 运行测试: `python tests/test_tushare_offline_fetcher.py`
- 📊 查看使用示例: `python scripts/tushare_offline_usage_example.py`
- 🤖 配置自动拉取: [.github/TUSHARE_ACTIONS_SETUP.md](.github/TUSHARE_ACTIONS_SETUP.md)

## 技术支持

如有问题，请查看日志输出或查阅详细文档。