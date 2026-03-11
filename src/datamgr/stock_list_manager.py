import os
from .store import StockListStore
from .cache import StockListCache


class StockListManager:
    """
    股票列表管理器
    
    功能:
    1. 管理各市场的股票基础信息列表（代码、名称）
    2. 提供股票搜索功能
    3. 管理股票列表缓存
    
    数据文件:
    data/
    ├── cn_stock_list.csv    # A股股票列表
    ├── us_stock_list.csv    # 美股股票列表 (可选)
    └── hk_stock_list.csv    # 港股股票列表 (可选)
    """
    
    MARKETS = ['A股', '美股', '港股']
    
    def __init__(self, data_dir=None):
        if data_dir is None:
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            data_dir = os.path.join(project_root, 'data')
        
        self.store = StockListStore(data_dir)
        self.cache = StockListCache()
    
    def get_stock_list(self, market='A股'):
        """
        获取股票列表
        
        Args:
            market: 市场 (A股/美股/港股)
        
        Returns:
            list: 股票列表，每项包含 code, name
        """
        cached = self.cache.get_stock_list(market)
        if cached is not None:
            return cached
        
        df = self.store.load(market)
        if df.empty:
            return []
        
        stocks = df.to_dict('records')
        self.cache.set_stock_list(market, stocks)
        return stocks
    
    def get_stock_list_df(self, market='A股'):
        """
        获取股票列表 (DataFrame格式)
        
        Args:
            market: 市场
        
        Returns:
            DataFrame: 股票列表
        """
        return self.store.load(market)
    
    def save_stock_list(self, market, data):
        """
        保存股票列表
        
        Args:
            market: 市场
            data: DataFrame 或 list 数据
        
        Returns:
            bool: 是否成功
        """
        success = self.store.save(market, data)
        if success:
            self.cache.delete_stock_list(market)
        return success
    
    def search(self, keyword, market='A股'):
        """
        搜索股票
        
        Args:
            keyword: 搜索关键词（代码或名称）
            market: 市场
        
        Returns:
            list: 匹配的股票列表
        """
        df = self.store.search(keyword, market)
        if df.empty:
            return []
        return df.to_dict('records')
    
    def get_stock_name(self, code, market='A股'):
        """
        根据代码获取股票名称
        
        Args:
            code: 股票代码
            market: 市场
        
        Returns:
            str: 股票名称，未找到返回 None
        """
        return self.store.get_stock_name(code, market)
    
    def get_stock_code(self, name, market='A股'):
        """
        根据名称获取股票代码
        
        Args:
            name: 股票名称
            market: 市场
        
        Returns:
            str: 股票代码，未找到返回 None
        """
        return self.store.get_stock_code(name, market)
    
    def get_count(self, market='A股'):
        """
        获取股票数量
        
        Args:
            market: 市场
        
        Returns:
            int: 股票数量
        """
        return self.store.get_count(market)
    
    def exists(self, market='A股'):
        """
        检查股票列表是否存在
        """
        return self.store.exists(market)
    
    def list_available_markets(self):
        """
        列出所有有数据的市场
        """
        return self.store.list_all_markets()
    
    def get_all_stocks(self):
        """
        获取所有市场的股票列表
        
        Returns:
            list: 股票列表，每项包含 code, name, market
        """
        all_stocks = []
        for market in self.MARKETS:
            if self.exists(market):
                stocks = self.get_stock_list(market)
                for stock in stocks:
                    all_stocks.append({
                        'code': stock.get('code'),
                        'name': stock.get('name'),
                        'market': market
                    })
        return all_stocks
    
    def clear_cache(self):
        """
        清空内存缓存
        """
        self.cache.clear()
