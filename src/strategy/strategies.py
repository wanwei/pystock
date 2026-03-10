import pandas as pd
from typing import List, Dict, Any
from datetime import datetime
from .interfaces import BaseStrategy, Signal, SignalType, SignalStrength
from .indicators import MAIndicator, MACDIndicator, RSIIndicator


class MACrossStrategy(BaseStrategy):
    """
    均线交叉策略
    
    当短期均线上穿长期均线时买入
    当短期均线下穿长期均线时卖出
    """
    
    def __init__(self, fast_period: int = 5, slow_period: int = 20, name: str = None):
        super().__init__(name)
        self._fast_period = fast_period
        self._slow_period = slow_period
        
        self.add_indicator(MAIndicator(period=fast_period, ma_type='EMA'))
        self.add_indicator(MAIndicator(period=slow_period, ma_type='EMA'))
        
        self.set_params(
            fast_period=fast_period,
            slow_period=slow_period
        )
    
    def generate_signals(self, kline_data: pd.DataFrame) -> List[Signal]:
        df = self.preprocess_data(kline_data)
        
        signals = []
        fast_col = f'MA{self._fast_period}'
        slow_col = f'MA{self._slow_period}'
        
        for i in range(1, len(df)):
            prev_fast = df[fast_col].iloc[i-1]
            prev_slow = df[slow_col].iloc[i-1]
            curr_fast = df[fast_col].iloc[i]
            curr_slow = df[slow_col].iloc[i]
            
            if pd.isna(prev_fast) or pd.isna(prev_slow) or pd.isna(curr_fast) or pd.isna(curr_slow):
                continue
            
            signal = None
            date_val = df['date'].iloc[i] if 'date' in df.columns else df.index[i]
            if isinstance(date_val, str):
                date_val = pd.to_datetime(date_val)
            elif not isinstance(date_val, datetime):
                date_val = pd.to_datetime(str(date_val))
            
            if prev_fast <= prev_slow and curr_fast > curr_slow:
                signal = Signal(
                    signal_type=SignalType.OPEN_LONG,
                    strength=SignalStrength.MEDIUM,
                    price=df['close'].iloc[i],
                    datetime=date_val,
                    reason=f"短期均线{self._fast_period}上穿长期均线{self._slow_period}",
                    confidence=0.7
                )
            elif prev_fast >= prev_slow and curr_fast < curr_slow:
                signal = Signal(
                    signal_type=SignalType.CLOSE_LONG,
                    strength=SignalStrength.MEDIUM,
                    price=df['close'].iloc[i],
                    datetime=date_val,
                    reason=f"短期均线{self._fast_period}下穿长期均线{self._slow_period}",
                    confidence=0.7
                )
            
            if signal:
                signals.append(signal)
        
        return signals


class MACDStrategy(BaseStrategy):
    """
    MACD策略
    
    当MACD上穿信号线时买入
    当MACD下穿信号线时卖出
    """
    
    def __init__(self, fast_period: int = 12, slow_period: int = 26, 
                 signal_period: int = 9, name: str = None):
        super().__init__(name)
        
        self.add_indicator(MACDIndicator(fast_period, slow_period, signal_period))
        
        self.set_params(
            fast_period=fast_period,
            slow_period=slow_period,
            signal_period=signal_period
        )
    
    def generate_signals(self, kline_data: pd.DataFrame) -> List[Signal]:
        df = self.preprocess_data(kline_data)
        
        signals = []
        
        for i in range(1, len(df)):
            prev_macd = df['MACD'].iloc[i-1]
            prev_signal = df['MACD_Signal'].iloc[i-1]
            curr_macd = df['MACD'].iloc[i]
            curr_signal = df['MACD_Signal'].iloc[i]
            curr_hist = df['MACD_Hist'].iloc[i]
            
            if pd.isna(prev_macd) or pd.isna(prev_signal) or pd.isna(curr_macd) or pd.isna(curr_signal):
                continue
            
            signal = None
            date_val = df['date'].iloc[i] if 'date' in df.columns else df.index[i]
            if isinstance(date_val, str):
                date_val = pd.to_datetime(date_val)
            elif not isinstance(date_val, datetime):
                date_val = pd.to_datetime(str(date_val))
            
            if prev_macd <= prev_signal and curr_macd > curr_signal:
                strength = SignalStrength.STRONG if curr_hist > 0 else SignalStrength.MEDIUM
                signal = Signal(
                    signal_type=SignalType.OPEN_LONG,
                    strength=strength,
                    price=df['close'].iloc[i],
                    datetime=date_val,
                    reason="MACD金叉",
                    confidence=0.75 if curr_hist > 0 else 0.6
                )
            elif prev_macd >= prev_signal and curr_macd < curr_signal:
                strength = SignalStrength.STRONG if curr_hist < 0 else SignalStrength.MEDIUM
                signal = Signal(
                    signal_type=SignalType.CLOSE_LONG,
                    strength=strength,
                    price=df['close'].iloc[i],
                    datetime=date_val,
                    reason="MACD死叉",
                    confidence=0.75 if curr_hist < 0 else 0.6
                )
            
            if signal:
                signals.append(signal)
        
        return signals


class RSIStrategy(BaseStrategy):
    """
    RSI策略
    
    RSI < 30 超卖，买入信号
    RSI > 70 超买，卖出信号
    """
    
    def __init__(self, period: int = 14, oversold: float = 30, overbought: float = 70,
                 name: str = None):
        super().__init__(name)
        
        self._oversold = oversold
        self._overbought = overbought
        
        self.add_indicator(RSIIndicator(period))
        
        self.set_params(
            period=period,
            oversold=oversold,
            overbought=overbought
        )
    
    def generate_signals(self, kline_data: pd.DataFrame) -> List[Signal]:
        df = self.preprocess_data(kline_data)
        
        signals = []
        rsi_col = f'RSI{self._params["period"]}'
        
        for i in range(1, len(df)):
            prev_rsi = df[rsi_col].iloc[i-1]
            curr_rsi = df[rsi_col].iloc[i]
            
            if pd.isna(prev_rsi) or pd.isna(curr_rsi):
                continue
            
            signal = None
            date_val = df['date'].iloc[i] if 'date' in df.columns else df.index[i]
            if isinstance(date_val, str):
                date_val = pd.to_datetime(date_val)
            elif not isinstance(date_val, datetime):
                date_val = pd.to_datetime(str(date_val))
            
            if prev_rsi <= self._oversold and curr_rsi > self._oversold:
                signal = Signal(
                    signal_type=SignalType.OPEN_LONG,
                    strength=SignalStrength.STRONG if curr_rsi < 40 else SignalStrength.MEDIUM,
                    price=df['close'].iloc[i],
                    datetime=date_val,
                    reason=f"RSI从超卖区域回升({curr_rsi:.2f})",
                    confidence=0.8 if curr_rsi < 40 else 0.65
                )
            elif prev_rsi >= self._overbought and curr_rsi < self._overbought:
                signal = Signal(
                    signal_type=SignalType.CLOSE_LONG,
                    strength=SignalStrength.STRONG if curr_rsi > 60 else SignalStrength.MEDIUM,
                    price=df['close'].iloc[i],
                    datetime=date_val,
                    reason=f"RSI从超买区域回落({curr_rsi:.2f})",
                    confidence=0.8 if curr_rsi > 60 else 0.65
                )
            
            if signal:
                signals.append(signal)
        
        return signals


class HighBreakoutStrategy(BaseStrategy):
    """
    高点突破策略
    
    策略逻辑:
    1. 找到5日前~50日前的K线中的高点
    2. 前4天K线最高价都低于该价格
    3. 上一根K线最高价低于该价格
    4. 当前K线最高价高于该价格
    
    即: 价格突破过去一段时间的高点时产生买入信号
    """
    
    def __init__(self, lookback_start: int = 5, lookback_end: int = 50, 
                 confirm_days: int = 4, name: str = None):
        """
        Args:
            lookback_start: 回溯起始天数(不含当天)
            lookback_end: 回溯结束天数(不含当天)
            confirm_days: 确认天数，前N天最高价都低于阻力位
        """
        super().__init__(name)
        self._lookback_start = lookback_start
        self._lookback_end = lookback_end
        self._confirm_days = confirm_days
        
        self.set_params(
            lookback_start=lookback_start,
            lookback_end=lookback_end,
            confirm_days=confirm_days
        )
    
    def generate_signals(self, kline_data: pd.DataFrame) -> List[Signal]:
        df = kline_data.copy()
        signals = []
        
        for i in range(self._lookback_end + 1, len(df)):
            start_idx = i - self._lookback_end
            end_idx = i - self._lookback_start
            
            if start_idx < 0 or end_idx >= i:
                continue
            
            lookback_highs = df['high'].iloc[start_idx:end_idx]
            resistance_high = lookback_highs.max()
            
            if pd.isna(resistance_high):
                continue
            
            confirm_highs = df['high'].iloc[i - self._confirm_days:i]
            all_below_resistance = all(confirm_highs < resistance_high)
            
            if not all_below_resistance:
                continue
            
            prev_high = df['high'].iloc[i - 1]
            curr_high = df['high'].iloc[i]
            
            if prev_high < resistance_high and curr_high > resistance_high:
                date_val = df['date'].iloc[i] if 'date' in df.columns else df.index[i]
                if isinstance(date_val, str):
                    date_val = pd.to_datetime(date_val)
                elif not isinstance(date_val, datetime):
                    date_val = pd.to_datetime(str(date_val))
                
                breakout_pct = (curr_high - resistance_high) / resistance_high * 100
                
                strength = SignalStrength.STRONG if breakout_pct > 1 else SignalStrength.MEDIUM
                
                signal = Signal(
                    signal_type=SignalType.OPEN_LONG,
                    strength=strength,
                    price=df['close'].iloc[i],
                    datetime=date_val,
                    reason=f"突破{self._lookback_start}~{self._lookback_end}日前高点{resistance_high:.2f}, 突破幅度{breakout_pct:.2f}%",
                    confidence=0.75,
                    metadata={
                        'resistance_high': resistance_high,
                        'breakout_pct': breakout_pct,
                        'lookback_range': f'{self._lookback_start}~{self._lookback_end}日',
                        'confirm_days': self._confirm_days
                    }
                )
                signals.append(signal)
        
        return signals


class CompositeStrategy(BaseStrategy):
    """
    组合策略
    
    结合多个策略的信号，通过投票机制决定最终信号
    """
    
    def __init__(self, strategies: List[BaseStrategy], min_votes: int = 2, name: str = None):
        super().__init__(name)
        self._strategies = strategies
        self._min_votes = min_votes
    
    def generate_signals(self, kline_data: pd.DataFrame) -> List[Signal]:
        all_signals = []
        for strategy in self._strategies:
            signals = strategy.generate_signals(kline_data)
            all_signals.extend(signals)
        
        signals_by_date: Dict[datetime, List[Signal]] = {}
        for signal in all_signals:
            dt = signal.datetime
            if dt not in signals_by_date:
                signals_by_date[dt] = []
            signals_by_date[dt].append(signal)
        
        final_signals = []
        for dt, signals in signals_by_date.items():
            open_long_count = sum(1 for s in signals if s.signal_type == SignalType.OPEN_LONG)
            close_long_count = sum(1 for s in signals if s.signal_type == SignalType.CLOSE_LONG)
            
            avg_confidence = sum(s.confidence for s in signals) / len(signals)
            avg_price = sum(s.price for s in signals) / len(signals)
            
            if open_long_count >= self._min_votes:
                final_signals.append(Signal(
                    signal_type=SignalType.OPEN_LONG,
                    strength=SignalStrength.STRONG,
                    price=avg_price,
                    datetime=dt,
                    reason=f"组合策略投票通过({open_long_count}/{len(self._strategies)}票)",
                    confidence=avg_confidence,
                    metadata={'votes': open_long_count, 'total_strategies': len(self._strategies)}
                ))
            elif close_long_count >= self._min_votes:
                final_signals.append(Signal(
                    signal_type=SignalType.CLOSE_LONG,
                    strength=SignalStrength.STRONG,
                    price=avg_price,
                    datetime=dt,
                    reason=f"组合策略投票通过({close_long_count}/{len(self._strategies)}票)",
                    confidence=avg_confidence,
                    metadata={'votes': close_long_count, 'total_strategies': len(self._strategies)}
                ))
        
        return sorted(final_signals, key=lambda s: s.datetime)
