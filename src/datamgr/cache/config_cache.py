from .base_cache import BaseCache


class ConfigCache(BaseCache):
    """
    配置数据缓存类
    
    缓存键格式: config
    """
    
    def __init__(self, max_size=10):
        super().__init__(max_size)
    
    def build_key(self, key=None):
        """
        构建配置缓存键
        
        Args:
            key: 配置键 (未使用)
        
        Returns:
            str: 缓存键
        """
        return 'config'
    
    def get_config(self):
        """
        获取配置缓存
        """
        key = self.build_key()
        return self.get(key)
    
    def set_config(self, data):
        """
        设置配置缓存
        """
        key = self.build_key()
        self.set(key, data)
    
    def exists_config(self):
        """
        检查配置缓存是否存在
        """
        key = self.build_key()
        return self.exists(key)
    
    def delete_config(self):
        """
        删除配置缓存
        """
        key = self.build_key()
        self.delete(key)
    
    def invalidate(self):
        """
        使配置缓存失效
        """
        self.delete_config()
