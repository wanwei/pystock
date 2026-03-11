import os
from .store import SectorStore
from .cache import SectorCache


class SectorManager:
    """
    股票分类数据管理器
    
    管理两类分类数据:
    1. 行业板块 - 如银行、酿酒、半导体等
    2. 概念板块 - 如人工智能、新能源、芯片等
    
    目录结构:
    data/
    └── sector/
        ├── industry.json       # 行业板块数据
        ├── concept.json        # 概念板块数据
        ├── industry_stocks/    # 行业成分股
        │   ├── BK0475.json     # 银行
        │   └── ...
        └── concept_stocks/     # 概念成分股
            └── ...
    """
    
    SECTOR_TYPES = {
        'industry': '行业板块',
        'concept': '概念板块'
    }
    
    SECTOR_COLUMNS = ['code', 'name', 'parent_code', 'parent_name', 'change_pct', 'change', 'price', 
                      'volume', 'amount', 'leading_stock', 'leading_code']
    
    STOCK_COLUMNS = ['code', 'name', 'change_pct', 'change', 'price',
                     'volume', 'amount', 'turnover']
    
    def __init__(self, base_dir='data'):
        sector_dir = os.path.join(base_dir, 'sector')
        self.store = SectorStore(sector_dir)
        self.cache = SectorCache()
    
    def save_sectors(self, sector_type, sectors):
        """
        保存板块列表
        
        Args:
            sector_type: 板块类型 (industry/concept/region)
            sectors: 板块列表，每项包含 code, name 等字段
        
        Returns:
            bool: 是否成功
        """
        if sector_type not in self.SECTOR_TYPES:
            print(f"不支持的板块类型: {sector_type}")
            return False
        
        success = self.store.save_sectors(sector_type, sectors)
        if success:
            self.cache.delete_sectors(sector_type)
            print(f"已保存 {len(sectors)} 个{self.SECTOR_TYPES[sector_type]}")
        
        return success
    
    def load_sectors(self, sector_type):
        """
        加载板块列表
        
        Args:
            sector_type: 板块类型
        
        Returns:
            list: 板块列表
        """
        if sector_type not in self.SECTOR_TYPES:
            print(f"不支持的板块类型: {sector_type}")
            return []
        
        cached = self.cache.get_sectors(sector_type)
        if cached is not None:
            return cached
        
        sectors = self.store.load_sectors(sector_type)
        if sectors:
            self.cache.set_sectors(sector_type, sectors)
        return sectors
    
    def get_sector_info(self, sector_type):
        """
        获取板块数据概览信息
        
        Args:
            sector_type: 板块类型
        
        Returns:
            dict: 包含 count, update_time 等信息
        """
        if sector_type not in self.SECTOR_TYPES:
            return None
        
        return self.store.get_sector_info(sector_type)
    
    def save_sector_stocks(self, sector_type, sector_code, sector_name, stocks):
        """
        保存板块成分股
        
        Args:
            sector_type: 板块类型
            sector_code: 板块代码
            sector_name: 板块名称
            stocks: 成分股列表
        
        Returns:
            bool: 是否成功
        """
        if sector_type not in self.SECTOR_TYPES:
            print(f"不支持的板块类型: {sector_type}")
            return False
        
        success = self.store.save_sector_stocks(sector_type, sector_code, sector_name, stocks)
        if success:
            self.cache.delete_stocks(sector_type, sector_code)
        
        return success
    
    def load_sector_stocks(self, sector_type, sector_code):
        """
        加载板块成分股
        
        Args:
            sector_type: 板块类型
            sector_code: 板块代码
        
        Returns:
            list: 成分股列表
        """
        cached = self.cache.get_stocks(sector_type, sector_code)
        if cached is not None:
            return cached
        
        stocks = self.store.load_sector_stocks(sector_type, sector_code)
        if stocks:
            self.cache.set_stocks(sector_type, sector_code, stocks)
        return stocks
    
    def get_sector_stocks_info(self, sector_type, sector_code):
        """
        获取板块成分股概览信息
        """
        return self.store.get_sector_stocks_info(sector_type, sector_code)
    
    def get_stock_sectors(self, stock_code):
        """
        获取股票所属的所有板块
        
        Args:
            stock_code: 股票代码
        
        Returns:
            dict: {'industry': [...], 'concept': [...]}
        """
        result = {t: [] for t in self.SECTOR_TYPES}
        
        for sector_type in self.SECTOR_TYPES:
            sectors = self.load_sectors(sector_type)
            for sector in sectors:
                sector_code = sector.get('code')
                stocks = self.load_sector_stocks(sector_type, sector_code)
                for stock in stocks:
                    if stock.get('code') == stock_code:
                        result[sector_type].append({
                            'code': sector_code,
                            'name': sector.get('name', '')
                        })
                        break
        
        return result
    
    def list_all_sectors(self):
        """
        列出所有板块信息
        """
        result = {}
        for sector_type in self.SECTOR_TYPES:
            info = self.get_sector_info(sector_type)
            if info:
                result[sector_type] = info
        return result
    
    def clear_cache(self):
        """清空内存缓存"""
        self.cache.clear()
    
    def get_statistics(self):
        """
        获取统计数据
        """
        return self.store.get_statistics()
    
    def get_root_sectors(self, sector_type):
        """
        获取根节点板块（没有父分类的板块）
        
        Args:
            sector_type: 板块类型
        
        Returns:
            list: 根节点板块列表
        """
        if sector_type not in self.SECTOR_TYPES:
            return []
        return self.store.get_root_sectors(sector_type)
    
    def get_child_sectors(self, sector_type, parent_code):
        """
        获取指定板块的子板块
        
        Args:
            sector_type: 板块类型
            parent_code: 父板块代码
        
        Returns:
            list: 子板块列表
        """
        if sector_type not in self.SECTOR_TYPES:
            return []
        return self.store.get_child_sectors(sector_type, parent_code)
    
    def get_sector_by_code(self, sector_type, sector_code):
        """
        根据代码获取板块信息
        
        Args:
            sector_type: 板块类型
            sector_code: 板块代码
        
        Returns:
            dict: 板块信息
        """
        if sector_type not in self.SECTOR_TYPES:
            return None
        return self.store.get_sector_by_code(sector_type, sector_code)
    
    def build_sector_tree(self, sector_type):
        """
        构建板块树形结构
        
        Args:
            sector_type: 板块类型
        
        Returns:
            list: 树形结构数据
        """
        if sector_type not in self.SECTOR_TYPES:
            return []
        return self.store.build_sector_tree(sector_type)
    
    def has_children(self, sector_type, sector_code):
        """
        检查板块是否有子板块
        
        Args:
            sector_type: 板块类型
            sector_code: 板块代码
        
        Returns:
            bool: 是否有子板块
        """
        children = self.get_child_sectors(sector_type, sector_code)
        return len(children) > 0


if __name__ == "__main__":
    manager = SectorManager()
    
    print("=" * 60)
    print("股票分类数据管理器")
    print("=" * 60)
    
    stats = manager.get_statistics()
    for sector_type, info in stats.items():
        print(f"\n{info['type_name']}:")
        print(f"  板块数量: {info['sector_count']}")
        print(f"  成分股文件: {info['stocks_files']}")
        print(f"  更新时间: {info['update_time']}")
