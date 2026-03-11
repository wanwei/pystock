import os
import pandas as pd
from .base_store import BaseStore


class KLineStore(BaseStore):
    """
    K线数据存储类
    
    目录结构:
    base_dir/
    ├── CN_600519/
    │   ├── daily.csv
    │   ├── 1hour.csv
    │   ├── 1min.csv
    │   └── ...
    └── US_AAPL/
        └── daily.csv
    """
    
    COLUMNS = [
        'date', 'open', 'close', 'high', 'low',
        'volume', 'amount', 'amplitude', 'change_pct', 'change', 'turnover'
    ]
    
    PERIODS = ['1min', '5min', '15min', '1hour', 'daily']
    
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
    
    def _get_stock_dir(self, symbol, market):
        stock_key = self._get_stock_key(symbol, market)
        return os.path.join(self.base_dir, stock_key)
    
    def get_filepath(self, symbol, market, period):
        stock_dir = self._get_stock_dir(symbol, market)
        return os.path.join(stock_dir, f"{period}.csv")
    
    def save(self, symbol, market, period, data):
        """
        保存K线数据
        
        Args:
            symbol: 股票代码
            market: 市场
            period: 周期
            data: DataFrame 或 list 数据
        
        Returns:
            bool: 是否成功
        """
        with self._lock:
            try:
                if isinstance(data, list):
                    df = pd.DataFrame(data)
                else:
                    df = data.copy()
                
                stock_dir = self._get_stock_dir(symbol, market)
                if not os.path.exists(stock_dir):
                    os.makedirs(stock_dir)
                
                filepath = self.get_filepath(symbol, market, period)
                df.to_csv(filepath, index=False, encoding='utf-8')
                
                return True
                
            except Exception as e:
                print(f"保存K线数据失败 {symbol} {period}: {e}")
                return False
    
    def load(self, symbol, market, period, limit=None):
        """
        加载K线数据
        
        Args:
            symbol: 股票代码
            market: 市场
            period: 周期
            limit: 返回最近N条数据
        
        Returns:
            DataFrame: K线数据
        """
        filepath = self.get_filepath(symbol, market, period)
        
        if not os.path.exists(filepath):
            return pd.DataFrame(columns=self.COLUMNS)
        
        try:
            df = pd.read_csv(filepath)
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])
                df = df.sort_values('date').reset_index(drop=True)
            
            if limit and len(df) > limit:
                return df.tail(limit).reset_index(drop=True)
            return df
            
        except Exception as e:
            print(f"加载K线数据失败 {symbol} {period}: {e}")
            return pd.DataFrame(columns=self.COLUMNS)
    
    def exists(self, symbol, market, period):
        """
        检查K线数据是否存在
        """
        filepath = self.get_filepath(symbol, market, period)
        return os.path.exists(filepath)
    
    def delete(self, symbol, market, period=None):
        """
        删除K线数据
        
        Args:
            symbol: 股票代码
            market: 市场
            period: 周期，None表示删除该股票所有周期数据
        """
        with self._lock:
            try:
                if period:
                    filepath = self.get_filepath(symbol, market, period)
                    if os.path.exists(filepath):
                        os.remove(filepath)
                else:
                    stock_dir = self._get_stock_dir(symbol, market)
                    if os.path.exists(stock_dir):
                        import shutil
                        shutil.rmtree(stock_dir)
                return True
            except Exception as e:
                print(f"删除K线数据失败 {symbol}: {e}")
                return False
    
    def append(self, symbol, market, period, data):
        """
        追加K线数据
        
        Args:
            symbol: 股票代码
            market: 市场
            period: 周期
            data: 单条或列表数据
        
        Returns:
            bool: 是否成功
        """
        with self._lock:
            try:
                if isinstance(data, list):
                    new_df = pd.DataFrame(data)
                else:
                    new_df = pd.DataFrame([data])
                
                filepath = self.get_filepath(symbol, market, period)
                
                if os.path.exists(filepath):
                    old_df = pd.read_csv(filepath)
                    df = pd.concat([old_df, new_df], ignore_index=True)
                else:
                    stock_dir = self._get_stock_dir(symbol, market)
                    if not os.path.exists(stock_dir):
                        os.makedirs(stock_dir)
                    df = new_df
                
                if 'date' in df.columns:
                    df = df.drop_duplicates(subset=['date'], keep='last')
                    df = df.sort_values('date').reset_index(drop=True)
                
                df.to_csv(filepath, index=False, encoding='utf-8')
                return True
                
            except Exception as e:
                print(f"追加K线数据失败 {symbol} {period}: {e}")
                return False
    
    def get_latest_date(self, symbol, market, period):
        """
        获取K线数据最新日期
        """
        df = self.load(symbol, market, period)
        if df.empty or 'date' not in df.columns:
            return None
        return df['date'].max()
    
    def get_data_info(self, symbol, market, period):
        """
        获取K线数据信息
        """
        filepath = self.get_filepath(symbol, market, period)
        
        if not os.path.exists(filepath):
            return {
                'exists': False,
                'count': 0,
                'latest_date': None,
                'filepath': None
            }
        
        try:
            df = pd.read_csv(filepath)
            count = len(df)
            latest_date = df['date'].max() if 'date' in df.columns else None
            
            return {
                'exists': True,
                'count': count,
                'latest_date': latest_date,
                'filepath': filepath
            }
        except Exception as e:
            return {
                'exists': False,
                'count': 0,
                'latest_date': None,
                'filepath': None
            }
    
    def list_stocks(self):
        """
        列出所有有K线数据的股票
        """
        stocks = []
        if not os.path.exists(self.base_dir):
            return stocks
        
        for item in os.listdir(self.base_dir):
            item_path = os.path.join(self.base_dir, item)
            if os.path.isdir(item_path):
                stocks.append(item)
        
        return sorted(stocks)
