import os
from datetime import datetime
from .store import KLineStore, RealtimeStore, ConfigStore
from .cache import KLineCache, RealtimeCache, ConfigCache


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
    
    def __init__(self, base_dir=None, config_path=None):
        if base_dir is None:
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            base_dir = os.path.join(project_root, 'data')
        
        self.base_dir = base_dir
        self.realtime_dir = os.path.join(base_dir, 'realtime')
        self.kline_dir = os.path.join(base_dir, 'kline_data')
        
        if config_path:
            self.config_path = config_path
            config_dir = os.path.dirname(config_path)
        else:
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            config_dir = os.path.join(project_root, 'config')
            self.config_path = os.path.join(config_dir, 'stocks_config.json')
        
        self.kline_store = KLineStore(self.kline_dir)
        self.realtime_store = RealtimeStore(self.realtime_dir)
        self.config_store = ConfigStore(config_dir)
        
        self.kline_cache = KLineCache()
        self.realtime_cache = RealtimeCache()
        self.config_cache = ConfigCache()
    
    def append_realtime_data(self, symbol, market, data):
        """
        追加即时数据
        
        Args:
            symbol: 股票代码
            market: 市场 (A股/美股/港股)
            data: 即时数据字典
        
        Returns:
            bool: 是否成功
        """
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
        
        success = self.realtime_store.append(symbol, market, row)
        if success:
            self.realtime_cache.delete_realtime(symbol, market)
        
        return success
    
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
        cached = self.realtime_cache.get_realtime(symbol, market)
        if cached is not None:
            if limit and len(cached) > limit:
                return cached.tail(limit).reset_index(drop=True)
            return cached.copy()
        
        df = self.realtime_store.load(symbol, market, limit)
        if df is not None and not df.empty:
            self.realtime_cache.set_realtime(symbol, market, df)
        return df
    
    def clear_realtime_data(self, symbol, market):
        """
        清空即时数据
        """
        self.realtime_store.delete(symbol, market)
        self.realtime_cache.delete_realtime(symbol, market)
    
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
        success = self.kline_store.save(symbol, market, period, data)
        if success:
            self.kline_cache.delete_kline(symbol, market, period)
            print(f"K线数据已保存: {symbol} {period} ({len(data) if hasattr(data, '__len__') else 0}条)")
        return success
    
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
        success = self.kline_store.append(symbol, market, period, data)
        if success:
            self.kline_cache.delete_kline(symbol, market, period)
        return success
    
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
        cached = self.kline_cache.get_kline(symbol, market, period)
        if cached is not None:
            if limit and len(cached) > limit:
                return cached.tail(limit).reset_index(drop=True)
            return cached.copy()
        
        df = self.kline_store.load(symbol, market, period, limit)
        if df is not None and not df.empty:
            self.kline_cache.set_kline(symbol, market, period, df)
        return df
    
    def get_latest_kline_date(self, symbol, market, period):
        """
        获取K线数据最新日期
        """
        return self.kline_store.get_latest_date(symbol, market, period)
    
    def get_stock_info(self, symbol, market):
        """
        获取股票数据概览
        """
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
        
        realtime_stocks = self.realtime_store.list_stocks()
        stocks.update(realtime_stocks)
        
        kline_stocks = self.kline_store.list_stocks()
        stocks.update(kline_stocks)
        
        return sorted(list(stocks))
    
    def clear_cache(self):
        """
        清空内存缓存
        """
        self.kline_cache.clear()
        self.realtime_cache.clear()
        self.config_cache.clear()
    
    def load_stocks_config(self):
        """
        从配置文件加载股票列表
        
        Returns:
            dict: 配置内容，包含 stocks 列表和 refresh_interval
        """
        cached = self.config_cache.get_config()
        if cached is not None:
            return cached
        
        config = self.config_store.load()
        self.config_cache.set_config(config)
        return config
    
    def save_stocks_config(self, config):
        """
        保存股票配置到文件
        
        Args:
            config: 配置字典
        
        Returns:
            bool: 是否成功
        """
        success = self.config_store.save(None, config)
        if success:
            self.config_cache.set_config(config)
        return success
    
    def get_stock_list(self):
        """
        获取股票列表（从现有K线数据目录读取）
        
        Returns:
            list: 股票列表，每项包含 symbol, name, market
        """
        stocks = []
        stock_keys = self.list_stocks()
        
        for stock_key in stock_keys:
            parts = stock_key.split('_', 1)
            if len(parts) == 2:
                prefix, symbol = parts
                if prefix == 'CN':
                    market = 'A股'
                elif prefix == 'US':
                    market = '美股'
                elif prefix == 'HK':
                    market = '港股'
                else:
                    market = 'A股'
                
                name = self._get_stock_name(symbol, market)
                stocks.append({
                    'symbol': symbol,
                    'name': name,
                    'market': market
                })
        
        return stocks
    
    def _get_stock_name(self, symbol, market):
        """
        从数据文件获取股票名称
        """
        try:
            df = self.get_realtime_data(symbol, market, limit=1)
            if not df.empty and 'name' in df.columns:
                name = df['name'].iloc[0]
                if name and name != symbol:
                    return name
        except:
            pass
        return symbol
    
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
        success = self.config_store.add_stock(symbol, name, market)
        if success:
            self.config_cache.invalidate()
        return success
    
    def remove_stock(self, symbol, market='A股'):
        """
        从配置中移除股票
        
        Args:
            symbol: 股票代码
            market: 市场
        
        Returns:
            bool: 是否成功
        """
        success = self.config_store.remove_stock(symbol, market)
        if success:
            self.config_cache.invalidate()
        return success
    
    def get_refresh_interval(self):
        """
        获取刷新间隔
        
        Returns:
            int: 刷新间隔（秒）
        """
        config = self.load_stocks_config()
        return config.get('refresh_interval', 5)
