import threading
from typing import List, Dict, Optional
from .store.board_category_store import BoardCategoryStore
from .cache.board_category_cache import BoardCategoryCache


class BoardCategoryManager:
    """
    板块分类数据管理类
    
    功能:
    1. 管理概念板块、地域板块、行业板块数据
    2. 管理股票行业信息
    3. 管理行业层级关系
    4. 提供查询接口
    
    使用示例:
        manager = BoardCategoryManager()
        
        # 获取概念板块列表
        concepts = manager.get_boards('concept')
        
        # 获取板块成分股
        stocks = manager.get_board_stocks('concept', 'BK1320')
        
        # 获取股票所属行业
        industry = manager.get_stock_industry('600519')
        
        # 获取行业层级关系
        hierarchy = manager.get_industry_hierarchy()
    """
    
    BOARD_TYPES = {
        'concept': '概念板块',
        'region': '地域板块',
        'industry': '行业板块'
    }
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        """单例模式"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, data_dir='data/board_category', cache_size=500):
        if hasattr(self, '_initialized') and self._initialized:
            return
        
        self.store = BoardCategoryStore(data_dir)
        self.cache = BoardCategoryCache(cache_size)
        self._initialized = True
        
        self._boards_cache = {}  # 板块列表缓存
        self._stock_industries_cache = {}  # 股票行业缓存
        self._industry_hierarchy_cache = None  # 行业层级缓存
    
    def get_boards(self, board_type: str, use_cache: bool = True) -> List[Dict]:
        """
        获取板块列表
        
        Args:
            board_type: 板块类型 (concept/region/industry)
            use_cache: 是否使用缓存
        
        Returns:
            list: 板块列表 [{code, name, price, change_pct, ...}, ...]
        """
        if board_type not in self.BOARD_TYPES:
            return []
        
        if use_cache:
            cached = self.cache.get_boards(board_type)
            if cached:
                return cached
        
        boards = self.store.load_boards(board_type)
        
        if boards and use_cache:
            self.cache.set_boards(board_type, boards)
        
        return boards
    
    def get_board_by_code(self, board_type: str, board_code: str) -> Optional[Dict]:
        """
        根据代码获取板块信息
        
        Args:
            board_type: 板块类型
            board_code: 板块代码
        
        Returns:
            dict: 板块信息
        """
        boards = self.get_boards(board_type)
        for board in boards:
            if board.get('code') == board_code:
                return board
        return None
    
    def get_board_by_name(self, board_type: str, board_name: str) -> Optional[Dict]:
        """
        根据名称获取板块信息
        
        Args:
            board_type: 板块类型
            board_name: 板块名称
        
        Returns:
            dict: 板块信息
        """
        boards = self.get_boards(board_type)
        for board in boards:
            if board.get('name') == board_name:
                return board
        return None
    
    def search_boards(self, board_type: str, keyword: str) -> List[Dict]:
        """
        搜索板块
        
        Args:
            board_type: 板块类型
            keyword: 搜索关键词
        
        Returns:
            list: 匹配的板块列表
        """
        boards = self.get_boards(board_type)
        keyword = keyword.lower()
        return [b for b in boards if keyword in b.get('name', '').lower() or keyword in b.get('code', '').lower()]
    
    def get_board_stocks(self, board_type: str, board_code: str, use_cache: bool = True) -> List[Dict]:
        """
        获取板块成分股
        
        Args:
            board_type: 板块类型
            board_code: 板块代码
            use_cache: 是否使用缓存
        
        Returns:
            list: 成分股列表 [{code, name, price, ...}, ...]
        """
        if board_type not in self.BOARD_TYPES:
            return []
        
        if use_cache:
            cached = self.cache.get_stocks(board_type, board_code)
            if cached:
                return cached
        
        stocks = self.store.load_board_stocks(board_type, board_code)
        
        if stocks and use_cache:
            self.cache.set_stocks(board_type, board_code, stocks)
        
        return stocks
    
    def get_stock_industry(self, stock_code: str, use_cache: bool = True) -> Optional[Dict]:
        """
        获取股票行业信息
        
        Args:
            stock_code: 股票代码
            use_cache: 是否使用缓存
        
        Returns:
            dict: 行业信息 {secid, name, industry, region, concepts}
        """
        if use_cache:
            cached = self.cache.get_stock_industry(stock_code)
            if cached:
                return cached
        
        stock_industries = self.get_all_stock_industries(use_cache)
        info = stock_industries.get(stock_code)
        
        if info and use_cache:
            self.cache.set_stock_industry(stock_code, info)
        
        return info
    
    def get_all_stock_industries(self, use_cache: bool = True) -> Dict:
        """
        获取所有股票行业信息
        
        Args:
            use_cache: 是否使用缓存
        
        Returns:
            dict: 股票行业信息字典 {code: {secid, name, industry, region, concepts}}
        """
        if use_cache:
            cached = self.cache.get_stock_industries()
            if cached:
                return cached
        
        stock_industries = self.store.load_stock_industries()
        
        if stock_industries and use_cache:
            self.cache.set_stock_industries(stock_industries)
        
        return stock_industries
    
    def get_industry_hierarchy(self, use_cache: bool = True) -> Optional[Dict]:
        """
        获取行业层级关系
        
        Args:
            use_cache: 是否使用缓存
        
        Returns:
            dict: 行业层级关系 {level1, level2, level3, other, relations}
        """
        if use_cache:
            cached = self.cache.get_industry_hierarchy()
            if cached:
                return cached
        
        hierarchy = self.store.load_industry_hierarchy()
        
        if hierarchy and use_cache:
            self.cache.set_industry_hierarchy(hierarchy)
        
        return hierarchy
    
    def get_stocks_by_industry(self, industry_name: str) -> List[str]:
        """
        获取指定行业的所有股票
        
        Args:
            industry_name: 行业名称
        
        Returns:
            list: 股票代码列表
        """
        stock_industries = self.get_all_stock_industries()
        return [code for code, info in stock_industries.items() if info.get('industry') == industry_name]
    
    def get_stocks_by_region(self, region_name: str) -> List[str]:
        """
        获取指定地域的所有股票
        
        Args:
            region_name: 地域名称
        
        Returns:
            list: 股票代码列表
        """
        stock_industries = self.get_all_stock_industries()
        return [code for code, info in stock_industries.items() if info.get('region') == region_name]
    
    def get_stocks_by_concept(self, concept_name: str) -> List[str]:
        """
        获取指定概念的所有股票
        
        Args:
            concept_name: 概念名称
        
        Returns:
            list: 股票代码列表
        """
        stock_industries = self.get_all_stock_industries()
        result = []
        for code, info in stock_industries.items():
            concepts = info.get('concepts', '')
            if concepts and concept_name in concepts:
                result.append(code)
        return result
    
    def get_stock_concepts(self, stock_code: str) -> List[str]:
        """
        获取股票所属概念列表
        
        Args:
            stock_code: 股票代码
        
        Returns:
            list: 概念列表
        """
        info = self.get_stock_industry(stock_code)
        if not info:
            return []
        
        concepts = info.get('concepts', '')
        if not concepts:
            return []
        
        return [c.strip() for c in concepts.split(',') if c.strip()]
    
    def get_industry_level1_list(self) -> List[Dict]:
        """获取一级行业列表"""
        hierarchy = self.get_industry_hierarchy()
        if not hierarchy:
            return []
        return hierarchy.get('level1', [])
    
    def get_industry_level2_list(self) -> List[Dict]:
        """获取二级行业列表"""
        hierarchy = self.get_industry_hierarchy()
        if not hierarchy:
            return []
        return hierarchy.get('level2', [])
    
    def get_industry_level3_list(self) -> List[Dict]:
        """获取三级行业列表"""
        hierarchy = self.get_industry_hierarchy()
        if not hierarchy:
            return []
        return hierarchy.get('level3', [])
    
    def get_industry_other_list(self) -> List[Dict]:
        """获取其他行业列表"""
        hierarchy = self.get_industry_hierarchy()
        if not hierarchy:
            return []
        return hierarchy.get('other', [])
    
    def get_industry_relations(self) -> Dict:
        """获取行业父子关系"""
        hierarchy = self.get_industry_hierarchy()
        if not hierarchy:
            return {}
        return hierarchy.get('relations', {})
    
    def get_level2_by_level1(self, level1_name: str) -> List[str]:
        """
        获取一级行业下的二级行业列表
        
        Args:
            level1_name: 一级行业名称
        
        Returns:
            list: 二级行业名称列表
        """
        relations = self.get_industry_relations()
        return relations.get(level1_name, [])
    
    def get_statistics(self) -> Dict:
        """
        获取统计数据
        
        Returns:
            dict: 统计信息
        """
        return self.store.get_statistics()
    
    def clear_cache(self):
        """清除所有缓存"""
        self.cache.clear_all()
        self._boards_cache = {}
        self._stock_industries_cache = {}
        self._industry_hierarchy_cache = None
    
    def refresh_data(self, board_type: str = None):
        """
        刷新数据
        
        Args:
            board_type: 板块类型，None表示刷新所有
        """
        if board_type:
            self.cache.delete_boards(board_type)
        else:
            self.clear_cache()
    
    def get_board_count(self, board_type: str) -> int:
        """获取板块数量"""
        boards = self.get_boards(board_type)
        return len(boards)
    
    def get_total_board_count(self) -> Dict[str, int]:
        """获取所有板块数量"""
        return {t: self.get_board_count(t) for t in self.BOARD_TYPES}
    
    def is_valid_board_type(self, board_type: str) -> bool:
        """检查板块类型是否有效"""
        return board_type in self.BOARD_TYPES
    
    def get_board_type_name(self, board_type: str) -> str:
        """获取板块类型名称"""
        return self.BOARD_TYPES.get(board_type, '')
