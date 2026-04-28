# Tushare 离线数据拉取模块 - 完整使用手册

## 📖 目录

1. [快速开始](#快速开始)
2. [功能特性](#功能特性)
3. [安装配置](#安装配置)
4. [使用方法](#使用方法)
5. [API 参考](#api-参考)
6. [数据格式](#数据格式)
7. [最佳实践](#最佳实践)
8. [故障排除](#故障排除)
9. [扩展开发](#扩展开发)

---

## 快速开始

### 1. 安装依赖

```bash
pip install tushare pandas pyarrow
```

### 2. 配置 Token

```bash
# Windows PowerShell
$env:TUSHARE_TOKEN="your_token_here"

# Linux/Mac
export TUSHARE_TOKEN="your_token_here"
```

### 3. 拉取数据

```bash
# 拉取单只股票
python scripts/tushare_offline_fetcher.py --symbols 600519 --days 365

# 查看数据摘要
python scripts/tushare_offline_fetcher.py --summary
```

### 4. 在代码中使用

```python
from scripts.tushare_offline_fetcher import TushareOfflineFetcher

fetcher = TushareOfflineFetcher()
fetcher.fetch_symbol("600519", days=365)
```

---

## 功能特性

### ✅ 核心功能

- **智能限流**: 严格遵守 Tushare API 限制（每分钟50次，每天8000次）
- **增量更新**: 自动检测已有数据，只拉取缺失或过期的数据
- **断点续传**: 保存调用状态，中断后可继续执行
- **批量处理**: 支持单股、指定列表、全市场三种模式
- **高效存储**: Parquet 格式，压缩率高，读取速度快
- **进度跟踪**: 实时显示拉取进度和统计信息

### ✅ 高级功能

- **数据摘要**: 查询本地数据的统计信息
- **强制更新**: 忽略已有数据，重新拉取
- **灵活配置**: 自定义拉取天数、股票列表等
- **错误处理**: 单个股票失败不影响其他股票
- **日志记录**: 详细的操作日志便于调试

### ✅ 自动化

- **GitHub Actions**: 定时自动拉取和更新数据
- **手动触发**: 支持自定义参数的手动运行
- **自动提交**: 可选择将数据推送到 Git 仓库

---

## 安装配置

### 系统要求

- Python 3.10+
- 操作系统: Windows / Linux / macOS

### 依赖包

```bash
pip install tushare>=1.2.0 pandas>=1.5.0 pyarrow>=10.0.0
```

### Token 配置

#### 方法1: 环境变量（推荐）

```bash
# Windows
set TUSHARE_TOKEN=your_token_here

# Linux/Mac
export TUSHARE_TOKEN=your_token_here
```

#### 方法2: Python 代码

```python
import os
os.environ['TUSHARE_TOKEN'] = 'your_token_here'
```

#### 方法3: Streamlit Session

在 Streamlit 应用的 Settings 页面中配置

### 获取 Tushare Token

1. 访问 [Tushare Pro](https://tushare.pro/)
2. 注册并登录
3. 在个人中心获取 Token
4. 确保账户有足够积分（基础行情通常需要120积分）

---

## 使用方法

### 命令行使用

#### 基本命令

```bash
python scripts/tushare_offline_fetcher.py [选项]
```

#### 可用选项

| 选项 | 说明 | 示例 |
|------|------|------|
| `--symbols` | 股票代码列表 | `--symbols 600519 000001` |
| `--all` | 拉取所有A股 | `--all` |
| `--days` | 拉取天数（默认365） | `--days 180` |
| `--force` | 强制更新 | `--force` |
| `--summary` | 显示数据摘要 | `--summary` |
| `--help` | 显示帮助 | `--help` |

#### 使用示例

```bash
# 示例1: 拉取单只股票最近一年数据
python scripts/tushare_offline_fetcher.py --symbols 600519 --days 365

# 示例2: 拉取多只股票
python scripts/tushare_offline_fetcher.py --symbols 600519 000001 300750 --days 365

# 示例3: 拉取所有股票（需要较长时间）
python scripts/tushare_offline_fetcher.py --all --days 365

# 示例4: 强制更新（忽略已有数据）
python scripts/tushare_offline_fetcher.py --symbols 600519 --days 365 --force

# 示例5: 查看本地数据摘要
python scripts/tushare_offline_fetcher.py --summary

# 示例6: 拉取最近30天数据
python scripts/tushare_offline_fetcher.py --symbols 600519 --days 30
```

### Python API 使用

#### 基本用法

```python
from scripts.tushare_offline_fetcher import TushareOfflineFetcher

# 创建拉取器实例
fetcher = TushareOfflineFetcher()

# 拉取单只股票
fetcher.fetch_symbol("600519", days=365)

# 批量拉取
symbols = ["600519", "000001", "300750"]
fetcher.fetch_symbols(symbols, days=365)

# 拉取所有股票
fetcher.fetch_all_stocks(days=365)

# 获取数据摘要
summary = fetcher.get_data_summary()
print(f"总文件数: {summary['total_files']}")
print(f"总记录数: {summary['total_records']}")
```

#### 高级用法

```python
from scripts.tushare_offline_fetcher import TushareOfflineFetcher

# 创建拉取器
fetcher = TushareOfflineFetcher()

# 设置自定义参数
watchlist = ["600519", "000001", "300750"]

# 拉取并监控进度
for i, symbol in enumerate(watchlist, 1):
    print(f"处理 [{i}/{len(watchlist)}]: {symbol}")
    try:
        fetcher.fetch_symbol(symbol, days=365, force_update=False)
    except Exception as e:
        print(f"失败: {e}")

# 查看详细统计
print(f"\n统计信息:")
print(f"成功: {fetcher.stats['success_count']}")
print(f"失败: {fetcher.stats['failed_count']}")
print(f"跳过: {fetcher.stats['skipped_count']}")
```

#### 读取和使用数据

```python
import pandas as pd
from pathlib import Path

def load_stock_data(symbol: str) -> pd.DataFrame:
    """加载股票数据"""
    file_path = Path("data/local_parquet_hist") / f"{symbol}.parquet"
    
    if not file_path.exists():
        return pd.DataFrame()
    
    df = pd.read_parquet(file_path)
    
    # 确保日期列存在
    if 'date' not in df.columns:
        if isinstance(df.index, pd.DatetimeIndex):
            df = df.reset_index()
            df.rename(columns={'index': 'date'}, inplace=True)
    
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'])
    
    return df.sort_values('date').reset_index(drop=True)

# 使用示例
df = load_stock_data("600519")
if not df.empty:
    print(f"最新收盘价: {df['close'].iloc[-1]:.2f}")
    print(f"数据条数: {len(df)}")
```

---

## API 参考

### TushareOfflineFetcher 类

#### 初始化

```python
fetcher = TushareOfflineFetcher(token=None)
```

**参数:**
- `token`: Tushare token，可选。如果不提供则从环境变量或 session 中获取

#### 方法

##### fetch_symbol(symbol, days=365, force_update=False)

拉取单只股票数据

**参数:**
- `symbol`: 股票代码（如: "600519"）
- `days`: 拉取天数（默认: 365）
- `force_update`: 是否强制更新（默认: False）

**示例:**
```python
fetcher.fetch_symbol("600519", days=365)
```

##### fetch_symbols(symbols, days=365, force_update=False)

批量拉取股票数据

**参数:**
- `symbols`: 股票代码列表
- `days`: 拉取天数（默认: 365）
- `force_update`: 是否强制更新（默认: False）

**示例:**
```python
fetcher.fetch_symbols(["600519", "000001"], days=365)
```

##### fetch_all_stocks(days=365, force_update=False)

拉取所有A股股票数据

**参数:**
- `days`: 拉取天数（默认: 365）
- `force_update`: 是否强制更新（默认: False）

**示例:**
```python
fetcher.fetch_all_stocks(days=365)
```

##### get_data_summary()

获取本地数据摘要

**返回:**
```python
{
    'total_files': 100,      # 总文件数
    'total_records': 50000,  # 总记录数
    'symbols': [             # 每只股票的详细信息
        {
            'symbol': '600519',
            'records': 500,
            'min_date': '2020-01-01',
            'max_date': '2026-04-27'
        },
        ...
    ]
}
```

**示例:**
```python
summary = fetcher.get_data_summary()
print(f"共有 {summary['total_files']} 只股票的数据")
```

##### get_stock_list()

获取A股股票列表

**返回:**
```python
[
    {'code': '600519', 'name': '贵州茅台', 'ts_code': '600519.SH'},
    {'code': '000001', 'name': '平安银行', 'ts_code': '000001.SZ'},
    ...
]
```

**示例:**
```python
stocks = fetcher.get_stock_list()
print(f"共有 {len(stocks)} 只A股")
```

### TushareRateLimiter 类

#### 初始化

```python
limiter = TushareRateLimiter(max_calls_per_minute=50, max_calls_per_day=8000)
```

**参数:**
- `max_calls_per_minute`: 每分钟最大调用次数（默认: 50）
- `max_calls_per_day`: 每天最大调用次数（默认: 8000）

#### 方法

##### wait_for_rate_limit()

等待直到可以发起新的API调用

**示例:**
```python
limiter.wait_for_rate_limit()
# 现在可以安全地调用 API
```

---

## 数据格式

### 存储位置

- **Parquet 文件**: `data/local_parquet_hist/{股票代码}.parquet`
- **限流状态**: `data/tushare_rate_limit_state.json`

### 数据结构

#### 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| date | datetime | 交易日期 |
| open | float | 开盘价 |
| high | float | 最高价 |
| low | float | 最低价 |
| close | float | 收盘价 |
| volume | float | 成交量（股） |
| amount | float | 成交额（元） |
| pct_chg | float | 涨跌幅（%） |

#### 示例数据

```
         date     open     high      low    close   volume     amount  pct_chg
0  2026-04-20  1403.00  1420.00  1400.00  1415.00  3645139  5150000000     0.85
1  2026-04-21  1411.00  1425.00  1408.00  1420.00  2175427  3080000000     0.35
2  2026-04-22  1415.00  1430.00  1412.00  1425.00  2691593  3830000000     0.35
```

### 兼容性说明

模块兼容两种数据格式：

1. **新格式**（推荐）: date 作为普通列
2. **旧格式**: date 作为索引

模块会自动检测和转换，无需手动处理。

详细参见: [DATA_FORMAT_COMPATIBILITY.md](DATA_FORMAT_COMPATIBILITY.md)

---

## 最佳实践

### 1. 拉取策略

#### 关注列表模式（推荐）

只拉取您关注的股票，节省时间和API配额：

```bash
python scripts/tushare_offline_fetcher.py --symbols 600519 000001 300750 --days 365
```

#### 分批拉取

全市场股票数量大，建议分批进行：

```python
# 第一批
fetcher.fetch_symbols(symbols[:100], days=365)

# 第二批
fetcher.fetch_symbols(symbols[100:200], days=365)
```

#### 定期更新

每天收盘后更新一次即可：

```bash
# 添加到 crontab（Linux/Mac）
0 18 * * 1-5 cd /path/to/project && python scripts/tushare_offline_fetcher.py --symbols YOUR_SYMBOLS --days 1
```

### 2. 性能优化

#### 减少拉取天数

如果只需要近期数据，减少天数可以加快速度：

```bash
# 只拉取最近30天
python scripts/tushare_offline_fetcher.py --symbols 600519 --days 30
```

#### 利用增量更新

默认情况下，模块会检查已有数据，只拉取缺失部分：

```python
# 第一次：拉取全年数据
fetcher.fetch_symbol("600519", days=365)

# 第二天：只会拉取最新一天的数据
fetcher.fetch_symbol("600519", days=365)  # 很快完成
```

#### 并行处理（谨慎使用）

注意不要超过API限制：

```python
from concurrent.futures import ThreadPoolExecutor

def fetch_with_limit(symbol):
    fetcher.fetch_symbol(symbol, days=365)

# 最多同时2个线程（保守策略）
with ThreadPoolExecutor(max_workers=2) as executor:
    executor.map(fetch_with_limit, symbols)
```

### 3. 数据管理

#### 定期清理

删除不需要的股票数据：

```python
from pathlib import Path

data_dir = Path("data/local_parquet_hist")

# 删除特定股票
(data_dir / "000002.parquet").unlink()

# 或删除很久未更新的股票
import time
for file in data_dir.glob("*.parquet"):
    if time.time() - file.stat().st_mtime > 86400 * 30:  # 30天未更新
        file.unlink()
```

#### 备份数据

定期备份重要数据：

```bash
# 压缩备份
tar -czf parquet_backup_$(date +%Y%m%d).tar.gz data/local_parquet_hist/
```

#### 监控存储空间

```python
from pathlib import Path

data_dir = Path("data/local_parquet_hist")
total_size = sum(f.stat().st_size for f in data_dir.glob("*.parquet"))
print(f"总大小: {total_size / 1024 / 1024:.2f} MB")
```

### 4. 错误处理

#### 重试机制

```python
import time

def fetch_with_retry(symbol, max_retries=3):
    for attempt in range(max_retries):
        try:
            fetcher.fetch_symbol(symbol, days=365)
            return True
        except Exception as e:
            print(f"尝试 {attempt + 1} 失败: {e}")
            if attempt < max_retries - 1:
                time.sleep(5)  # 等待5秒后重试
    return False
```

#### 日志记录

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('tushare_fetch.log'),
        logging.StreamHandler()
    ]
)
```

---

## 故障排除

### 常见问题

#### Q1: 提示 "未找到 Tushare token"

**原因**: Token 未正确配置

**解决**:
```bash
# 检查环境变量
echo $TUSHARE_TOKEN  # Linux/Mac
echo %TUSHARE_TOKEN%  # Windows

# 重新设置
export TUSHARE_TOKEN="your_token"
```

#### Q2: API 调用失败

**可能原因**:
- Token 无效或过期
- 积分不足
- 网络问题

**解决**:
1. 检查 Token 是否正确
2. 登录 Tushare 网站查看积分
3. 检查网络连接
4. 稍后重试

#### Q3: 某些股票拉取失败

**可能原因**:
- 新股，历史数据少
- 停牌股票
- 代码错误

**解决**:
- 这是正常现象，程序会继续处理其他股票
- 检查股票代码是否正确
- 查看日志了解具体错误信息

#### Q4: 拉取速度很慢

**原因**: 遵守 API 限流规则

**说明**:
- 每分钟最多50次调用是正常的
- 全市场5000股需要约100分钟
- 建议只拉取关注的股票

#### Q5: 数据文件太大

**解决**:
1. 只拉取需要的股票
2. 减少拉取天数
3. 定期清理旧数据
4. 使用 Git LFS（如果需要提交到 Git）

#### Q6: Parquet 文件读取失败

**可能原因**:
- 文件损坏
- 版本不兼容

**解决**:
```python
# 尝试重新拉取
fetcher.fetch_symbol("600519", days=365, force_update=True)

# 或删除损坏的文件后重新拉取
from pathlib import Path
Path("data/local_parquet_hist/600519.parquet").unlink()
```

### 调试技巧

#### 启用详细日志

```python
import logging
logging.getLogger('scripts.tushare_offline_fetcher').setLevel(logging.DEBUG)
```

#### 检查限流状态

```python
import json
from pathlib import Path

state_file = Path("data/tushare_rate_limit_state.json")
if state_file.exists():
    with open(state_file) as f:
        state = json.load(f)
    print(f"今日调用次数: {len(state.get('day_calls', []))}")
    print(f"最近调用: {state.get('minute_calls', [])[-5:]}")
```

#### 验证数据完整性

```python
def verify_data(symbol):
    df = load_stock_data(symbol)
    
    if df.empty:
        print(f"✗ {symbol}: 无数据")
        return False
    
    # 检查必需字段
    required_cols = ['date', 'open', 'high', 'low', 'close', 'volume']
    missing = [col for col in required_cols if col not in df.columns]
    
    if missing:
        print(f"✗ {symbol}: 缺少字段 {missing}")
        return False
    
    # 检查缺失值
    null_counts = df[required_cols].isnull().sum()
    if null_counts.sum() > 0:
        print(f"⚠ {symbol}: 存在缺失值\n{null_counts}")
    
    print(f"✓ {symbol}: {len(df)} 条记录, {df['date'].min()} 至 {df['date'].max()}")
    return True

# 验证所有数据
from pathlib import Path
for file in Path("data/local_parquet_hist").glob("*.parquet"):
    verify_data(file.stem)
```

---

## 扩展开发

### 添加新的数据字段

修改 `fetch_single_stock` 方法：

```python
def fetch_single_stock(self, symbol: str, start_date: str, end_date: str):
    # ... 现有代码 ...
    
    # 获取更多字段
    df = self.pro.daily_basic(
        ts_code=ts_code,
        start_date=start_date,
        end_date=end_date,
        fields='trade_date,pe,pb,ps,total_mv'
    )
    
    # 合并数据
    # ... 合并逻辑 ...
    
    return df
```

### 支持其他数据类型

创建新的拉取器类：

```python
class IndexDataFetcher(TushareOfflineFetcher):
    """指数数据拉取器"""
    
    def fetch_index(self, index_code: str, days: int = 365):
        """拉取指数数据"""
        # 实现指数数据拉取逻辑
        pass
```

### 异步并发

使用 asyncio 提高并发效率：

```python
import asyncio
import aiohttp

async def fetch_stock_async(session, symbol):
    async with session.get(url) as response:
        return await response.json()

async def batch_fetch_async(symbols):
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_stock_async(session, s) for s in symbols]
        results = await asyncio.gather(*tasks)
    return results
```

### 数据质量检查

添加数据验证逻辑：

```python
def validate_data(df: pd.DataFrame) -> bool:
    """验证数据质量"""
    checks = [
        len(df) > 0,  # 非空
        df['close'].notna().all(),  # 收盘价无缺失
        (df['high'] >= df['low']).all(),  # 最高价 >= 最低价
        (df['volume'] >= 0).all(),  # 成交量非负
    ]
    return all(checks)
```

### Web 界面

使用 Streamlit 创建可视化界面：

```python
import streamlit as st
from scripts.tushare_offline_fetcher import TushareOfflineFetcher

st.title("Tushare 离线数据管理")

# 输入股票代码
symbols = st.text_input("股票代码（逗号分隔）", "600519,000001")
days = st.slider("拉取天数", 30, 365, 365)

if st.button("开始拉取"):
    fetcher = TushareOfflineFetcher()
    symbol_list = [s.strip() for s in symbols.split(",")]
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, symbol in enumerate(symbol_list):
        status_text.text(f"正在拉取 {symbol}...")
        fetcher.fetch_symbol(symbol, days=days)
        progress_bar.progress((i + 1) / len(symbol_list))
    
    status_text.text("完成！")
    st.success(f"成功拉取 {len(symbol_list)} 只股票的数据")
```

---

## 相关资源

- [Tushare 官方文档](https://tushare.pro/document/1)
- [Pandas 文档](https://pandas.pydata.org/docs/)
- [PyArrow 文档](https://arrow.apache.org/docs/python/)
- [GitHub Actions 文档](https://docs.github.com/en/actions)

## 项目文件

- `scripts/tushare_offline_fetcher.py` - 核心模块
- `scripts/tushare_offline_usage_example.py` - 使用示例
- `tests/test_tushare_offline_fetcher.py` - 测试套件
- `verify_tushare_offline.py` - 验证工具
- `docs/TUSHARE_OFFLINE_FETCHER_GUIDE.md` - 详细指南
- `docs/DATA_FORMAT_COMPATIBILITY.md` - 数据格式兼容性说明
- `.github/workflows/tushare_offline_data.yml` - GitHub Actions 配置

---

**最后更新**: 2026-04-27  
**版本**: 1.0.0