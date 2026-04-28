# 数据格式兼容性说明

## 现有数据格式

项目中已存在的 Parquet 文件使用以下格式：

### 结构
- **索引**: date (DatetimeIndex)
- **列**: open, high, low, close, amount, volume

### 示例
```python
import pandas as pd
from pathlib import Path

file_path = Path("data/local_parquet_hist/600519.parquet")
df = pd.read_parquet(file_path)

print(df.head())
#                    open     high      low    close      amount   volume
# date                                                                    
# 2020-01-02  1000.000000  1010.00  995.000  1005.00  1000000.00  1000000
# 2020-01-03  1005.000000  1015.00  1000.00  1010.00  1100000.00  1100000
```

## 新模块数据格式

`tushare_offline_fetcher.py` 模块生成的数据格式：

### 结构
- **列**: date, open, high, low, close, volume, amount, pct_chg
- **日期**: 作为普通列（非索引）

### 示例
```python
import pandas as pd
from pathlib import Path

file_path = Path("data/local_parquet_hist/600519.parquet")
df = pd.read_parquet(file_path)

print(df.head())
#         date     open     high      low    close   volume     amount  pct_chg
# 0 2020-01-02  1000.00  1010.00  995.000  1005.00  1000000  1000000.00     1.00
# 1 2020-01-03  1005.00  1015.00  1000.00  1010.00  1100000  1100000.00     0.50
```

## 兼容性处理

### 方法1: 统一读取函数

```python
def load_stock_data_unified(symbol: str) -> pd.DataFrame:
    """
    统一加载股票数据，兼容两种格式
    """
    from pathlib import Path
    
    file_path = Path("data/local_parquet_hist") / f"{symbol}.parquet"
    
    if not file_path.exists():
        return pd.DataFrame()
    
    df = pd.read_parquet(file_path)
    
    # 检查日期是否在索引中
    if isinstance(df.index, pd.DatetimeIndex) and 'date' not in df.columns:
        # 旧格式：日期在索引中
        df = df.reset_index()
        df.rename(columns={'index': 'date'}, inplace=True)
    
    # 确保日期列是 datetime 类型
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'])
    
    # 按日期排序
    df = df.sort_values('date').reset_index(drop=True)
    
    return df
```

### 方法2: 转换现有数据

如果需要将现有数据转换为新格式：

```python
def convert_existing_data():
    """
    将现有数据转换为新格式
    """
    from pathlib import Path
    import pandas as pd
    
    data_dir = Path("data/local_parquet_hist")
    
    for file_path in data_dir.glob("*.parquet"):
        try:
            df = pd.read_parquet(file_path)
            
            # 如果日期在索引中，转换为列
            if isinstance(df.index, pd.DatetimeIndex) and 'date' not in df.columns:
                df = df.reset_index()
                df.rename(columns={'index': 'date'}, inplace=True)
                
                # 保存为新格式
                df.to_parquet(file_path, index=False)
                print(f"✓ 转换完成: {file_path.name}")
        
        except Exception as e:
            print(f"✗ 转换失败 {file_path.name}: {e}")
```

### 方法3: 在 tushare_offline_fetcher 中兼容

修改 `TushareOfflineFetcher.save_stock_data` 方法以兼容现有格式：

```python
def save_stock_data(self, symbol: str, df: pd.DataFrame):
    """保存股票数据到本地 Parquet 文件（兼容现有格式）"""
    if df is None or df.empty:
        return
    
    file_path = self.data_dir / f"{symbol}.parquet"
    
    try:
        # 如果文件已存在，合并新旧数据
        if file_path.exists():
            existing_df = pd.read_parquet(file_path)
            
            # 兼容处理：确保日期格式一致
            if isinstance(existing_df.index, pd.DatetimeIndex) and 'date' not in existing_df.columns:
                existing_df = existing_df.reset_index()
                existing_df.rename(columns={'index': 'date'}, inplace=True)
            
            combined_df = pd.concat([existing_df, df])
            # 去重并按日期排序
            combined_df = combined_df.drop_duplicates(subset=['date'], keep='last')
            combined_df = combined_df.sort_values('date').reset_index(drop=True)
            df = combined_df
        
        # 保存为 Parquet 格式（date 作为列）
        df.to_parquet(file_path, index=False)
        
    except Exception as e:
        logger.error(f"保存 {symbol} 数据失败: {e}")
```

## 推荐做法

### 对于新项目
直接使用新模块的格式（date 作为列），这样更灵活：
- 易于筛选和查询
- 便于导出为 CSV
- 与其他数据处理工具兼容性好

### 对于现有项目
1. **保持兼容**: 使用统一读取函数处理两种格式
2. **逐步迁移**: 在更新数据时自动转换为新格式
3. **避免破坏**: 不要强制转换所有现有数据，按需处理

## 字段说明

### 共同字段
- `open`: 开盘价
- `high`: 最高价
- `low`: 最低价
- `close`: 收盘价
- `volume`: 成交量（股）
- `amount`: 成交额（元）

### 新模块额外字段
- `date`: 交易日期（作为列）
- `pct_chg`: 涨跌幅（%）

## 注意事项

1. **日期格式**: 
   - 确保日期是 datetime 类型
   - 避免字符串和 datetime 混用

2. **重复数据**:
   - 合并时注意去重
   - 保留最新的数据（keep='last'）

3. **缺失值**:
   - 检查关键字段是否有缺失
   - 适当处理 NaN 值

4. **数据类型**:
   - 价格字段应为 float
   - 成交量应为 int 或 float
   - 日期应为 datetime

## 示例代码

### 读取并分析股票数据

```python
import pandas as pd
from pathlib import Path

def analyze_stock(symbol: str):
    """分析股票数据（兼容两种格式）"""
    file_path = Path("data/local_parquet_hist") / f"{symbol}.parquet"
    
    if not file_path.exists():
        print(f"未找到 {symbol} 的数据")
        return None
    
    # 读取数据
    df = pd.read_parquet(file_path)
    
    # 兼容处理
    if isinstance(df.index, pd.DatetimeIndex) and 'date' not in df.columns:
        df = df.reset_index()
        df.rename(columns={'index': 'date'}, inplace=True)
    
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'])
    
    # 计算基本统计
    print(f"\n{symbol} 数据统计:")
    print(f"记录数: {len(df)}")
    print(f"日期范围: {df['date'].min()} 至 {df['date'].max()}")
    print(f"最新收盘价: {df['close'].iloc[-1]:.2f}")
    print(f"平均成交量: {df['volume'].mean():,.0f}")
    
    return df

# 使用示例
df = analyze_stock("600519")
```

## 总结

- ✅ 两种格式都可以正常工作
- ✅ 建议在新项目中使用 date 作为列的格式
- ✅ 现有数据可以保持不变，通过兼容函数读取
- ✅ 逐步迁移是最佳策略，避免一次性大规模改动

---

**更新日期**: 2026-04-27