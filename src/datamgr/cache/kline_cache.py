from .base_cache import BaseCache


class KLineCache(BaseCache):
    """
    K线数据缓存类
    
    缓存键格式: {market_prefix}_{symbol}_{period}
    例如: CN_600519_daily
    """
    
    def __init__(self, max_size=500):
        super().__init__(max_size)
    
    def build_key(self, symbol, market, period):
        """
        构建K线缓存键
        
        Args:
            symbol: 股票代码
            market: 市场
            period: 周期
        
        Returns:
            str: 缓存键
        """
        prefix = self._get_market_prefix(market)
        return f"{prefix}_{symbol}_{period}"
    
    def _get_market_prefix(self, market):
        if market in ['A股', 'CN', 'cn']:
            return 'CN'
        elif market in ['美股', 'US', 'us']:
            return 'US'
        elif market in ['港股', 'HK', 'hk']:
            return 'HK'
        return 'CN'
    
    def get_kline(self, symbol, market, period):
        """
        获取K线缓存数据
        """
        key = self.build_key(symbol, market, period)
        return self.get(key)
    
    def set_kline(self, symbol, market, period, data):
        """
        设置K线缓存数据
        """
        key = self.build_key(symbol, market, period)
        self.set(key, data)
    
    def exists_kline(self, symbol, market, period):
        """
        检查K线缓存是否存在
        """
        key = self.build_key(symbol, market, period)
        return self.exists(key)
    
    def delete_kline(self, symbol, market, period):
        """
        删除K线缓存
        """
        key = self.build_key(symbol, market, period)
        self.delete(key)
    
    def delete_stock(self, symbol, market):
        """
        删除某只股票的所有周期缓存
        """
        prefix = self._get_market_prefix(market)
        keys_to_delete = [k for k in self.keys() if k.startswith(f"{prefix}_{symbol}_")]
        for key in keys_to_delete:
            self.delete(key)
