import os
import pandas as pd
from .base_store import BaseStore


class RealtimeStore(BaseStore):
    """
    即时数据存储类
    
    目录结构:
    base_dir/
    ├── CN_600519.csv
    ├── US_AAPL.csv
    └── ...
    """
    
    COLUMNS = [
        'datetime', 'symbol', 'name', 'market',
        'price', 'open', 'high', 'low', 'prev_close',
        'change', 'change_pct', 'volume', 'amount'
    ]
    
    def __init__(self, base_dir):
        super().__init__(base_dir)
    
    def _get_market_prefix(self, market):
        if market in ['A股', 'CN', 'cn']:
            return 'CN'
        elif market in ['美股', 'US', 'us']:
            return 'US'
        elif market in ['港股', 'HK', 'hk']:
            return 'HK'
        return 'CN'
    
    def _get_stock_key(self, symbol, market):
        prefix = self._get_market_prefix(market)
        return f"{prefix}_{symbol}"
    
    def get_filepath(self, symbol, market):
        stock_key = self._get_stock_key(symbol, market)
        return os.path.join(self.base_dir, f"{stock_key}.csv")
    
    def save(self, symbol, market, data):
        """
        保存即时数据
        
        Args:
            symbol: 股票代码
            market: 市场
            data: DataFrame 数据
        
        Returns:
            bool: 是否成功
        """
        with self._lock:
            try:
                if isinstance(data, list):
                    df = pd.DataFrame(data)
                else:
                    df = data.copy()
                
                filepath = self.get_filepath(symbol, market)
                df.to_csv(filepath, index=False, encoding='utf-8')
                return True
                
            except Exception as e:
                print(f"保存即时数据失败 {symbol}: {e}")
                return False
    
    def load(self, symbol, market, limit=None):
        """
        加载即时数据
        
        Args:
            symbol: 股票代码
            market: 市场
            limit: 返回最近N条数据
        
        Returns:
            DataFrame: 即时数据
        """
        filepath = self.get_filepath(symbol, market)
        
        if not os.path.exists(filepath):
            return pd.DataFrame(columns=self.COLUMNS)
        
        try:
            df = pd.read_csv(filepath)
            
            if limit and len(df) > limit:
                return df.tail(limit).reset_index(drop=True)
            return df
            
        except Exception as e:
            print(f"加载即时数据失败 {symbol}: {e}")
            return pd.DataFrame(columns=self.COLUMNS)
    
    def exists(self, symbol, market):
        """
        检查即时数据是否存在
        """
        filepath = self.get_filepath(symbol, market)
        return os.path.exists(filepath)
    
    def delete(self, symbol, market):
        """
        删除即时数据
        """
        with self._lock:
            try:
                filepath = self.get_filepath(symbol, market)
                if os.path.exists(filepath):
                    os.remove(filepath)
                return True
            except Exception as e:
                print(f"删除即时数据失败 {symbol}: {e}")
                return False
    
    def append(self, symbol, market, data):
        """
        追加即时数据
        
        Args:
            symbol: 股票代码
            market: 市场
            data: 单条数据字典
        
        Returns:
            bool: 是否成功
        """
        with self._lock:
            try:
                new_df = pd.DataFrame([data])
                filepath = self.get_filepath(symbol, market)
                
                file_exists = os.path.exists(filepath)
                new_df.to_csv(filepath, mode='a', header=not file_exists, index=False, encoding='utf-8')
                return True
                
            except Exception as e:
                print(f"追加即时数据失败 {symbol}: {e}")
                return False
    
    def get_latest_datetime(self, symbol, market):
        """
        获取最新数据时间
        """
        df = self.load(symbol, market)
        if df.empty or 'datetime' not in df.columns:
            return None
        return df['datetime'].max()
    
    def list_stocks(self):
        """
        列出所有有即时数据的股票
        """
        stocks = []
        if not os.path.exists(self.base_dir):
            return stocks
        
        for f in os.listdir(self.base_dir):
            if f.endswith('.csv'):
                stocks.append(f.replace('.csv', ''))
        
        return sorted(stocks)
