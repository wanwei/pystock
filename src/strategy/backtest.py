import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
from datetime import datetime
from .interfaces import BaseBacktest, BaseStrategy, Signal, SignalType, TradeResult


class SimpleBacktest(BaseBacktest):
    """
    简单回测引擎
    
    基于信号进行简单的买卖回测
    """
    
    def __init__(self, strategy: BaseStrategy, initial_capital: float = 100000.0,
                 commission_rate: float = 0.0003, slippage: float = 0.001):
        super().__init__(strategy, initial_capital)
        self._commission_rate = commission_rate
        self._slippage = slippage
        self._position: Optional[Dict[str, Any]] = None
        self._capital = initial_capital
        self._equity_history: List[Dict[str, Any]] = []
    
    def run(self, kline_data: pd.DataFrame) -> Dict[str, Any]:
        df = self.strategy.preprocess_data(kline_data)
        signals = self.strategy.generate_signals(kline_data)
        
        self._results = []
        self._equity_history = []
        self._capital = self.initial_capital
        self._position = None
        
        signal_dict = {}
        for signal in signals:
            signal_dict[signal.datetime] = signal
        
        for i in range(len(df)):
            date_val = df['date'].iloc[i] if 'date' in df.columns else df.index[i]
            if isinstance(date_val, str):
                date_val = pd.to_datetime(date_val)
            elif not isinstance(date_val, datetime):
                date_val = pd.to_datetime(str(date_val))
            
            close_price = df['close'].iloc[i]
            
            if date_val in signal_dict:
                signal = signal_dict[date_val]
                self._process_signal(signal, close_price)
            
            equity = self._calculate_equity(close_price)
            self._equity_history.append({
                'datetime': date_val,
                'equity': equity,
                'capital': self._capital,
                'position': self._position is not None
            })
        
        self._equity_curve = pd.DataFrame(self._equity_history)
        
        return self.get_statistics()
    
    def _process_signal(self, signal: Signal, price: float):
        actual_price = price * (1 + self._slippage if signal.signal_type == SignalType.OPEN_LONG 
                               else 1 - self._slippage)
        
        if signal.signal_type == SignalType.OPEN_LONG and self._position is None:
            shares = int(self._capital * 0.95 / actual_price)
            if shares > 0:
                cost = shares * actual_price * (1 + self._commission_rate)
                self._position = {
                    'entry_price': actual_price,
                    'entry_time': signal.datetime,
                    'shares': shares,
                    'cost': cost,
                    'signal': signal
                }
                self._capital -= cost
        
        elif signal.signal_type == SignalType.CLOSE_LONG and self._position is not None:
            revenue = self._position['shares'] * actual_price * (1 - self._commission_rate)
            profit = revenue - self._position['cost']
            profit_pct = profit / self._position['cost']
            
            hold_periods = 0
            if 'datetime' in self._equity_history:
                entry_idx = next((i for i, h in enumerate(self._equity_history) 
                                 if h.get('position')), len(self._equity_history))
                hold_periods = len(self._equity_history) - entry_idx
            
            trade_result = TradeResult(
                entry_price=self._position['entry_price'],
                exit_price=actual_price,
                entry_time=self._position['entry_time'],
                exit_time=signal.datetime,
                profit=profit,
                profit_pct=profit_pct,
                hold_periods=hold_periods,
                signal=self._position['signal']
            )
            self._results.append(trade_result)
            
            self._capital += revenue
            self._position = None
    
    def _calculate_equity(self, current_price: float) -> float:
        equity = self._capital
        if self._position is not None:
            equity += self._position['shares'] * current_price
        return equity
    
    def get_trade_history(self) -> List[TradeResult]:
        return self._results
    
    def get_equity_curve(self) -> pd.DataFrame:
        return self._equity_curve
    
    def get_statistics(self) -> Dict[str, Any]:
        if not self._results:
            return {
                'total_return': 0,
                'annual_return': 0,
                'max_drawdown': 0,
                'win_rate': 0,
                'profit_factor': 0,
                'sharpe_ratio': 0,
                'total_trades': 0
            }
        
        total_profit = sum(r.profit for r in self._results)
        total_return = (self._capital - self.initial_capital) / self.initial_capital
        
        wins = [r for r in self._results if r.profit > 0]
        losses = [r for r in self._results if r.profit <= 0]
        win_rate = len(wins) / len(self._results) if self._results else 0
        
        total_win = sum(r.profit for r in wins)
        total_loss = abs(sum(r.profit for r in losses))
        profit_factor = total_win / total_loss if total_loss > 0 else float('inf')
        
        if self._equity_curve is not None and len(self._equity_curve) > 0:
            equity_series = self._equity_curve['equity']
            rolling_max = equity_series.expanding().max()
            drawdown = (equity_series - rolling_max) / rolling_max
            max_drawdown = abs(drawdown.min())
            
            returns = equity_series.pct_change().dropna()
            sharpe_ratio = (returns.mean() * 252) / (returns.std() * np.sqrt(252)) if returns.std() > 0 else 0
            
            if len(self._equity_curve) > 1:
                days = (self._equity_curve['datetime'].iloc[-1] - 
                       self._equity_curve['datetime'].iloc[0]).days
                annual_return = (1 + total_return) ** (365 / max(days, 1)) - 1 if days > 0 else 0
            else:
                annual_return = 0
        else:
            max_drawdown = 0
            sharpe_ratio = 0
            annual_return = 0
        
        return {
            'total_return': total_return,
            'annual_return': annual_return,
            'max_drawdown': max_drawdown,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'sharpe_ratio': sharpe_ratio,
            'total_trades': len(self._results),
            'total_profit': total_profit,
            'win_count': len(wins),
            'loss_count': len(losses),
            'avg_profit': total_profit / len(self._results) if self._results else 0,
            'avg_win': total_win / len(wins) if wins else 0,
            'avg_loss': total_loss / len(losses) if losses else 0
        }


class VectorizedBacktest(BaseBacktest):
    """
    向量化回测引擎
    
    使用向量化计算提高回测效率
    """
    
    def __init__(self, strategy: BaseStrategy, initial_capital: float = 100000.0,
                 commission_rate: float = 0.0003):
        super().__init__(strategy, initial_capital)
        self._commission_rate = commission_rate
    
    def run(self, kline_data: pd.DataFrame) -> Dict[str, Any]:
        df = self.strategy.preprocess_data(kline_data)
        signals = self.strategy.generate_signals(kline_data)
        
        df = df.copy()
        df['signal'] = 0
        
        for signal in signals:
            date_val = signal.datetime
            if isinstance(date_val, datetime):
                date_str = date_val
            else:
                date_str = pd.to_datetime(date_val)
            
            mask = df['date'] == date_str if 'date' in df.columns else df.index == date_str
            if signal.signal_type == SignalType.OPEN_LONG:
                df.loc[mask, 'signal'] = 1
            elif signal.signal_type == SignalType.CLOSE_LONG:
                df.loc[mask, 'signal'] = -1
        
        df['position'] = df['signal'].replace(0, np.nan).ffill().fillna(0)
        df['position'] = df['position'].shift(1).fillna(0)
        
        df['returns'] = df['close'].pct_change()
        df['strategy_returns'] = df['position'] * df['returns']
        
        df['equity'] = self.initial_capital * (1 + df['strategy_returns']).cumprod()
        
        self._equity_curve = df[['date', 'equity', 'position', 'returns', 'strategy_returns']].copy()
        self._equity_curve = self._equity_curve.rename(columns={'date': 'datetime'})
        
        self._results = self._extract_trades(df)
        
        return self.get_statistics()
    
    def _extract_trades(self, df: pd.DataFrame) -> List[TradeResult]:
        trades = []
        position_changes = df['position'].diff()
        
        entry_indices = df.index[position_changes == 1].tolist()
        exit_indices = df.index[position_changes == -1].tolist()
        
        for i, entry_idx in enumerate(entry_indices):
            exit_idx = next((x for x in exit_indices if x > entry_idx), None)
            
            if exit_idx is not None:
                entry_price = df.loc[entry_idx, 'close']
                exit_price = df.loc[exit_idx, 'close']
                
                entry_time = df.loc[entry_idx, 'date'] if 'date' in df.columns else df.index[entry_idx]
                exit_time = df.loc[exit_idx, 'date'] if 'date' in df.columns else df.index[exit_idx]
                
                if isinstance(entry_time, str):
                    entry_time = pd.to_datetime(entry_time)
                if isinstance(exit_time, str):
                    exit_time = pd.to_datetime(exit_time)
                
                profit_pct = (exit_price / entry_price) - 1
                profit = self.initial_capital * 0.95 * profit_pct
                
                trades.append(TradeResult(
                    entry_price=entry_price,
                    exit_price=exit_price,
                    entry_time=entry_time,
                    exit_time=exit_time,
                    profit=profit,
                    profit_pct=profit_pct,
                    hold_periods=exit_idx - entry_idx,
                    signal=None
                ))
        
        return trades
    
    def get_trade_history(self) -> List[TradeResult]:
        return self._results
    
    def get_equity_curve(self) -> pd.DataFrame:
        return self._equity_curve
    
    def get_statistics(self) -> Dict[str, Any]:
        if self._equity_curve is None or len(self._equity_curve) == 0:
            return self._empty_stats()
        
        equity = self._equity_curve['equity']
        returns = self._equity_curve['strategy_returns'].dropna()
        
        total_return = (equity.iloc[-1] / self.initial_capital) - 1
        
        rolling_max = equity.expanding().max()
        drawdown = (equity - rolling_max) / rolling_max
        max_drawdown = abs(drawdown.min())
        
        sharpe_ratio = 0
        if len(returns) > 0 and returns.std() > 0:
            sharpe_ratio = (returns.mean() * 252) / (returns.std() * np.sqrt(252))
        
        annual_return = 0
        if len(self._equity_curve) > 1:
            days = (self._equity_curve['datetime'].iloc[-1] - 
                   self._equity_curve['datetime'].iloc[0]).days
            if days > 0:
                annual_return = (1 + total_return) ** (365 / days) - 1
        
        wins = [r for r in self._results if r.profit > 0]
        losses = [r for r in self._results if r.profit <= 0]
        win_rate = len(wins) / len(self._results) if self._results else 0
        
        total_win = sum(r.profit for r in wins)
        total_loss = abs(sum(r.profit for r in losses))
        profit_factor = total_win / total_loss if total_loss > 0 else float('inf')
        
        return {
            'total_return': total_return,
            'annual_return': annual_return,
            'max_drawdown': max_drawdown,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'sharpe_ratio': sharpe_ratio,
            'total_trades': len(self._results),
            'total_profit': sum(r.profit for r in self._results),
            'win_count': len(wins),
            'loss_count': len(losses)
        }
    
    def _empty_stats(self) -> Dict[str, Any]:
        return {
            'total_return': 0,
            'annual_return': 0,
            'max_drawdown': 0,
            'win_rate': 0,
            'profit_factor': 0,
            'sharpe_ratio': 0,
            'total_trades': 0
        }
