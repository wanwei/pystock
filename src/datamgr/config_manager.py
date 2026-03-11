import os
from .store import ConfigStore
from .cache import ConfigCache


class ConfigManager:
    """
    配置数据管理器
    
    功能:
    1. 管理股票配置列表
    2. 管理刷新间隔等配置项
    3. 管理配置缓存
    
    目录结构:
    config/
    └── stocks_config.json
    """
    
    def __init__(self, config_dir=None):
        if config_dir is None:
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            config_dir = os.path.join(project_root, 'config')
        
        self.store = ConfigStore(config_dir)
        self.cache = ConfigCache()
    
    def load_config(self):
        """
        从配置文件加载配置
        
        Returns:
            dict: 配置内容，包含 stocks 列表和 refresh_interval
        """
        cached = self.cache.get_config()
        if cached is not None:
            return cached
        
        config = self.store.load()
        self.cache.set_config(config)
        return config
    
    def save_config(self, config):
        """
        保存配置到文件
        
        Args:
            config: 配置字典
        
        Returns:
            bool: 是否成功
        """
        success = self.store.save(None, config)
        if success:
            self.cache.set_config(config)
        return success
    
    def get_stock_list(self):
        """
        获取股票列表
        
        Returns:
            list: 股票列表，每项包含 symbol, name, market
        """
        config = self.load_config()
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
        success = self.store.add_stock(symbol, name, market)
        if success:
            self.cache.invalidate()
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
        success = self.store.remove_stock(symbol, market)
        if success:
            self.cache.invalidate()
        return success
    
    def get_refresh_interval(self):
        """
        获取刷新间隔
        
        Returns:
            int: 刷新间隔（秒）
        """
        config = self.load_config()
        return config.get('refresh_interval', 5)
    
    def set_refresh_interval(self, interval):
        """
        设置刷新间隔
        
        Args:
            interval: 刷新间隔（秒）
        
        Returns:
            bool: 是否成功
        """
        return self.store.set_refresh_interval(interval)
    
    def clear_cache(self):
        """
        清空内存缓存
        """
        self.cache.clear()
