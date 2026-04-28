# -*- coding: utf-8 -*-
"""
Tushare 离线数据使用示例

展示如何在现有项目中集成和使用 Tushare 离线数据
"""

import pandas as pd
from pathlib import Path
from datetime import date, timedelta


def load_offline_stock_data(symbol: str, start_date: date = None, end_date: date = None) -> pd.DataFrame:
    """
    从本地 Parquet 文件加载股票历史数据
    
    Args:
        symbol: 股票代码 (如: 600519)
        start_date: 开始日期（可选）
        end_date: 结束日期（可选）
        
    Returns:
        DataFrame with columns: date, open, high, low, close, volume, amount, pct_chg
    """
    file_path = Path("data/local_parquet_hist") / f"{symbol}.parquet"
    
    if not file_path.exists():
        print(f"[OfflineData] 未找到 {symbol} 的本地数据")
        return pd.DataFrame()
    
    try:
        df = pd.read_parquet(file_path)
        
        # 确保日期列是 datetime 类型
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
        elif isinstance(df.index, pd.DatetimeIndex):
            df = df.reset_index()
            df.rename(columns={'index': 'date'}, inplace=True)
        
        # 按日期排序
        df = df.sort_values('date').reset_index(drop=True)
        
        # 如果指定了日期范围，进行过滤
        if start_date:
            df = df[df['date'] >= pd.Timestamp(start_date)]
        if end_date:
            df = df[df['date'] <= pd.Timestamp(end_date)]
        
        if df.empty:
            print(f"[OfflineData] {symbol} 在指定日期范围内无数据")
            return pd.DataFrame()
        
        print(f"[OfflineData] 加载 {symbol}: {len(df)} 条记录")
        return df
        
    except Exception as e:
        print(f"[OfflineData] 读取 {symbol} 数据失败: {e}")
        return pd.DataFrame()


def calculate_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    计算技术指标
    
    Args:
        df: 股票数据 DataFrame
        
    Returns:
        添加了技术指标的 DataFrame
    """
    if df.empty:
        return df
    
    df = df.copy()
    
    # 移动平均线
    df['ma5'] = df['close'].rolling(window=5).mean()
    df['ma10'] = df['close'].rolling(window=10).mean()
    df['ma20'] = df['close'].rolling(window=20).mean()
    df['ma60'] = df['close'].rolling(window=60).mean()
    
    # RSI (相对强弱指标)
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # MACD
    exp1 = df['close'].ewm(span=12, adjust=False).mean()
    exp2 = df['close'].ewm(span=26, adjust=False).mean()
    df['macd'] = exp1 - exp2
    df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
    df['macd_hist'] = df['macd'] - df['macd_signal']
    
    # 布林带
    df['bb_middle'] = df['close'].rolling(window=20).mean()
    bb_std = df['close'].rolling(window=20).std()
    df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
    df['bb_lower'] = df['bb_middle'] - (bb_std * 2)
    
    # 成交量移动平均
    df['volume_ma5'] = df['volume'].rolling(window=5).mean()
    df['volume_ma20'] = df['volume'].rolling(window=20).mean()
    
    return df


def analyze_stock(symbol: str, days: int = 60):
    """
    分析单只股票
    
    Args:
        symbol: 股票代码
        days: 分析天数
    """
    print(f"\n{'='*60}")
    print(f"分析股票: {symbol}")
    print(f"{'='*60}")
    
    # 加载数据
    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    
    df = load_offline_stock_data(symbol, start_date, end_date)
    
    if df.empty:
        print(f"无法获取 {symbol} 的数据")
        return
    
    # 计算技术指标
    df = calculate_technical_indicators(df)
    
    # 显示最新数据
    latest = df.iloc[-1]
    print(f"\n最新数据 ({latest['date'].date()}):")
    print(f"  收盘价: {latest['close']:.2f}")
    print(f"  涨跌幅: {latest['pct_chg']:.2f}%")
    print(f"  成交量: {latest['volume']:,.0f}")
    print(f"  成交额: {latest['amount']:,.0f}")
    
    # 显示技术指标
    print(f"\n技术指标:")
    print(f"  MA5:  {latest['ma5']:.2f}")
    print(f"  MA20: {latest['ma20']:.2f}")
    print(f"  MA60: {latest['ma60']:.2f}")
    print(f"  RSI:  {latest['rsi']:.2f}" if pd.notna(latest['rsi']) else "  RSI:  N/A")
    print(f"  MACD: {latest['macd']:.3f}" if pd.notna(latest['macd']) else "  MACD: N/A")
    
    # 简单趋势判断
    if pd.notna(latest['ma5']) and pd.notna(latest['ma20']):
        if latest['close'] > latest['ma5'] > latest['ma20']:
            trend = "上升趋势 ⬆️"
        elif latest['close'] < latest['ma5'] < latest['ma20']:
            trend = "下降趋势 ⬇️"
        else:
            trend = "震荡趋势 ➡️"
        print(f"\n趋势判断: {trend}")
    
    # 显示最近5天数据
    print(f"\n最近5天数据:")
    recent = df.tail(5)[['date', 'open', 'high', 'low', 'close', 'volume', 'pct_chg']]
    recent['date'] = recent['date'].dt.strftime('%Y-%m-%d')
    print(recent.to_string(index=False))
    
    return df


def compare_stocks(symbols: list):
    """
    对比多只股票
    
    Args:
        symbols: 股票代码列表
    """
    print(f"\n{'='*60}")
    print(f"股票对比分析")
    print(f"{'='*60}")
    
    results = []
    
    for symbol in symbols:
        df = load_offline_stock_data(symbol)
        
        if df.empty:
            continue
        
        # 计算基本统计
        latest = df.iloc[-1]
        month_ago = df.iloc[-min(20, len(df)-1)] if len(df) > 1 else latest
        
        monthly_return = ((latest['close'] - month_ago['close']) / month_ago['close'] * 100) if month_ago['close'] != 0 else 0
        
        results.append({
            'symbol': symbol,
            'price': latest['close'],
            'monthly_return': monthly_return,
            'avg_volume': df['volume'].tail(20).mean(),
            'volatility': df['pct_chg'].tail(20).std()
        })
    
    if results:
        df_compare = pd.DataFrame(results)
        print(f"\n对比结果:")
        print(df_compare.to_string(index=False))
        
        # 找出表现最好的股票
        best = df_compare.loc[df_compare['monthly_return'].idxmax()]
        print(f"\n本月表现最佳: {best['symbol']} ({best['monthly_return']:.2f}%)")


def batch_analysis():
    """批量分析示例"""
    print("\n" + "="*60)
    print("批量分析示例")
    print("="*60)
    
    # 定义关注的股票列表
    watchlist = [
        "600519",  # 贵州茅台
        "000001",  # 平安银行
        "300750",  # 宁德时代
        "000858",  # 五粮液
        "600036",  # 招商银行
    ]
    
    # 分析每只股票
    for symbol in watchlist:
        try:
            analyze_stock(symbol, days=60)
        except Exception as e:
            print(f"分析 {symbol} 时出错: {e}")
    
    # 对比所有股票
    compare_stocks(watchlist)


def export_to_csv(symbol: str, output_dir: str = "output/offline_data"):
    """
    将离线数据导出为 CSV 格式
    
    Args:
        symbol: 股票代码
        output_dir: 输出目录
    """
    df = load_offline_stock_data(symbol)
    
    if df.empty:
        print(f"没有 {symbol} 的数据可导出")
        return
    
    # 创建输出目录
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # 导出为 CSV
    output_file = Path(output_dir) / f"{symbol}_offline.csv"
    df.to_csv(output_file, index=False, encoding='utf-8-sig')
    
    print(f"✓ 数据已导出到: {output_file}")
    print(f"  记录数: {len(df)}")


def main():
    """主函数 - 演示各种用法"""
    print("\n" + "="*60)
    print("Tushare 离线数据使用示例")
    print("="*60)
    
    # 示例1: 分析单只股票
    print("\n[示例1] 分析单只股票")
    analyze_stock("600519", days=60)
    
    # 示例2: 批量分析
    print("\n[示例2] 批量分析")
    batch_analysis()
    
    # 示例3: 导出数据
    print("\n[示例3] 导出数据")
    export_to_csv("600519")
    
    print("\n" + "="*60)
    print("示例运行完成")
    print("="*60)


if __name__ == "__main__":
    main()