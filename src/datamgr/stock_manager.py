import os
import json
import pandas as pd
from datetime import datetime
from threading import Lock


class StockDataManager:
    """
    股票数据管理器
    
    管理两类数据:
    1. K线数据 - 历史数据，按周期存储
    2. 即时数据 - 实时数据，持续追加
    
    目录结构:
    data/
    ├── realtime/           # 即时数据目录
    │   ├── CN_600519.csv   # 每只股票一个文件
    │   └── ...
    └── kline_data/         # K线数据目录
        ├── CN_600519/
        │   ├── daily.csv
        │   ├── 1hour.csv
        │   └── ...
        └── ...
    """
    
    REALTIME_COLUMNS = [
        'datetime', 'symbol', 'name', 'market',
        'price', 'open', 'high', 'low', 'prev_close',
        'change', 'change_pct', 'volume', 'amount'
    ]
    
    KLINE_COLUMNS = [
        'date', 'open', 'close', 'high', 'low',
        'volume', 'amount', 'amplitude', 'change_pct', 'change', 'turnover'
    ]
    
    PERIODS = ['1min', '5min', '15min', '1hour', 'daily']
    
    DEFAULT_CONFIG = {
        "stocks": [],
        "refresh_interval": 5
    }
    
    def __init__(self, base_dir='data', config_path=None):
        self.base_dir = base_dir
        self.realtime_dir = os.path.join(base_dir, 'realtime')
        self.kline_dir = os.path.join(base_dir, 'kline_data')
        
        if config_path:
            self.config_path = config_path
        else:
            self.config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'config', 'stocks_config.json')
        
        self._realtime_cache = {}
        self._kline_cache = {}
        self._config_cache = None
        self._lock = Lock()
        
        self._ensure_directories()
    
    def _ensure_directories(self):
        if not os.path.exists(self.realtime_dir):
            os.makedirs(self.realtime_dir)
        if not os.path.exists(self.kline_dir):
            os.makedirs(self.kline_dir)
    
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
    
    def _get_realtime_filepath(self, symbol, market):
        stock_key = self._get_stock_key(symbol, market)
        return os.path.join(self.realtime_dir, f"{stock_key}.csv")
    
    def _get_kline_dirpath(self, symbol, market):
        stock_key = self._get_stock_key(symbol, market)
        return os.path.join(self.kline_dir, stock_key)
    
    def _get_kline_filepath(self, symbol, market, period):
        dirpath = self._get_kline_dirpath(symbol, market)
        return os.path.join(dirpath, f"{period}.csv")
    
    def append_realtime_data(self, symbol, market, data):
        """
        追加即时数据
        
        Args:
            symbol: 股票代码
            market: 市场 (A股/美股/港股)
            data: 即时数据字典，包含:
                - price: 当前价格
                - open: 开盘价
                - high: 最高价
                - low: 最低价
                - prev_close: 昨收价
                - change: 涨跌额
                - change_pct: 涨跌幅
                - volume: 成交量
                - amount: 成交额
                - name: 股票名称 (可选)
        
        Returns:
            bool: 是否成功
        """
        with self._lock:
            try:
                now = datetime.now()
                row = {
                    'datetime': now.strftime('%Y-%m-%d %H:%M:%S'),
                    'symbol': symbol,
                    'name': data.get('name', ''),
                    'market': market,
                    'price': data.get('price') or data.get('c'),
                    'open': data.get('open') or data.get('o'),
                    'high': data.get('high') or data.get('h'),
                    'low': data.get('low') or data.get('l'),
                    'prev_close': data.get('prev_close') or data.get('pc'),
                    'change': data.get('change') or data.get('d'),
                    'change_pct': data.get('change_pct') or data.get('dp'),
                    'volume': data.get('volume', 0),
                    'amount': data.get('amount', 0)
                }
                
                stock_key = self._get_stock_key(symbol, market)
                filepath = self._get_realtime_filepath(symbol, market)
                
                if stock_key in self._realtime_cache:
                    df = self._realtime_cache[stock_key]
                    new_row = pd.DataFrame([row])
                    df = pd.concat([df, new_row], ignore_index=True)
                else:
                    df = pd.DataFrame([row])
                
                self._realtime_cache[stock_key] = df
                
                file_exists = os.path.exists(filepath)
                df.to_csv(filepath, mode='a', header=not file_exists, index=False, encoding='utf-8')
                
                return True
                
            except Exception as e:
                print(f"追加即时数据失败 {symbol}: {e}")
                return False
    
    def get_realtime_data(self, symbol, market, limit=None):
        """
        获取即时数据
        
        Args:
            symbol: 股票代码
            market: 市场
            limit: 返回最近N条数据
        
        Returns:
            DataFrame: 即时数据
        """
        stock_key = self._get_stock_key(symbol, market)
        
        if stock_key in self._realtime_cache:
            df = self._realtime_cache[stock_key]
        else:
            filepath = self._get_realtime_filepath(symbol, market)
            if os.path.exists(filepath):
                df = pd.read_csv(filepath)
                self._realtime_cache[stock_key] = df
            else:
                df = pd.DataFrame(columns=self.REALTIME_COLUMNS)
                self._realtime_cache[stock_key] = df
        
        if limit and len(df) > limit:
            return df.tail(limit).reset_index(drop=True)
        return df.copy()
    
    def clear_realtime_data(self, symbol, market):
        """
        清空即时数据
        """
        stock_key = self._get_stock_key(symbol, market)
        filepath = self._get_realtime_filepath(symbol, market)
        
        with self._lock:
            if stock_key in self._realtime_cache:
                del self._realtime_cache[stock_key]
            if os.path.exists(filepath):
                os.remove(filepath)
    
    def save_kline_data(self, symbol, market, period, data):
        """
        保存K线数据
        
        Args:
            symbol: 股票代码
            market: 市场
            period: 周期 (1min/5min/15min/1hour/daily)
            data: K线数据列表或DataFrame
        
        Returns:
            bool: 是否成功
        """
        with self._lock:
            try:
                if isinstance(data, list):
                    df = pd.DataFrame(data)
                else:
                    df = data.copy()
                
                dirpath = self._get_kline_dirpath(symbol, market)
                if not os.path.exists(dirpath):
                    os.makedirs(dirpath)
                
                filepath = self._get_kline_filepath(symbol, market, period)
                df.to_csv(filepath, index=False, encoding='utf-8')
                
                cache_key = f"{self._get_stock_key(symbol, market)}_{period}"
                self._kline_cache[cache_key] = df
                
                print(f"K线数据已保存: {filepath} ({len(df)}条)")
                return True
                
            except Exception as e:
                print(f"保存K线数据失败 {symbol} {period}: {e}")
                return False
    
    def append_kline_data(self, symbol, market, period, data):
        """
        追加K线数据
        
        Args:
            symbol: 股票代码
            market: 市场
            period: 周期
            data: 单条K线数据字典或列表
        
        Returns:
            bool: 是否成功
        """
        with self._lock:
            try:
                if isinstance(data, list):
                    new_df = pd.DataFrame(data)
                else:
                    new_df = pd.DataFrame([data])
                
                cache_key = f"{self._get_stock_key(symbol, market)}_{period}"
                filepath = self._get_kline_filepath(symbol, market, period)
                
                if cache_key in self._kline_cache:
                    df = self._kline_cache[cache_key]
                    df = pd.concat([df, new_df], ignore_index=True)
                elif os.path.exists(filepath):
                    df = pd.read_csv(filepath)
                    df = pd.concat([df, new_df], ignore_index=True)
                else:
                    df = new_df
                
                if 'date' in df.columns:
                    df = df.drop_duplicates(subset=['date'], keep='last')
                    df = df.sort_values('date').reset_index(drop=True)
                
                self._kline_cache[cache_key] = df
                
                dirpath = self._get_kline_dirpath(symbol, market)
                if not os.path.exists(dirpath):
                    os.makedirs(dirpath)
                
                df.to_csv(filepath, index=False, encoding='utf-8')
                return True
                
            except Exception as e:
                print(f"追加K线数据失败 {symbol} {period}: {e}")
                return False
    
    def get_kline_data(self, symbol, market, period, limit=None):
        """
        获取K线数据
        
        Args:
            symbol: 股票代码
            market: 市场
            period: 周期
            limit: 返回最近N条数据
        
        Returns:
            DataFrame: K线数据
        """
        cache_key = f"{self._get_stock_key(symbol, market)}_{period}"
        
        if cache_key in self._kline_cache:
            df = self._kline_cache[cache_key]
        else:
            filepath = self._get_kline_filepath(symbol, market, period)
            if os.path.exists(filepath):
                df = pd.read_csv(filepath)
                if 'date' in df.columns:
                    df['date'] = pd.to_datetime(df['date'])
                    df = df.sort_values('date').reset_index(drop=True)
                self._kline_cache[cache_key] = df
            else:
                df = pd.DataFrame(columns=self.KLINE_COLUMNS)
                self._kline_cache[cache_key] = df
        
        if limit and len(df) > limit:
            return df.tail(limit).reset_index(drop=True)
        return df.copy()
    
    def get_latest_kline_date(self, symbol, market, period):
        """
        获取K线数据最新日期
        """
        df = self.get_kline_data(symbol, market, period)
        if df.empty or 'date' not in df.columns:
            return None
        return df['date'].max()
    
    def get_stock_info(self, symbol, market):
        """
        获取股票数据概览
        """
        stock_key = self._get_stock_key(symbol, market)
        
        info = {
            'symbol': symbol,
            'market': market,
            'kline': {},
            'realtime': {
                'count': 0,
                'latest': None
            }
        }
        
        for period in self.PERIODS:
            df = self.get_kline_data(symbol, market, period)
            if not df.empty:
                info['kline'][period] = {
                    'count': len(df),
                    'latest': df['date'].max() if 'date' in df.columns else None
                }
        
        realtime_df = self.get_realtime_data(symbol, market)
        if not realtime_df.empty:
            info['realtime']['count'] = len(realtime_df)
            info['realtime']['latest'] = realtime_df['datetime'].max()
        
        return info
    
    def list_stocks(self):
        """
        列出所有有数据的股票
        """
        stocks = set()
        
        if os.path.exists(self.realtime_dir):
            for f in os.listdir(self.realtime_dir):
                if f.endswith('.csv'):
                    stocks.add(f.replace('.csv', ''))
        
        if os.path.exists(self.kline_dir):
            for d in os.listdir(self.kline_dir):
                if os.path.isdir(os.path.join(self.kline_dir, d)):
                    stocks.add(d)
        
        return sorted(list(stocks))
    
    def clear_cache(self):
        """
        清空内存缓存
        """
        with self._lock:
            self._realtime_cache.clear()
            self._kline_cache.clear()
    
    def load_stocks_config(self):
        """
        从配置文件加载股票列表
        
        Returns:
            dict: 配置内容，包含 stocks 列表和 refresh_interval
        """
        if self._config_cache is not None:
            return self._config_cache
        
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self._config_cache = json.load(f)
                    return self._config_cache
            except Exception as e:
                print(f"加载股票配置文件失败: {e}")
                return self.DEFAULT_CONFIG.copy()
        return self.DEFAULT_CONFIG.copy()
    
    def save_stocks_config(self, config):
        """
        保存股票配置到文件
        
        Args:
            config: 配置字典
        
        Returns:
            bool: 是否成功
        """
        try:
            config_dir = os.path.dirname(self.config_path)
            if not os.path.exists(config_dir):
                os.makedirs(config_dir)
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=4)
            
            self._config_cache = config
            return True
        except Exception as e:
            print(f"保存股票配置文件失败: {e}")
            return False
    
    def get_stock_list(self):
        """
        获取股票列表
        
        Returns:
            list: 股票列表，每项包含 symbol, name, market
        """
        config = self.load_stocks_config()
        return config.get('stocks', [])
    
    def add_stock(self, symbol, name, market='A股'):
        """
        添加股票到配置
        
        Args:
            symbol: 股票代码
            name: 股票名称
            market: 市场
        
        Returns:
            bool: 是否成功
        """
        config = self.load_stocks_config()
        stocks = config.get('stocks', [])
        
        for stock in stocks:
            if stock.get('symbol') == symbol and stock.get('market') == market:
                return False
        
        stocks.append({
            'symbol': symbol,
            'name': name,
            'market': market
        })
        config['stocks'] = stocks
        
        return self.save_stocks_config(config)
    
    def remove_stock(self, symbol, market='A股'):
        """
        从配置中移除股票
        
        Args:
            symbol: 股票代码
            market: 市场
        
        Returns:
            bool: 是否成功
        """
        config = self.load_stocks_config()
        stocks = config.get('stocks', [])
        
        new_stocks = [s for s in stocks if not (s.get('symbol') == symbol and s.get('market') == market)]
        
        if len(new_stocks) == len(stocks):
            return False
        
        config['stocks'] = new_stocks
        return self.save_stocks_config(config)
    
    def get_refresh_interval(self):
        """
        获取刷新间隔
        
        Returns:
            int: 刷新间隔（秒）
        """
        config = self.load_stocks_config()
        return config.get('refresh_interval', 5)
