"""
K线可视化模块
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import logging

logger = logging.getLogger('Visualizer')

class KLineVisualizer:
    """K线可视化器"""
    
    def __init__(self, style_config: Dict = None):
        self.style = style_config or {
            'figure_size': (14, 10),
            'dpi': 150,
            'up_color': '#ef4444',      # A股红涨
            'down_color': '#22c55e',    # A股绿跌
            'volume_color': '#3b82f6',
            'ma20_color': '#f59e0b',
            'ma60_color': '#8b5cf6',
            'support_color': '#10b981',
            'resistance_color': '#ef4444',
            'signal_colors': {
                'SPRING': '#10b981',     # 绿色
                'SOS': '#3b82f6',        # 蓝色
                'BC': '#ef4444',         # 红色
                'SC': '#f59e0b',         # 橙色
                'TEST': '#8b5cf6'        # 紫色
            }
        }
        
        # 设置中文字体
        plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False
    
    def plot_stock(self, symbol: str, name: str, df: pd.DataFrame, 
                   analysis=None, save_path: Optional[Path] = None) -> Path:
        """
        绘制单只股票K线图（带威科夫标记）
        """
        if df.empty or len(df) < 20:
            logger.error(f"数据不足: {symbol}")
            return None
        
        # 创建图形
        fig, axes = plt.subplots(3, 1, figsize=self.style['figure_size'], 
                                gridspec_kw={'height_ratios': [3, 1, 1]}, 
                                dpi=self.style['dpi'])
        
        # 1. 主图：K线 + 均线 + 支撑阻力
        ax1 = axes[0]
        self._plot_candlestick(ax1, df)
        self._plot_ma_lines(ax1, df)
        self._plot_support_resistance(ax1, df, analysis)
        self._plot_signals(ax1, df, analysis)
        
        # 设置标题
        title = f"{symbol} {name} - 威科夫分析"
        if analysis:
            title += f" | 阶段: {analysis.phase.value} | 评分: {analysis.composite_score}"
        ax1.set_title(title, fontsize=14, fontweight='bold', pad=20)
        ax1.set_ylabel('价格', fontsize=10)
        ax1.legend(loc='upper left', fontsize=8)
        ax1.grid(True, alpha=0.3)
        
        # 2. 成交量
        ax2 = axes[1]
        self._plot_volume(ax2, df)
        ax2.set_ylabel('成交量', fontsize=10)
        ax2.grid(True, alpha=0.3)
        
        # 3. 威科夫评分/信号时间线
        ax3 = axes[2]
        self._plot_wyckoff_timeline(ax3, df, analysis)
        ax3.set_ylabel('威科夫信号', fontsize=10)
        ax3.set_xlabel('日期', fontsize=10)
        
        plt.tight_layout()
        
        # 保存
        if save_path is None:
            save_path = Path(f"./charts/{symbol}_{datetime.now().strftime('%Y%m%d')}.png")
        
        save_path.parent.mkdir(exist_ok=True)
        plt.savefig(save_path, dpi=self.style['dpi'], bbox_inches='tight')
        plt.close()
        
        logger.info(f"图表已保存: {save_path}")
        return save_path
    
    def _plot_candlestick(self, ax, df: pd.DataFrame):
        """绘制K线"""
        width = 0.6
        width2 = 0.05
        
        for i, (date, row) in enumerate(df.iterrows()):
            idx = i
            
            if row['close'] >= row['open']:
                color = self.style['up_color']
                height = row['close'] - row['open']
                bottom = row['open']
            else:
                color = self.style['down_color']
                height = row['open'] - row['close']
                bottom = row['close']
            
            # 实体
            ax.bar(idx, height, width, bottom=bottom, color=color, edgecolor=color)
            
            # 影线
            ax.plot([idx, idx], [row['low'], row['high']], color=color, linewidth=0.8)
        
        # 设置x轴标签
        n = len(df)
        step = max(n // 10, 1)
        ax.set_xticks(range(0, n, step))
        ax.set_xticklabels([df.index[i].strftime('%m-%d') for i in range(0, n, step)], 
                          rotation=45, ha='right', fontsize=8)
    
    def _plot_ma_lines(self, ax, df: pd.DataFrame):
        """绘制均线"""
        if len(df) >= 20:
            ma20 = df['close'].rolling(20).mean()
            ax.plot(range(len(df)), ma20, color=self.style['ma20_color'], 
                   linewidth=1.5, label='MA20', alpha=0.8)
        
        if len(df) >= 60:
            ma60 = df['close'].rolling(60).mean()
            ax.plot(range(len(df)), ma60, color=self.style['ma60_color'], 
                   linewidth=1.5, label='MA60', alpha=0.8)
    
    def _plot_support_resistance(self, ax, df: pd.DataFrame, analysis):
        """绘制支撑阻力线"""
        if analysis is None:
            return
        
        tech = analysis.technicals
        n = len(df)
        
        # 支撑线
        support = tech.get('support', 0)
        if support > 0:
            ax.axhline(y=support, color=self.style['support_color'], 
                      linestyle='--', linewidth=1.5, alpha=0.7, label=f'支撑: {support:.2f}')
        
        # 阻力线
        resistance = tech.get('resistance', 0)
        if resistance > 0:
            ax.axhline(y=resistance, color=self.style['resistance_color'], 
                      linestyle='--', linewidth=1.5, alpha=0.7, label=f'阻力: {resistance:.2f}')
        
        # 当前价格标注
        current = tech.get('current_price', 0)
        if current > 0:
            ax.axhline(y=current, color='gray', linestyle=':', linewidth=1, alpha=0.5)
    
    def _plot_signals(self, ax, df: pd.DataFrame, analysis):
        """绘制威科夫信号标记"""
        if analysis is None or not analysis.signals:
            return
        
        for signal in analysis.signals:
            try:
                signal_date = pd.to_datetime(signal.date)
                
                # 找到对应的x坐标
                if signal_date in df.index:
                    idx = df.index.get_loc(signal_date)
                else:
                    # 找最近的日期
                    closest_idx = df.index.get_indexer([signal_date], method='nearest')[0]
                    idx = closest_idx if closest_idx >= 0 else None
                
                if idx is not None and 0 <= idx < len(df):
                    color = self.style['signal_colors'].get(signal.event.name, 'gray')
                    
                    # 根据信号类型绘制不同标记
                    if signal.event.name == 'SPRING':
                        # 弹簧：向下箭头
                        ax.annotate('⬇', xy=(idx, df.iloc[idx]['low']), 
                                   fontsize=20, color=color, ha='center',
                                   xytext=(idx, df.iloc[idx]['low'] * 0.98),
                                   arrowprops=dict(arrowstyle='->', color=color))
                    elif signal.event.name == 'SOS':
                        # 强势：向上箭头
                        ax.annotate('⬆', xy=(idx, df.iloc[idx]['high']), 
                                   fontsize=20, color=color, ha='center',
                                   xytext=(idx, df.iloc[idx]['high'] * 1.02),
                                   arrowprops=dict(arrowstyle='->', color=color))
                    else:
                        # 其他：圆圈
                        ax.scatter(idx, df.iloc[idx]['close'], s=200, 
                                  c=color, marker='o', edgecolors='white', 
                                  linewidths=2, zorder=5, alpha=0.8)
                    
                    # 添加文字标签
                    ax.annotate(signal.event.value, 
                               xy=(idx, df.iloc[idx]['close']),
                               xytext=(10, 10), textcoords='offset points',
                               fontsize=8, color=color, fontweight='bold',
                               bbox=dict(boxstyle='round,pad=0.3', 
                                        facecolor='white', edgecolor=color, alpha=0.8))
                    
            except Exception as e:
                logger.debug(f"绘制信号失败: {e}")
    
    def _plot_volume(self, ax, df: pd.DataFrame):
        """绘制成交量"""
        colors = [self.style['up_color'] if c >= o else self.style['down_color'] 
                  for c, o in zip(df['close'], df['open'])]
        
        ax.bar(range(len(df)), df['volume'], color=colors, alpha=0.7, width=0.6)
        ax.set_ylim(0, df['volume'].max() * 1.2)
        
        # 成交量均线
        if len(df) >= 20:
            vol_ma20 = df['volume'].rolling(20).mean()
            ax.plot(range(len(df)), vol_ma20, color=self.style['volume_color'], 
                   linewidth=1.5, label='VOL_MA20', alpha=0.8)
            ax.legend(loc='upper left', fontsize=8)
    
    def _plot_wyckoff_timeline(self, ax, df: pd.DataFrame, analysis):
        """绘制威科夫信号时间线"""
        if analysis is None:
            ax.text(0.5, 0.5, '无威科夫分析数据', ha='center', va='center', 
                   transform=ax.transAxes, fontsize=12, color='gray')
            ax.set_xticks([])
            ax.set_yticks([])
            return
        
        # 绘制评分变化（简化：用柱状图表示信号强度）
        signal_dates = []
        signal_scores = []
        signal_colors = []
        
        # 基础评分线
        base_score = analysis.composite_score
        ax.axhline(y=base_score, color='gray', linestyle='--', alpha=0.5, label=f'当前评分: {base_score}')
        
        # 标记信号点
        for i, signal in enumerate(analysis.signals[:5]):  # 最近5个信号
            try:
                signal_date = pd.to_datetime(signal.date)
                if signal_date in df.index:
                    idx = df.index.get_loc(signal_date)
                    
                    # 信号强度（基于置信度）
                    strength = signal.confidence * 100
                    color = self.style['signal_colors'].get(signal.event.name, 'gray')
                    
                    ax.scatter(idx, strength, s=300, c=color, marker='*', 
                              edgecolors='white', linewidths=2, zorder=5)
                    
                    ax.annotate(f"{signal.event.value}\n{signal.date[5:]}", 
                               xy=(idx, strength), xytext=(0, 10), 
                               textcoords='offset points', ha='center',
                               fontsize=7, color=color, fontweight='bold')
                    
            except Exception as e:
                continue
        
        ax.set_ylim(0, 100)
        ax.set_yticks([0, 25, 50, 75, 100])
        ax.set_yticklabels(['0', '25', '50', '75', '100'])
        ax.legend(loc='upper left', fontsize=8)
        ax.grid(True, alpha=0.3)
    
    def batch_plot_results(self, results: List, data_manager, 
                          max_plots: int = 20, output_dir: Path = Path("./charts")):
        """
        批量绘制高评分股票
        """
        output_dir.mkdir(exist_ok=True)
        plotted = 0
        
        for result in results[:max_plots]:
            try:
                symbol = result.symbol if hasattr(result, 'symbol') else result['代码']
                name = result.name if hasattr(result, 'name') else result['名称']
                
                df = data_manager.get_daily_data(symbol, days=120)
                if df.empty:
                    continue
                
                # 如果有完整分析对象，传递过去
                analysis = result if hasattr(result, 'technicals') else None
                
                save_path = output_dir / f"{symbol}_{name}_{datetime.now().strftime('%Y%m%d')}.png"
                self.plot_stock(symbol, name, df, analysis, save_path)
                
                plotted += 1
                
            except Exception as e:
                logger.error(f"绘制 {symbol} 失败: {e}")
                continue
        
        logger.info(f"批量绘图完成: {plotted}/{min(len(results), max_plots)} 只")
        return plotted
