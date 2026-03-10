import pandas as pd
import numpy as np
from typing import Dict, Any
from .interfaces import BaseIndicator


class MAIndicator(BaseIndicator):
    """
    移动平均线指标 (Moving Average)
    
    支持简单移动平均(SMA)和指数移动平均(EMA)
    """
    
    def __init__(self, period: int = 20, ma_type: str = 'SMA'):
        """
        Args:
            period: 周期
            ma_type: 移动平均类型 ('SMA' 或 'EMA')
        """
        self._period = period
        self._ma_type = ma_type.upper()
    
    @property
    def name(self) -> str:
        return f"MA_{self._period}_{self._ma_type}"
    
    @property
    def params(self) -> Dict[str, Any]:
        return {'period': self._period, 'type': self._ma_type}
    
    def calculate(self, kline_data: pd.DataFrame) -> pd.DataFrame:
        df = kline_data.copy()
        col_name = f'MA{self._period}'
        
        if self._ma_type == 'SMA':
            df[col_name] = df['close'].rolling(window=self._period).mean()
        elif self._ma_type == 'EMA':
            df[col_name] = df['close'].ewm(span=self._period, adjust=False).mean()
        else:
            raise ValueError(f"不支持的移动平均类型: {self._ma_type}")
        
        return df


class MACDIndicator(BaseIndicator):
    """
    MACD指标 (Moving Average Convergence Divergence)
    
    包含 MACD线、信号线、柱状图
    """
    
    def __init__(self, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9):
        """
        Args:
            fast_period: 快线周期
            slow_period: 慢线周期
            signal_period: 信号线周期
        """
        self._fast_period = fast_period
        self._slow_period = slow_period
        self._signal_period = signal_period
    
    @property
    def name(self) -> str:
        return f"MACD_{self._fast_period}_{self._slow_period}_{self._signal_period}"
    
    @property
    def params(self) -> Dict[str, Any]:
        return {
            'fast_period': self._fast_period,
            'slow_period': self._slow_period,
            'signal_period': self._signal_period
        }
    
    def calculate(self, kline_data: pd.DataFrame) -> pd.DataFrame:
        df = kline_data.copy()
        
        ema_fast = df['close'].ewm(span=self._fast_period, adjust=False).mean()
        ema_slow = df['close'].ewm(span=self._slow_period, adjust=False).mean()
        
        df['MACD'] = ema_fast - ema_slow
        df['MACD_Signal'] = df['MACD'].ewm(span=self._signal_period, adjust=False).mean()
        df['MACD_Hist'] = (df['MACD'] - df['MACD_Signal']) * 2
        
        return df


class RSIIndicator(BaseIndicator):
    """
    RSI指标 (Relative Strength Index)
    
    相对强弱指数
    """
    
    def __init__(self, period: int = 14):
        """
        Args:
            period: 周期
        """
        self._period = period
    
    @property
    def name(self) -> str:
        return f"RSI_{self._period}"
    
    @property
    def params(self) -> Dict[str, Any]:
        return {'period': self._period}
    
    def calculate(self, kline_data: pd.DataFrame) -> pd.DataFrame:
        df = kline_data.copy()
        col_name = f'RSI{self._period}'
        
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = (-delta).where(delta < 0, 0)
        
        avg_gain = gain.rolling(window=self._period).mean()
        avg_loss = loss.rolling(window=self._period).mean()
        
        rs = avg_gain / avg_loss
        df[col_name] = 100 - (100 / (1 + rs))
        
        return df


class BollingerBandsIndicator(BaseIndicator):
    """
    布林带指标 (Bollinger Bands)
    
    包含上轨、中轨、下轨
    """
    
    def __init__(self, period: int = 20, std_dev: float = 2.0):
        """
        Args:
            period: 周期
            std_dev: 标准差倍数
        """
        self._period = period
        self._std_dev = std_dev
    
    @property
    def name(self) -> str:
        return f"BOLL_{self._period}_{self._std_dev}"
    
    @property
    def params(self) -> Dict[str, Any]:
        return {'period': self._period, 'std_dev': self._std_dev}
    
    def calculate(self, kline_data: pd.DataFrame) -> pd.DataFrame:
        df = kline_data.copy()
        
        df['BOLL_MID'] = df['close'].rolling(window=self._period).mean()
        std = df['close'].rolling(window=self._period).std()
        
        df['BOLL_UPPER'] = df['BOLL_MID'] + (std * self._std_dev)
        df['BOLL_LOWER'] = df['BOLL_MID'] - (std * self._std_dev)
        df['BOLL_WIDTH'] = (df['BOLL_UPPER'] - df['BOLL_LOWER']) / df['BOLL_MID']
        
        return df


class KDJIndicator(BaseIndicator):
    """
    KDJ指标
    
    随机指标，包含K、D、J三条线
    """
    
    def __init__(self, n: int = 9, m1: int = 3, m2: int = 3):
        """
        Args:
            n: RSV计算周期
            m1: K值平滑周期
            m2: D值平滑周期
        """
        self._n = n
        self._m1 = m1
        self._m2 = m2
    
    @property
    def name(self) -> str:
        return f"KDJ_{self._n}_{self._m1}_{self._m2}"
    
    @property
    def params(self) -> Dict[str, Any]:
        return {'n': self._n, 'm1': self._m1, 'm2': self._m2}
    
    def calculate(self, kline_data: pd.DataFrame) -> pd.DataFrame:
        df = kline_data.copy()
        
        low_min = df['low'].rolling(window=self._n).min()
        high_max = df['high'].rolling(window=self._n).max()
        
        df['RSV'] = (df['close'] - low_min) / (high_max - low_min) * 100
        
        df['K'] = df['RSV'].ewm(alpha=1/self._m1, adjust=False).mean()
        df['D'] = df['K'].ewm(alpha=1/self._m2, adjust=False).mean()
        df['J'] = 3 * df['K'] - 2 * df['D']
        
        return df


class ATRIndicator(BaseIndicator):
    """
    ATR指标 (Average True Range)
    
    真实波动幅度均值
    """
    
    def __init__(self, period: int = 14):
        """
        Args:
            period: 周期
        """
        self._period = period
    
    @property
    def name(self) -> str:
        return f"ATR_{self._period}"
    
    @property
    def params(self) -> Dict[str, Any]:
        return {'period': self._period}
    
    def calculate(self, kline_data: pd.DataFrame) -> pd.DataFrame:
        df = kline_data.copy()
        
        high = df['high']
        low = df['low']
        close = df['close'].shift(1)
        
        tr1 = high - low
        tr2 = abs(high - close)
        tr3 = abs(low - close)
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        df[f'ATR{self._period}'] = tr.rolling(window=self._period).mean()
        
        return df


class VolumeIndicator(BaseIndicator):
    """
    成交量指标
    
    包含成交量移动平均和量价关系
    """
    
    def __init__(self, period: int = 5):
        """
        Args:
            period: 成交量均线周期
        """
        self._period = period
    
    @property
    def name(self) -> str:
        return f"VOL_{self._period}"
    
    @property
    def params(self) -> Dict[str, Any]:
        return {'period': self._period}
    
    def calculate(self, kline_data: pd.DataFrame) -> pd.DataFrame:
        df = kline_data.copy()
        
        df[f'VOL_MA{self._period}'] = df['volume'].rolling(window=self._period).mean()
        
        if 'amount' in df.columns:
            df[f'AMT_MA{self._period}'] = df['amount'].rolling(window=self._period).mean()
        
        df['VOL_RATIO'] = df['volume'] / df[f'VOL_MA{self._period}']
        
        return df


class OBVIndicator(BaseIndicator):
    """
    OBV指标 (On Balance Volume)
    
    能量潮指标
    """
    
    def __init__(self):
        pass
    
    @property
    def name(self) -> str:
        return "OBV"
    
    @property
    def params(self) -> Dict[str, Any]:
        return {}
    
    def calculate(self, kline_data: pd.DataFrame) -> pd.DataFrame:
        df = kline_data.copy()
        
        direction = np.where(df['close'] > df['close'].shift(1), 1,
                            np.where(df['close'] < df['close'].shift(1), -1, 0))
        df['OBV'] = (df['volume'] * direction).cumsum()
        
        return df
