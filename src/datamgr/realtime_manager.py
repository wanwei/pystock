import os
from datetime import datetime
from .store import RealtimeStore
from .cache import RealtimeCache


class RealtimeManager:
    """
    即时数据管理器
    
    功能:
    1. 管理即时数据的存储和读取
    2. 管理即时数据缓存
    3. 提供即时数据的增删改查
    
    目录结构:
    data/realtime/
    ├── CN_600519.csv
    ├── US_AAPL.csv
    └── ...
    """
    
    COLUMNS = [
        'datetime', 'symbol', 'name', 'market',
        'price', 'open', 'high', 'low', 'prev_close',
        'change', 'change_pct', 'volume', 'amount'
    ]
    
    def __init__(self, data_dir=None):
        if data_dir is None:
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            data_dir = os.path.join(project_root, 'data', 'realtime')
        
        self.store = RealtimeStore(data_dir)
        self.cache = RealtimeCache()
    
    def append_data(self, symbol, market, data):
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
        
        success = self.store.append(symbol, market, row)
        if success:
            self.cache.delete_realtime(symbol, market)
        
        return success
    
    def get_data(self, symbol, market, limit=None):
        """
        获取即时数据
        
        Args:
            symbol: 股票代码
            market: 市场
            limit: 返回最近N条数据
        
        Returns:
            DataFrame: 即时数据
        """
        cached = self.cache.get_realtime(symbol, market)
        if cached is not None:
            if limit and len(cached) > limit:
                return cached.tail(limit).reset_index(drop=True)
            return cached.copy()
        
        df = self.store.load(symbol, market, limit)
        if df is not None and not df.empty:
            self.cache.set_realtime(symbol, market, df)
        return df
    
    def save_data(self, symbol, market, data):
        """
        保存即时数据（覆盖）
        
        Args:
            symbol: 股票代码
            market: 市场
            data: DataFrame 或 list 数据
        
        Returns:
            bool: 是否成功
        """
        success = self.store.save(symbol, market, data)
        if success:
            self.cache.delete_realtime(symbol, market)
        return success
    
    def clear_data(self, symbol, market):
        """
        清空即时数据
        """
        self.store.delete(symbol, market)
        self.cache.delete_realtime(symbol, market)
    
    def exists(self, symbol, market):
        """
        检查即时数据是否存在
        """
        return self.store.exists(symbol, market)
    
    def get_latest_datetime(self, symbol, market):
        """
        获取最新数据时间
        """
        return self.store.get_latest_datetime(symbol, market)
    
    def list_stocks(self):
        """
        列出所有有即时数据的股票
        """
        return self.store.list_stocks()
    
    def get_stock_name(self, symbol, market):
        """
        从数据文件获取股票名称
        """
        try:
            df = self.get_data(symbol, market, limit=1)
            if not df.empty and 'name' in df.columns:
                name = df['name'].iloc[0]
                if name and name != symbol:
                    return name
        except:
            pass
        return symbol
    
    def clear_cache(self):
        """
        清空内存缓存
        """
        self.cache.clear()
