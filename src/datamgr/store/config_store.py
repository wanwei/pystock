import os
import json
from .base_store import BaseStore


class ConfigStore(BaseStore):
    """
    配置数据存储类
    
    目录结构:
    base_dir/
    └── stocks_config.json
    """
    
    DEFAULT_CONFIG = {
        "stocks": [],
        "refresh_interval": 5
    }
    
    def __init__(self, base_dir, config_filename='stocks_config.json'):
        self.config_filename = config_filename
        super().__init__(base_dir)
    
    def get_filepath(self, key=None):
        return os.path.join(self.base_dir, self.config_filename)
    
    def save(self, key, data, **kwargs):
        """
        保存配置数据
        
        Args:
            key: 配置键 (未使用)
            data: 配置数据字典
        
        Returns:
            bool: 是否成功
        """
        with self._lock:
            try:
                filepath = self.get_filepath()
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=4)
                return True
            except Exception as e:
                print(f"保存配置文件失败: {e}")
                return False
    
    def load(self, key=None, **kwargs):
        """
        加载配置数据
        
        Args:
            key: 配置键 (未使用)
        
        Returns:
            dict: 配置数据
        """
        filepath = self.get_filepath()
        
        if not os.path.exists(filepath):
            return self.DEFAULT_CONFIG.copy()
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"加载配置文件失败: {e}")
            return self.DEFAULT_CONFIG.copy()
    
    def exists(self, key=None, **kwargs):
        """
        检查配置文件是否存在
        """
        filepath = self.get_filepath()
        return os.path.exists(filepath)
    
    def delete(self, key=None, **kwargs):
        """
        删除配置文件
        """
        with self._lock:
            try:
                filepath = self.get_filepath()
                if os.path.exists(filepath):
                    os.remove(filepath)
                return True
            except Exception as e:
                print(f"删除配置文件失败: {e}")
                return False
    
    def get_stock_list(self):
        """
        获取股票列表
        """
        config = self.load()
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
        with self._lock:
            try:
                config = self.load()
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
                
                return self.save(None, config)
                
            except Exception as e:
                print(f"添加股票失败: {e}")
                return False
    
    def remove_stock(self, symbol, market='A股'):
        """
        从配置中移除股票
        
        Args:
            symbol: 股票代码
            market: 市场
        
        Returns:
            bool: 是否成功
        """
        with self._lock:
            try:
                config = self.load()
                stocks = config.get('stocks', [])
                
                new_stocks = [s for s in stocks if not (s.get('symbol') == symbol and s.get('market') == market)]
                
                if len(new_stocks) == len(stocks):
                    return False
                
                config['stocks'] = new_stocks
                return self.save(None, config)
                
            except Exception as e:
                print(f"移除股票失败: {e}")
                return False
    
    def get_refresh_interval(self):
        """
        获取刷新间隔
        """
        config = self.load()
        return config.get('refresh_interval', 5)
    
    def set_refresh_interval(self, interval):
        """
        设置刷新间隔
        """
        with self._lock:
            try:
                config = self.load()
                config['refresh_interval'] = interval
                return self.save(None, config)
            except Exception as e:
                print(f"设置刷新间隔失败: {e}")
                return False
    
    def clear_stocks(self):
        """
        清空股票列表
        
        Returns:
            bool: 是否成功
        """
        with self._lock:
            try:
                config = self.load()
                config['stocks'] = []
                return self.save(None, config)
            except Exception as e:
                print(f"清空股票列表失败: {e}")
                return False
    
    def add_stocks_batch(self, stocks_list):
        """
        批量添加股票到配置
        
        Args:
            stocks_list: 股票列表，每项包含 symbol, name, market
        
        Returns:
            int: 成功添加的数量
        """
        with self._lock:
            try:
                config = self.load()
                existing_stocks = config.get('stocks', [])
                existing_keys = {(s.get('symbol'), s.get('market')) for s in existing_stocks}
                
                added_count = 0
                for stock in stocks_list:
                    key = (stock.get('symbol'), stock.get('market'))
                    if key not in existing_keys:
                        existing_stocks.append({
                            'symbol': stock.get('symbol'),
                            'name': stock.get('name'),
                            'market': stock.get('market', 'A股')
                        })
                        existing_keys.add(key)
                        added_count += 1
                
                config['stocks'] = existing_stocks
                self.save(None, config)
                return added_count
                
            except Exception as e:
                print(f"批量添加股票失败: {e}")
                return 0
