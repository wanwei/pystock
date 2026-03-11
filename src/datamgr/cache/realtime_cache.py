from .base_cache import BaseCache


class RealtimeCache(BaseCache):
    """
    即时数据缓存类
    
    缓存键格式: {market_prefix}_{symbol}
    例如: CN_600519
    """
    
    def __init__(self, max_size=200):
        super().__init__(max_size)
    
    def build_key(self, symbol, market):
        """
        构建即时数据缓存键
        
        Args:
            symbol: 股票代码
            market: 市场
        
        Returns:
            str: 缓存键
        """
        prefix = self._get_market_prefix(market)
        return f"{prefix}_{symbol}"
    
    def _get_market_prefix(self, market):
        if market in ['A股', 'CN', 'cn']:
            return 'CN'
        elif market in ['美股', 'US', 'us']:
            return 'US'
        elif market in ['港股', 'HK', 'hk']:
            return 'HK'
        return 'CN'
    
    def get_realtime(self, symbol, market):
        """
        获取即时数据缓存
        """
        key = self.build_key(symbol, market)
        return self.get(key)
    
    def set_realtime(self, symbol, market, data):
        """
        设置即时数据缓存
        """
        key = self.build_key(symbol, market)
        self.set(key, data)
    
    def exists_realtime(self, symbol, market):
        """
        检查即时数据缓存是否存在
        """
        key = self.build_key(symbol, market)
        return self.exists(key)
    
    def delete_realtime(self, symbol, market):
        """
        删除即时数据缓存
        """
        key = self.build_key(symbol, market)
        self.delete(key)
