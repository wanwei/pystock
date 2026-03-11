from .base_cache import BaseCache


class StockListCache(BaseCache):
    """
    股票列表缓存类
    
    缓存股票基础信息列表
    """
    
    def __init__(self, max_size=10):
        super().__init__(max_size)
    
    def build_key(self, market):
        return f"stock_list_{market}"
    
    def get_stock_list(self, market):
        key = self.build_key(market)
        return self.get(key)
    
    def set_stock_list(self, market, data):
        key = self.build_key(market)
        self.set(key, data)
    
    def delete_stock_list(self, market):
        key = self.build_key(market)
        self.delete(key)
