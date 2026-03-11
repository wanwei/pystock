import os
import sys
import json
import pandas as pd
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime

if __name__ == "__main__":
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from strategy.interfaces import BaseStrategy, Signal
    from strategy.strategies import HighBreakoutStrategy
else:
    from .interfaces import BaseStrategy, Signal
    from .strategies import HighBreakoutStrategy


class StockScanner:
    """
    股票扫描器
    
    在指定股票列表中搜索满足策略条件的股票
    支持外部传入K线数据管理器以利用缓存
    """
    
    def __init__(self, kline_manager=None, data_dir: str = 'data/kline_data'):
        """
        Args:
            kline_manager: K线数据管理器实例（推荐传入，可利用缓存）
            data_dir: K线数据目录（当kline_manager为None时使用）
        """
        self.kline_manager = kline_manager
        self.data_dir = data_dir
    
    def _load_kline_data(self, symbol: str, market: str, period: str = 'daily') -> Optional[pd.DataFrame]:
        """加载K线数据"""
        if self.kline_manager:
            try:
                df = self.kline_manager.get_data(symbol, market, period)
                if df is not None and not df.empty:
                    if 'date' in df.columns:
                        df['date'] = pd.to_datetime(df['date'])
                        df = df.sort_values('date').reset_index(drop=True)
                    return df
            except Exception as e:
                print(f"加载 {symbol} 数据失败: {e}")
                return None
        
        prefix = {'A股': 'CN', '美股': 'US', '港股': 'HK'}.get(market, 'CN')
        stock_dir = f"{prefix}_{symbol}"
        filepath = os.path.join(self.data_dir, stock_dir, f"{period}.csv")
        
        if not os.path.exists(filepath):
            return None
        
        try:
            df = pd.read_csv(filepath)
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])
                df = df.sort_values('date').reset_index(drop=True)
            return df
        except Exception as e:
            print(f"加载 {symbol} 数据失败: {e}")
            return None
    
    def scan_stocks(self, stocks: List[Dict], strategy: BaseStrategy, period: str = 'daily',
                    min_data_days: int = 60, max_results: int = None,
                    show_progress: bool = True,
                    filters: Dict[str, Any] = None,
                    progress_callback: Callable = None) -> List[Dict[str, Any]]:
        """
        扫描指定股票列表，找出最新一根K线满足策略条件的股票
        
        Args:
            stocks: 要扫描的股票列表，每项包含 symbol, market, name
            strategy: 策略实例
            period: K线周期
            min_data_days: 最小数据天数要求
            max_results: 最大结果数量，None表示不限制
            show_progress: 是否显示进度信息
            filters: 过滤条件，如 {'min_volume': 1000000, 'min_price': 5}
            progress_callback: 进度回调函数 callback(current, total, symbol, results_count)
            
        Returns:
            List[Dict]: 满足条件的股票列表
        """
        results = []
        total = len(stocks)
        
        if show_progress:
            print(f"正在扫描 {total} 只股票...")
        
        for i, stock in enumerate(stocks, 1):
            symbol = stock.get('symbol', '')
            market = stock.get('market', 'A股')
            name = stock.get('name', '')
            
            if progress_callback:
                progress_callback(i, total, symbol, len(results))
            
            if show_progress and i % 100 == 0:
                pct = i / total * 100
                print(f"  进度: {i}/{total} ({pct:.1f}%) - 已找到 {len(results)} 只突破股票")
            
            df = self._load_kline_data(symbol, market, period)
            
            if df is None or len(df) < min_data_days:
                continue
            
            if filters:
                last_row = df.iloc[-1]
                passes_filter = True
                
                if 'min_volume' in filters:
                    volume = last_row.get('volume', 0)
                    if volume < filters['min_volume']:
                        passes_filter = False
                
                if passes_filter and 'min_price' in filters:
                    close_price = last_row.get('close')
                    if close_price is not None and close_price < filters['min_price']:
                        passes_filter = False
                
                if passes_filter and 'max_price' in filters:
                    close_price = last_row.get('close')
                    if close_price is not None and close_price > filters['max_price']:
                        passes_filter = False
                
                if passes_filter and 'min_turnover' in filters:
                    turnover = last_row.get('turnover', 0)
                    if turnover < filters['min_turnover']:
                        passes_filter = False
                
                if not passes_filter:
                    continue
            
            try:
                signals = strategy.generate_signals(df)
                
                if not signals:
                    continue
                
                last_signal = signals[-1]
                last_date = df['date'].iloc[-1] if 'date' in df.columns else df.index[-1]
                
                if isinstance(last_date, str):
                    last_date = pd.to_datetime(last_date)
                
                if last_signal.datetime.date() == last_date.date():
                    result = {
                        'symbol': symbol,
                        'name': name,
                        'market': market,
                        'date': last_signal.datetime,
                        'price': last_signal.price,
                        'signal_type': last_signal.signal_type.value,
                        'strength': last_signal.strength.value,
                        'reason': last_signal.reason,
                        'confidence': last_signal.confidence,
                        'metadata': last_signal.metadata
                    }
                    results.append(result)
                    
                    if max_results and len(results) >= max_results:
                        if show_progress:
                            print(f"  已达到最大结果数量 {max_results}，停止扫描")
                        break
            except Exception as e:
                pass
        
        if show_progress:
            print(f"  扫描完成: 共找到 {len(results)} 只突破股票")
        
        return results
    
    def scan_latest(self, strategy: BaseStrategy, period: str = 'daily',
                    min_data_days: int = 60, save_config: bool = True,
                    config_dir: str = None, max_results: int = None,
                    show_progress: bool = True,
                    filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        扫描所有股票，找出最新一根K线满足策略条件的股票
        
        注意：此方法从数据目录获取股票列表，推荐使用 scan_stocks 方法传入股票列表
        
        Args:
            strategy: 策略实例
            period: K线周期
            min_data_days: 最小数据天数要求
            save_config: 是否保存结果到配置文件
            config_dir: 配置文件目录，默认为 data_dir 同级的 config 目录
            max_results: 最大结果数量，None表示不限制
            show_progress: 是否显示进度信息
            filters: 过滤条件，如 {'min_volume': 1000000, 'min_price': 5}
            
        Returns:
            List[Dict]: 满足条件的股票列表
        """
        stocks = self._get_stock_list_from_dir()
        results = self.scan_stocks(
            stocks=stocks,
            strategy=strategy,
            period=period,
            min_data_days=min_data_days,
            max_results=max_results,
            show_progress=show_progress,
            filters=filters
        )
        
        if save_config and results:
            self._save_results_to_config(results, config_dir)
        
        return results
    
    def _get_stock_list_from_dir(self) -> List[Dict[str, str]]:
        """从数据目录获取所有有数据的股票列表"""
        stocks = []
        
        if not os.path.exists(self.data_dir):
            return stocks
        
        for item in os.listdir(self.data_dir):
            item_path = os.path.join(self.data_dir, item)
            if os.path.isdir(item_path):
                if item.startswith('CN_'):
                    symbol = item.replace('CN_', '')
                    market = 'A股'
                elif item.startswith('US_'):
                    symbol = item.replace('US_', '')
                    market = '美股'
                elif item.startswith('HK_'):
                    symbol = item.replace('HK_', '')
                    market = '港股'
                else:
                    continue
                
                stocks.append({
                    'symbol': symbol,
                    'name': '',
                    'market': market
                })
        
        return stocks
    
    def _save_results_to_config(self, results: List[Dict[str, Any]], config_dir: str = None):
        """
        保存扫描结果到配置文件
        
        Args:
            results: 扫描结果列表
            config_dir: 配置文件目录
        """
        try:
            stocks = []
            for r in results:
                stocks.append({
                    'symbol': r['symbol'],
                    'name': r.get('name', r['symbol']),
                    'market': r['market']
                })
            
            config_data = {
                'stocks': stocks,
                'refresh_interval': 5
            }
            
            if config_dir is None:
                config_dir = os.path.join(os.path.dirname(self.data_dir), 'config')
            
            if not os.path.exists(config_dir):
                os.makedirs(config_dir)
            
            filename = f"stocks_config_break_{datetime.now().strftime('%Y%m%d')}.json"
            filepath = os.path.join(config_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, ensure_ascii=False, indent=4)
            
            print(f"扫描结果已保存到: {filepath}")
            
        except Exception as e:
            print(f"保存扫描结果失败: {e}")
    
    def scan_breakout_stocks(self, lookback_start: int = 5, lookback_end: int = 50,
                             confirm_days: int = 4, period: str = 'daily',
                             max_results: int = None) -> List[Dict[str, Any]]:
        """
        扫描突破股票的便捷方法
        
        Args:
            lookback_start: 回溯起始天数
            lookback_end: 回溯结束天数
            confirm_days: 确认天数
            period: K线周期
            max_results: 最大结果数量
            
        Returns:
            List[Dict]: 突破股票列表
        """
        strategy = HighBreakoutStrategy(
            lookback_start=lookback_start,
            lookback_end=lookback_end,
            confirm_days=confirm_days
        )
        
        return self.scan_latest(strategy, period, max_results=max_results)
    
    def scan_with_filter(self, strategy: BaseStrategy, period: str = 'daily',
                         filters: Dict[str, Any] = None,
                         max_results: int = None) -> List[Dict[str, Any]]:
        """
        带过滤条件的扫描
        
        Args:
            strategy: 策略实例
            period: K线周期
            filters: 过滤条件，如 {'min_volume': 1000000, 'min_price': 5}
            max_results: 最大结果数量
            
        Returns:
            List[Dict]: 满足条件的股票列表
        """
        return self.scan_latest(strategy, period, filters=filters, max_results=max_results)


def scan_today_breakout(data_dir: str = 'data/kline_data',
                        lookback_start: int = 5,
                        lookback_end: int = 50,
                        confirm_days: int = 4,
                        filters: Dict[str, Any] = None,
                        max_results: int = 100) -> pd.DataFrame:
    """
    扫描今日突破股票的便捷函数
    
    Args:
        data_dir: K线数据目录
        lookback_start: 回溯起始天数
        lookback_end: 回溯结束天数
        confirm_days: 确认天数
        filters: 过滤条件
        max_results: 最大结果数量，默认100
        
    Returns:
        DataFrame: 突破股票列表
    """
    scanner = StockScanner(data_dir=data_dir)
    
    strategy = HighBreakoutStrategy(
        lookback_start=lookback_start,
        lookback_end=lookback_end,
        confirm_days=confirm_days
    )
    
    if filters:
        results = scanner.scan_with_filter(strategy, filters=filters, max_results=max_results)
    else:
        results = scanner.scan_latest(strategy, period='daily', max_results=max_results)
    
    if not results:
        print("未找到满足条件的股票")
        return pd.DataFrame()
    
    df = pd.DataFrame(results)
    
    df = df.sort_values('date', ascending=False).reset_index(drop=True)
    
    return df


if __name__ == "__main__":
    print("=" * 60)
    print("股票突破扫描器")
    print("=" * 60)
    
    results = scan_today_breakout(
        data_dir='data/kline_data',
        lookback_start=5,
        lookback_end=50,
        confirm_days=4,
        max_results=100
    )
    
    if not results.empty:
        print(f"\n找到 {len(results)} 只突破股票:\n")
        
        for _, row in results.iterrows():
            print(f"股票: {row['symbol']} ({row['market']})")
            print(f"  日期: {row['date'].strftime('%Y-%m-%d')}")
            print(f"  价格: {row['price']:.2f}")
            print(f"  原因: {row['reason']}")
            print(f"  置信度: {row['confidence']:.2%}")
            print()
    else:
        print("\n今日未发现突破股票")
