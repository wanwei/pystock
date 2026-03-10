from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Optional, Any
import pandas as pd
from datetime import datetime


class SignalType(Enum):
    OPEN_LONG = "open_long"
    CLOSE_LONG = "close_long"
    OPEN_SHORT = "open_short"
    CLOSE_SHORT = "close_short"
    HOLD = "hold"


class SignalStrength(Enum):
    STRONG = 3
    MEDIUM = 2
    WEAK = 1


@dataclass
class Signal:
    signal_type: SignalType
    strength: SignalStrength
    price: float
    datetime: datetime
    reason: str = ""
    confidence: float = 0.0
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class TradeResult:
    entry_price: float
    exit_price: float
    entry_time: datetime
    exit_time: datetime
    profit: float
    profit_pct: float
    hold_periods: int
    signal: Signal


class BaseIndicator(ABC):
    """
    技术指标基类
    
    所有技术指标都需要继承此类并实现 calculate 方法
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """指标名称"""
        pass
    
    @property
    def params(self) -> Dict[str, Any]:
        """指标参数"""
        return {}
    
    @abstractmethod
    def calculate(self, kline_data: pd.DataFrame) -> pd.DataFrame:
        """
        计算指标值
        
        Args:
            kline_data: K线数据，包含 date, open, close, high, low, volume 等列
            
        Returns:
            DataFrame: 原始数据加上指标列
        """
        pass
    
    def validate_data(self, kline_data: pd.DataFrame) -> bool:
        """
        验证输入数据是否有效
        
        Args:
            kline_data: K线数据
            
        Returns:
            bool: 数据是否有效
        """
        required_columns = ['open', 'close', 'high', 'low']
        return all(col in kline_data.columns for col in required_columns)


class BaseStrategy(ABC):
    """
    策略基类
    
    所有交易策略都需要继承此类并实现 generate_signals 方法
    """
    
    def __init__(self, name: str = None):
        self._name = name or self.__class__.__name__
        self._indicators: List[BaseIndicator] = []
        self._params: Dict[str, Any] = {}
    
    @property
    def name(self) -> str:
        """策略名称"""
        return self._name
    
    @property
    def indicators(self) -> List[BaseIndicator]:
        """策略使用的指标列表"""
        return self._indicators
    
    @property
    def params(self) -> Dict[str, Any]:
        """策略参数"""
        return self._params
    
    def add_indicator(self, indicator: BaseIndicator) -> 'BaseStrategy':
        """
        添加技术指标
        
        Args:
            indicator: 技术指标实例
            
        Returns:
            self: 支持链式调用
        """
        self._indicators.append(indicator)
        return self
    
    def set_params(self, **kwargs) -> 'BaseStrategy':
        """
        设置策略参数
        
        Args:
            **kwargs: 参数键值对
            
        Returns:
            self: 支持链式调用
        """
        self._params.update(kwargs)
        return self
    
    @abstractmethod
    def generate_signals(self, kline_data: pd.DataFrame) -> List[Signal]:
        """
        生成交易信号
        
        Args:
            kline_data: K线数据
            
        Returns:
            List[Signal]: 信号列表
        """
        pass
    
    def preprocess_data(self, kline_data: pd.DataFrame) -> pd.DataFrame:
        """
        数据预处理，计算所有指标
        
        Args:
            kline_data: 原始K线数据
            
        Returns:
            DataFrame: 添加了指标的数据
        """
        df = kline_data.copy()
        
        for indicator in self._indicators:
            if indicator.validate_data(df):
                df = indicator.calculate(df)
        
        return df
    
    def validate_signals(self, signals: List[Signal]) -> List[Signal]:
        """
        验证和过滤信号
        
        Args:
            signals: 原始信号列表
            
        Returns:
            List[Signal]: 过滤后的信号列表
        """
        return [s for s in signals if s.signal_type != SignalType.HOLD]


class BaseBacktest(ABC):
    """
    回测基类
    
    提供策略回测的基础框架
    """
    
    def __init__(self, strategy: BaseStrategy, initial_capital: float = 100000.0):
        self.strategy = strategy
        self.initial_capital = initial_capital
        self._results: List[TradeResult] = []
        self._equity_curve: pd.DataFrame = None
    
    @abstractmethod
    def run(self, kline_data: pd.DataFrame) -> Dict[str, Any]:
        """
        执行回测
        
        Args:
            kline_data: K线数据
            
        Returns:
            Dict: 回测结果，包含收益、胜率等统计信息
        """
        pass
    
    @abstractmethod
    def get_trade_history(self) -> List[TradeResult]:
        """
        获取交易历史
        
        Returns:
            List[TradeResult]: 交易结果列表
        """
        pass
    
    @abstractmethod
    def get_equity_curve(self) -> pd.DataFrame:
        """
        获取资金曲线
        
        Returns:
            DataFrame: 资金变化曲线
        """
        pass
    
    @abstractmethod
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取回测统计信息
        
        Returns:
            Dict: 统计信息，包含：
                - total_return: 总收益率
                - annual_return: 年化收益率
                - max_drawdown: 最大回撤
                - win_rate: 胜率
                - profit_factor: 盈亏比
                - sharpe_ratio: 夏普比率
                - total_trades: 总交易次数
        """
        pass


class StrategyAnalyzer(ABC):
    """
    策略分析器基类
    
    用于分析策略的表现和特征
    """
    
    @abstractmethod
    def analyze(self, strategy: BaseStrategy, kline_data: pd.DataFrame) -> Dict[str, Any]:
        """
        分析策略表现
        
        Args:
            strategy: 策略实例
            kline_data: K线数据
            
        Returns:
            Dict: 分析结果
        """
        pass
    
    @abstractmethod
    def compare_strategies(self, strategies: List[BaseStrategy], 
                          kline_data: pd.DataFrame) -> pd.DataFrame:
        """
        比较多个策略的表现
        
        Args:
            strategies: 策略列表
            kline_data: K线数据
            
        Returns:
            DataFrame: 策略比较结果
        """
        pass


class PortfolioManager(ABC):
    """
    组合管理器基类
    
    管理多个股票的策略组合
    """
    
    @abstractmethod
    def add_position(self, symbol: str, strategy: BaseStrategy, weight: float = 1.0):
        """
        添加持仓
        
        Args:
            symbol: 股票代码
            strategy: 策略实例
            weight: 权重
        """
        pass
    
    @abstractmethod
    def remove_position(self, symbol: str):
        """
        移除持仓
        
        Args:
            symbol: 股票代码
        """
        pass
    
    @abstractmethod
    def rebalance(self, kline_data_dict: Dict[str, pd.DataFrame]) -> List[Signal]:
        """
        组合再平衡
        
        Args:
            kline_data_dict: 各股票的K线数据字典
            
        Returns:
            List[Signal]: 调仓信号列表
        """
        pass
    
    @abstractmethod
    def get_portfolio_signals(self, kline_data_dict: Dict[str, pd.DataFrame]) -> Dict[str, List[Signal]]:
        """
        获取组合中所有股票的信号
        
        Args:
            kline_data_dict: 各股票的K线数据字典
            
        Returns:
            Dict[str, List[Signal]]: 各股票的信号列表
        """
        pass


class RiskManager(ABC):
    """
    风险管理器基类
    
    管理策略的风险控制
    """
    
    @abstractmethod
    def calculate_position_size(self, capital: float, price: float, 
                                signal: Signal) -> float:
        """
        计算仓位大小
        
        Args:
            capital: 可用资金
            price: 当前价格
            signal: 交易信号
            
        Returns:
            float: 建议仓位数量
        """
        pass
    
    @abstractmethod
    def check_risk(self, position: Dict[str, Any], current_price: float) -> Optional[Signal]:
        """
        检查风险并生成风控信号
        
        Args:
            position: 当前持仓信息
            current_price: 当前价格
            
        Returns:
            Optional[Signal]: 风控信号（如止损信号）
        """
        pass
    
    @abstractmethod
    def set_stop_loss(self, entry_price: float, strategy_params: Dict[str, Any]) -> float:
        """
        设置止损价格
        
        Args:
            entry_price: 入场价格
            strategy_params: 策略参数
            
        Returns:
            float: 止损价格
        """
        pass
    
    @abstractmethod
    def set_take_profit(self, entry_price: float, strategy_params: Dict[str, Any]) -> float:
        """
        设置止盈价格
        
        Args:
            entry_price: 入场价格
            strategy_params: 策略参数
            
        Returns:
            float: 止盈价格
        """
        pass
