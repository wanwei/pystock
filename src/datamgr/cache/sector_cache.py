from .base_cache import BaseCache


class SectorCache(BaseCache):
    """
    板块数据缓存类
    
    缓存键格式:
    - 板块列表: sector_{type}  例如: sector_industry
    - 成分股: stocks_{type}_{code}  例如: stocks_industry_BK0475
    """
    
    def __init__(self, max_size=300):
        super().__init__(max_size)
    
    def build_key(self, sector_type, sector_code=None):
        """
        构建板块缓存键
        
        Args:
            sector_type: 板块类型
            sector_code: 板块代码 (可选)
        
        Returns:
            str: 缓存键
        """
        if sector_code:
            return f"stocks_{sector_type}_{sector_code}"
        return f"sector_{sector_type}"
    
    def get_sectors(self, sector_type):
        """
        获取板块列表缓存
        """
        key = self.build_key(sector_type)
        return self.get(key)
    
    def set_sectors(self, sector_type, data):
        """
        设置板块列表缓存
        """
        key = self.build_key(sector_type)
        self.set(key, data)
    
    def exists_sectors(self, sector_type):
        """
        检查板块列表缓存是否存在
        """
        key = self.build_key(sector_type)
        return self.exists(key)
    
    def delete_sectors(self, sector_type):
        """
        删除板块列表缓存
        """
        key = self.build_key(sector_type)
        self.delete(key)
    
    def get_stocks(self, sector_type, sector_code):
        """
        获取成分股缓存
        """
        key = self.build_key(sector_type, sector_code)
        return self.get(key)
    
    def set_stocks(self, sector_type, sector_code, data):
        """
        设置成分股缓存
        """
        key = self.build_key(sector_type, sector_code)
        self.set(key, data)
    
    def exists_stocks(self, sector_type, sector_code):
        """
        检查成分股缓存是否存在
        """
        key = self.build_key(sector_type, sector_code)
        return self.exists(key)
    
    def delete_stocks(self, sector_type, sector_code):
        """
        删除成分股缓存
        """
        key = self.build_key(sector_type, sector_code)
        self.delete(key)
