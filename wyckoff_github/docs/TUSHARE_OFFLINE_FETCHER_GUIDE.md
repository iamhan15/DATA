# Tushare 离线数据拉取模块使用指南

## 功能概述

本模块用于按照 Tushare API 限流规则（每分钟50次，每天8000次）拉取股票非复权日线行情数据，并保存到本地 Parquet 格式作为离线数据源。

## 主要特性

1. **智能限流**: 自动遵守 Tushare API 调用限制（每分钟50次，每天8000次）
2. **增量更新**: 支持检查已有数据，只拉取缺失或过期的数据
3. **断点续传**: 保存调用状态，中断后可继续执行
4. **高效存储**: 使用 Parquet 格式存储，读取速度快，占用空间小
5. **批量处理**: 支持单只股票、指定股票列表或全市场股票拉取

## 安装依赖

确保已安装 tushare：

```bash
pip install tushare pandas pyarrow
```

## 配置 Tushare Token

### 方法1: 环境变量
```bash
export TUSHARE_TOKEN="your_tushare_token_here"
```

### 方法2: 在 Streamlit 应用中配置
在 Settings 页面中配置 Tushare Token

## 使用方法

### 1. 命令行使用

#### 拉取指定股票
```bash
python scripts/tushare_offline_fetcher.py --symbols 600519 000001 300750 --days 365
```

#### 拉取所有A股股票
```bash
python scripts/tushare_offline_fetcher.py --all --days 365
```

#### 强制更新（忽略已有数据）
```bash
python scripts/tushare_offline_fetcher.py --symbols 600519 --days 365 --force
```

#### 查看本地数据摘要
```bash
python scripts/tushare_offline_fetcher.py --summary
```

### 2. Python 代码使用

#### 基本用法

```python
from scripts.tushare_offline_fetcher import TushareOfflineFetcher

# 创建拉取器实例
fetcher = TushareOfflineFetcher()

# 拉取指定股票最近一年的数据
symbols = ["600519", "000001", "300750"]
fetcher.fetch_symbols(symbols, days=365)

# 或者拉取所有股票
# fetcher.fetch_all_stocks(days=365)
```

#### 高级用法

```python
from scripts.tushare_offline_fetcher import TushareOfflineFetcher

# 创建拉取器
fetcher = TushareOfflineFetcher()

# 拉取单只股票
fetcher.fetch_symbol("600519", days=365, force_update=False)

# 获取本地数据摘要
summary = fetcher.get_data_summary()
print(f"总文件数: {summary['total_files']}")
print(f"总记录数: {summary['total_records']}")

# 查看每只股票的详细信息
for stock_info in summary['symbols']:
    print(f"{stock_info['symbol']}: {stock_info['records']} 条记录, "
          f"{stock_info['min_date']} 至 {stock_info['max_date']}")
```

#### 自定义限流参数

```python
from scripts.tushare_offline_fetcher import TushareOfflineFetcher, TushareRateLimiter

# 自定义限流器（如果需要调整限制）
rate_limiter = TushareRateLimiter(
    max_calls_per_minute=40,  # 更保守的每分钟限制
    max_calls_per_day=7000     # 更保守的每日限制
)

# 注意：目前 TushareOfflineFetcher 内部创建自己的限流器
# 如需自定义，可以修改源码
```

## 数据存储

### 存储位置
- Parquet 文件: `data/local_parquet_hist/`
- 限流状态: `data/tushare_rate_limit_state.json`

### 文件格式
每个股票一个 Parquet 文件，文件名格式: `{股票代码}.parquet`

### 数据列
- `date`: 交易日期
- `open`: 开盘价
- `high`: 最高价
- `low`: 最低价
- `close`: 收盘价
- `volume`: 成交量（股）
- `amount`: 成交额（元）
- `pct_chg`: 涨跌幅（%）

## 读取本地数据

```python
import pandas as pd
from pathlib import Path

# 读取单只股票数据
def load_stock_data(symbol: str) -> pd.DataFrame:
    file_path = Path("data/local_parquet_hist") / f"{symbol}.parquet"
    if file_path.exists():
        df = pd.read_parquet(file_path)
        df['date'] = pd.to_datetime(df['date'])
        return df.sort_values('date').reset_index(drop=True)
    return None

# 使用示例
df = load_stock_data("600519")
if df is not None:
    print(df.head())
    print(f"数据范围: {df['date'].min()} 至 {df['date'].max()}")
```

## 注意事项

1. **API 限制**: 
   - 每分钟最多调用50次
   - 每天最多调用8000次
   - 全市场约5000只股票，全部拉取需要约100分钟（不考虑其他限制）

2. **积分要求**:
   - 基础行情接口通常需要一定积分
   - 请确保您的 Tushare 账户有足够积分

3. **网络稳定性**:
   - 建议在网络稳定的环境下运行
   - 大规模拉取建议在夜间或网络空闲时段进行

4. **存储空间**:
   - 全市场数据大约需要几GB存储空间
   - Parquet 格式压缩率高，实际占用空间较小

5. **增量更新**:
   - 默认情况下，如果本地数据已是最新，会跳过该股票
   - 使用 `--force` 参数可强制重新拉取

## 性能优化建议

1. **分批拉取**: 不要一次性拉取所有股票，可以分批进行
2. **定期更新**: 每天收盘后更新一次即可，无需频繁拉取
3. **监控用量**: 定期检查 `tushare_rate_limit_state.json` 了解使用情况
4. **错误处理**: 程序会自动处理单个股票的失败，继续处理下一个

## 故障排除

### 问题1: Token 无效
```
错误: 未找到 Tushare token
解决: 设置 TUSHARE_TOKEN 环境变量或在 Streamlit 中配置
```

### 问题2: API 调用失败
```
错误: 获取股票列表失败 / 拉取数据失败
解决: 检查网络连接，确认 Tushare 账户积分足够
```

### 问题3: 数据为空
```
警告: XXX 无数据返回
解决: 可能是新股或停牌股票，属于正常现象
```

### 问题4: 限流等待时间长
```
信息: 达到每分钟限制，等待 XX 秒
解决: 这是正常行为，程序会自动等待后继续
```

## 与其他模块集成

本模块保存的数据可以被以下模块直接使用：

1. **core/local_cache.py**: 已有的本地缓存模块可以直接读取 Parquet 文件
2. **integrations/data_source.py**: 数据源模块可以优先使用本地数据
3. **app/single_stock_logic.py**: 个股分析逻辑可以使用本地数据

## 示例工作流

```python
from scripts.tushare_offline_fetcher import TushareOfflineFetcher
import pandas as pd
from pathlib import Path

# 1. 初始化拉取器
fetcher = TushareOfflineFetcher()

# 2. 拉取关注的股票列表
watchlist = ["600519", "000001", "300750", "000858"]
fetcher.fetch_symbols(watchlist, days=365)

# 3. 读取数据进行分析和回测
def analyze_stock(symbol: str):
    file_path = Path("data/local_parquet_hist") / f"{symbol}.parquet"
    if file_path.exists():
        df = pd.read_parquet(file_path)
        df['date'] = pd.to_datetime(df['date'])
        
        # 计算一些指标
        df['ma20'] = df['close'].rolling(window=20).mean()
        df['ma60'] = df['close'].rolling(window=60).mean()
        
        latest = df.iloc[-1]
        print(f"\n{symbol} 最新数据:")
        print(f"日期: {latest['date'].date()}")
        print(f"收盘价: {latest['close']:.2f}")
        print(f"MA20: {latest['ma20']:.2f}")
        print(f"MA60: {latest['ma60']:.2f}")
        
        return df
    return None

# 4. 分析每只股票
for symbol in watchlist:
    analyze_stock(symbol)
```

## 扩展开发

如需扩展功能，可以参考以下方向：

1. **添加更多数据字段**: 修改 `fetch_single_stock` 方法获取更多字段
2. **支持其他数据类型**: 如指数、基金等
3. **数据验证**: 添加数据质量检查和清洗逻辑
4. **异步处理**: 使用 asyncio 提高并发效率
5. **进度可视化**: 添加进度条或 Web 界面

## 技术支持

如有问题，请查看日志输出或联系项目维护者。