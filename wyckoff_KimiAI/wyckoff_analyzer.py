"""
威科夫分析引擎模块
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum
from datetime import datetime
import logging

logger = logging.getLogger('WyckoffAnalyzer')

class WyckoffPhase(Enum):
    ACCUMULATION = "吸筹阶段"
    MARKUP = "上涨阶段"
    DISTRIBUTION = "派发阶段"
    MARKDOWN = "下跌阶段"
    UNKNOWN = "未知"

class WyckoffEvent(Enum):
    SPRING = "弹簧效应"
    TEST = "测试"
    SOS = "强势信号"
    BC = "抢购高潮"
    SC = "抛售高潮"

# 常量配置
WYCKOFF_PARAMS = {
    'lookback': 60,
    'spring_volume_ratio': 1.5,  # 弹簧量比
    'sos_volume_ratio': 1.3,     # 突破量比
    'spring_low_ratio': 0.98,    # 跌破幅度
    'spring_close_ratio': 0.995, # 收回幅度
    'trend_threshold': 5.0,      # 20 日趋势阈值 (5%)
    'vol_climax_mult': 2.0       # 高量日判定 (2 倍均量)
}

@dataclass
class WyckoffSignal:
    event: WyckoffEvent
    confidence: float
    description: str
    date: str
    price: float

@dataclass
class StockAnalysis:
    symbol: str
    name: str
    industry: str
    phase: WyckoffPhase
    phase_confidence: float
    signals: List[WyckoffSignal]
    composite_score: float
    technicals: Dict
    recommendation: str
    data_freshness: str = "unknown"

class WyckoffAnalyzer:
    """优化的威科夫分析引擎"""
    
    def __init__(self, **kwargs):
        # 支持传入配置参数，默认为类常量
        config = WYCKOFF_PARAMS.copy()
        for k, v in kwargs.items():
            if hasattr(WYCKOFF_PARAMS, k):
                config[k] = v
        self.lookback = config.get('lookback', 60)
        config['lookback'] = self.lookback

    def analyze(self, symbol: str, info: Dict, df: pd.DataFrame) -> Optional[StockAnalysis]:
        if len(df) < self.lookback:
            return None
        
        # 检查数据时效性
        if not pd.api.types.is_datetime64_any_dtype(df.index):
            logger.warning("检测到非时间索引数据")
            return None
            
        try:
            # 1. 计算基础技术位 (缓存到 tech dict)
            tech = self._calculate_technicals(df)
            
            # 2. 向量化信号检测 (替代 for 循环)
            signals = self._detect_signals_vectorized(df, tech)
            
            # 3. 阶段识别 (增加上下文判断)
            phase, phase_conf, phase_reason = self._identify_phase_smart(df, signals, tech)
            
            # 4. 综合评分
            score = self._calculate_score(phase, signals, tech)
            
            # 5. 生成建议
            rec = self._generate_recommendation(phase, score, signals)
            
            last_date = df.index[-1]
            days_stale = (datetime.now() - last_date).days
            freshness = "新鲜" if days_stale <= 2 else "较旧" if days_stale <= 7 else "过期"
            
            return StockAnalysis(
                symbol=symbol,
                name=info.get('name', symbol),
                industry=info.get('industry', '未知'),
                phase=phase,
                phase_confidence=phase_conf,
                signals=signals,
                composite_score=score,
                technicals=tech,
                recommendation=rec,
                data_freshness=freshness
            )
        except Exception as e:
            logger.error(f"分析 {symbol} 出错: {e}", exc_info=True)
            return None
    
    def _calculate_technicals(self, df: pd.DataFrame) -> Dict:
        close = df['close']
        high = df['high']
        low = df['low']
        volume = df['volume']
        
        # 使用滚动指标
        ma20 = close.rolling(20).mean()
        ma60 = close.rolling(60).mean()
        
        # ATR 优化 (标准 TR 计算)
        tr1 = high - low
        tr2 = high - close.shift(1)
        tr3 = low - close.shift(1)
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(14).mean()
        
        # 支撑阻力 (使用过去 50 天的高低价，而非滚动极值，更稳健)
        support_candidates = low.rolling(50, min_periods=1).min()
        resistance_candidates = high.rolling(50, min_periods=1).max()
        
        # 获取最近几个关键水平
        current_price = close.iloc[-1]
        
        return {
            'current_price': current_price,
            'ma20': ma20.iloc[-1],
            'ma60': ma60.iloc[-1],
            'atr': atr.iloc[-1] if not np.isnan(atr.iloc[-1]) else 0,
            'vol_ratio': volume.iloc[-1] / volume.rolling(20, min_periods=1).mean().iloc[-1],
            'support_key': support_candidates.iloc[-1],
            'resistance_key': resistance_candidates.iloc[-1],
            'rs_pct': (current_price / ma20.iloc[-1] - 1) * 100,
            'trend_20d': (current_price / close.iloc[-20] - 1) * 100 if len(close) >= 20 else 0,
            'range_pos': (current_price - support_candidates.iloc[-1]) / (resistance_candidates.iloc[-1] - support_candidates.iloc[-1] + 0.001)
        }
    
    def _detect_signals_vectorized(self, df: pd.DataFrame, tech: Dict) -> List[WyckoffSignal]:
        signals = []
        recent = df.tail(10).copy() # 使用 copy 避免 SettingWithCopyWarning
        
        # 使用 shift 创建当前和前一个 K 线数据
        curr = recent
        prev = recent.shift(1)
        
        # 确保有数据可比较
        if len(curr) < 2:
            return signals
            
        # 弹簧效应 (SPRING)
        spring_cond = (
            (curr['close'] < prev['close'] * WYCKOFF_PARAMS['spring_low_ratio']) & 
            (curr['close'] >= prev['close'] * WYCKOFF_PARAMS['spring_close_ratio']) &
            (curr['volume'] > prev['volume'] * WYCKOFF_PARAMS['spring_volume_ratio'])
        )
        springs = curr.loc[spring_cond, 'close'].tolist()
        dates = curr[spring_cond].index.tolist()
        
        for i in range(len(springs)):
            signals.append(WyckoffSignal(
                event=WyckoffEvent.SPRING,
                confidence=0.8,
                description=f"弹簧效应：跌破关键位后收回，放量 {springs[i]/(curr.iloc[i-1]['close']/curr.iloc[i-1]['volume']*curr.iloc[i-1]['volume']):.1f} 倍",
                date=str(dates[i])[:10],
                price=springs[i]
            ))
        
        # 强势突破 (SOS) - 修复代码结构
        # 先获取与curr相同时间段的成交量均值
        vol_ma20_full = df['volume'].rolling(20, min_periods=1).mean()
        vol_ma20_curr = curr['volume'] / curr.index.map(vol_ma20_full)
        
        sos_cond = (
            (curr['close'] > tech['resistance_key'] * 0.99) &
            (curr['volume'] > vol_ma20_curr * WYCKOFF_PARAMS['sos_volume_ratio'])
        )
        sos = curr[sos_cond]
        
        for _, row in sos.iterrows():
            signals.append(WyckoffSignal(
                event=WyckoffEvent.SOS,
                confidence=0.85,
                description=f"强势信号：突破关键阻力位，放巨量",
                date=str(row.name)[:10],
                price=row['close']
            ))
        
        # 简单增加 BC/SC 检测逻辑 (示例)
        # 抛售高潮：高位下跌 + 巨量
        vol_mean = df['volume'].rolling(20, min_periods=1).mean().reindex(curr.index)
        sc_cond = (curr['close'] < prev['close'] * 0.97) & (curr['volume'] > vol_mean * WYCKOFF_PARAMS['vol_climax_mult'])
        if sc_cond.any():
            # 只记录最近的几个
            sc_indices = curr.index[sc_cond]
            for idx in sc_indices:
                 signals.append(WyckoffSignal(
                    event=WyckoffEvent.SC,
                    confidence=0.6,
                    description=f"抛售高潮：高位放量",
                    date=str(idx)[:10],
                    price=curr['close'][idx]
                ))
        
        # 按时间排序
        return sorted(signals, key=lambda x: datetime.strptime(x.date, '%Y-%m-%d'), reverse=True)
        
    def _identify_phase_smart(self, df: pd.DataFrame, signals: List[WyckoffSignal], tech: Dict) -> Tuple[WyckoffPhase, float, str]:
        if not signals:
            return WyckoffPhase.UNKNOWN, 0.1, "无信号"
        
        recent = df.tail(5)
        price = tech['current_price']
        
        # 逻辑增强：结合价格在 MA 上的位置判断趋势
        if price > tech['ma20'] and price > tech['ma60']:
            trend_direction = "Up"
        else:
            trend_direction = "Down"
            
        last_event = signals[-1].event if signals else None
        signals_map = {e.name: e for e in WyckoffEvent}
        
        # 简化：优先基于最近事件，其次基于趋势
        if last_event == WyckoffEvent.SPRING:
            # 弹簧后通常进入吸筹尾声或突破，检查是否放量突破
            if price > tech['resistance_key']:
                return WyckoffPhase.MARKUP, 0.85, "弹簧后突破"
            else:
                return WyckoffPhase.ACCUMULATION, 0.7, "弹簧后整理"
        elif last_event == WyckoffEvent.SOS:
            return WyckoffPhase.MARKUP, 0.9, "强势突破信号"
        elif last_event == WyckoffEvent.SC:
            return WyckoffPhase.DISTRIBUTION, 0.7, "派发信号"
            
        # 基于趋势补充判断
        if trend_direction == "Up":
            if tech['trend_20d'] > WYCKOFF_PARAMS['trend_threshold']:
                return WyckoffPhase.MARKUP, 0.6, "强势上涨"
            else:
                return WyckoffPhase.ACCUMULATION, 0.5, "震荡上涨"
        else:
            if tech['trend_20d'] < -WYCKOFF_PARAMS['trend_threshold']:
                return WyckoffPhase.MARKDOWN, 0.6, "弱势下跌"
            else:
                return WyckoffPhase.ACCUMULATION, 0.5, "下跌中继"
        
        return WyckoffPhase.UNKNOWN, 0.3, "未知"

    def _calculate_score(self, phase: WyckoffPhase, signals: List[WyckoffSignal], tech: Dict) -> float:
        score = 50
        
        # 阶段加分/减分
        base_scores = {
            WyckoffPhase.ACCUMULATION: 30, # 吸筹通常可买，给分
            WyckoffPhase.MARKUP: 70,       # 上涨趋势
            WyckoffPhase.DISTRIBUTION: 10,  # 派发风险
            WyckoffPhase.MARKDOWN: -30     # 下跌风险
        }
        score += base_scores.get(phase, 0)
        
        # 信号加权
        for sig in signals:
            if sig.event == WyckoffEvent.SPRING:
                score += 10 # 弹簧是洗盘信号
            elif sig.event == WyckoffEvent.SOS:
                score += 20 # 突破是强信号
            elif sig.event == WyckoffEvent.SC:
                score -= 20 # 抛售高潮看空
        
        # 价格区间位置
        if 0.2 < tech['range_pos'] < 0.8:
            score += 5
        
        return min(100, max(0, score))
    
    def _generate_recommendation(self, phase: WyckoffPhase, score: float, signals: List[WyckoffSignal]) -> str:
        if score >= 85:
            return "买入：趋势确立"
        elif score >= 70 and phase == WyckoffPhase.MARKUP:
            return "持有：沿均线持有"
        elif phase == WyckoffPhase.ACCUMULATION and score >= 60:
            return "关注：吸筹整理中"
        elif phase in [WyckoffPhase.DISTRIBUTION, WyckoffPhase.MARKDOWN]:
            return "卖出/回避"
        else:
            return "观望"
