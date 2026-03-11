from .base_cache import BaseCache


class BoardCategoryCache(BaseCache):
    """
    板块分类数据缓存类
    
    缓存键格式:
    - 板块列表: boards_{type}  例如: boards_concept
    - 成分股: stocks_{type}_{code}  例如: stocks_concept_BK1320
    - 股票行业: stock_industry_{code}  例如: stock_industry_600519
    - 行业层级: industry_hierarchy
    """
    
    BOARD_TYPES = ['concept', 'region', 'industry']
    
    def __init__(self, max_size=500):
        super().__init__(max_size)
    
    def build_key(self, *args, **kwargs):
        """
        构建缓存键（实现抽象方法）
        
        Args:
            *args: 位置参数
            **kwargs: 关键字参数
        
        Returns:
            str: 缓存键
        """
        if not args:
            return ''
        
        data_type = args[0]
        
        if data_type == 'boards':
            board_type = args[1] if len(args) > 1 else ''
            return self._build_boards_key(board_type)
        
        elif data_type == 'stocks':
            board_type = args[1] if len(args) > 1 else ''
            board_code = args[2] if len(args) > 2 else ''
            return self._build_stocks_key(board_type, board_code)
        
        elif data_type == 'stock_industry':
            stock_code = args[1] if len(args) > 1 else ''
            return self._build_stock_industry_key(stock_code)
        
        elif data_type == 'stock_industries':
            return self._build_stock_industries_key()
        
        elif data_type == 'industry_hierarchy':
            return self._build_industry_hierarchy_key()
        
        return ''
    
    def _build_boards_key(self, board_type):
        """构建板块列表缓存键"""
        return f"boards_{board_type}"
    
    def _build_stocks_key(self, board_type, board_code):
        """构建成分股缓存键"""
        return f"stocks_{board_type}_{board_code}"
    
    def _build_stock_industry_key(self, stock_code):
        """构建股票行业缓存键"""
        return f"stock_industry_{stock_code}"
    
    def _build_industry_hierarchy_key(self):
        """构建行业层级缓存键"""
        return "industry_hierarchy"
    
    def _build_stock_industries_key(self):
        """构建所有股票行业缓存键"""
        return "stock_industries"
    
    # 板块列表缓存
    def get_boards(self, board_type):
        """获取板块列表缓存"""
        key = self._build_boards_key(board_type)
        return self.get(key)
    
    def set_boards(self, board_type, data):
        """设置板块列表缓存"""
        key = self._build_boards_key(board_type)
        self.set(key, data)
    
    def exists_boards(self, board_type):
        """检查板块列表缓存是否存在"""
        key = self._build_boards_key(board_type)
        return self.exists(key)
    
    def delete_boards(self, board_type):
        """删除板块列表缓存"""
        key = self._build_boards_key(board_type)
        self.delete(key)
    
    # 成分股缓存
    def get_stocks(self, board_type, board_code):
        """获取成分股缓存"""
        key = self._build_stocks_key(board_type, board_code)
        return self.get(key)
    
    def set_stocks(self, board_type, board_code, data):
        """设置成分股缓存"""
        key = self._build_stocks_key(board_type, board_code)
        self.set(key, data)
    
    def exists_stocks(self, board_type, board_code):
        """检查成分股缓存是否存在"""
        key = self._build_stocks_key(board_type, board_code)
        return self.exists(key)
    
    def delete_stocks(self, board_type, board_code):
        """删除成分股缓存"""
        key = self._build_stocks_key(board_type, board_code)
        self.delete(key)
    
    # 股票行业缓存
    def get_stock_industry(self, stock_code):
        """获取单只股票行业缓存"""
        key = self._build_stock_industry_key(stock_code)
        return self.get(key)
    
    def set_stock_industry(self, stock_code, data):
        """设置单只股票行业缓存"""
        key = self._build_stock_industry_key(stock_code)
        self.set(key, data)
    
    def exists_stock_industry(self, stock_code):
        """检查单只股票行业缓存是否存在"""
        key = self._build_stock_industry_key(stock_code)
        return self.exists(key)
    
    def delete_stock_industry(self, stock_code):
        """删除单只股票行业缓存"""
        key = self._build_stock_industry_key(stock_code)
        self.delete(key)
    
    # 所有股票行业缓存
    def get_stock_industries(self):
        """获取所有股票行业缓存"""
        key = self._build_stock_industries_key()
        return self.get(key)
    
    def set_stock_industries(self, data):
        """设置所有股票行业缓存"""
        key = self._build_stock_industries_key()
        self.set(key, data)
    
    def exists_stock_industries(self):
        """检查所有股票行业缓存是否存在"""
        key = self._build_stock_industries_key()
        return self.exists(key)
    
    def delete_stock_industries(self):
        """删除所有股票行业缓存"""
        key = self._build_stock_industries_key()
        self.delete(key)
    
    # 行业层级缓存
    def get_industry_hierarchy(self):
        """获取行业层级缓存"""
        key = self._build_industry_hierarchy_key()
        return self.get(key)
    
    def set_industry_hierarchy(self, data):
        """设置行业层级缓存"""
        key = self._build_industry_hierarchy_key()
        self.set(key, data)
    
    def exists_industry_hierarchy(self):
        """检查行业层级缓存是否存在"""
        key = self._build_industry_hierarchy_key()
        return self.exists(key)
    
    def delete_industry_hierarchy(self):
        """删除行业层级缓存"""
        key = self._build_industry_hierarchy_key()
        self.delete(key)
    
    # 批量操作
    def clear_all_boards(self):
        """清除所有板块列表缓存"""
        for board_type in self.BOARD_TYPES:
            self.delete_boards(board_type)
    
    def clear_all_stocks(self, board_type, board_codes):
        """清除指定类型的所有成分股缓存"""
        for code in board_codes:
            self.delete_stocks(board_type, code)
    
    def clear_all_stock_industries(self, stock_codes):
        """清除所有股票行业缓存"""
        for code in stock_codes:
            self.delete_stock_industry(code)
    
    def clear_all(self):
        """清除所有缓存"""
        self.clear()
