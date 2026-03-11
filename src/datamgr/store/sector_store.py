import os
import json
from datetime import datetime
from .base_store import BaseStore


class SectorStore(BaseStore):
    """
    板块数据存储类
    
    目录结构:
    base_dir/
    ├── industry.json       # 行业板块数据
    ├── concept.json        # 概念板块数据
    ├── industry_stocks/    # 行业成分股
    │   ├── BK0475.json
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
    
    def __init__(self, base_dir):
        super().__init__(base_dir)
        self._ensure_subdirectories()
    
    def _ensure_subdirectories(self):
        for sector_type in self.SECTOR_TYPES:
            stocks_dir = os.path.join(self.base_dir, f'{sector_type}_stocks')
            if not os.path.exists(stocks_dir):
                os.makedirs(stocks_dir)
    
    def _get_sector_filepath(self, sector_type):
        return os.path.join(self.base_dir, f'{sector_type}.json')
    
    def _get_stocks_dirpath(self, sector_type):
        return os.path.join(self.base_dir, f'{sector_type}_stocks')
    
    def get_filepath(self, sector_type, sector_code=None):
        if sector_code:
            dirpath = self._get_stocks_dirpath(sector_type)
            return os.path.join(dirpath, f'{sector_code}.json')
        return self._get_sector_filepath(sector_type)
    
    def save_sectors(self, sector_type, sectors):
        """
        保存板块列表
        
        Args:
            sector_type: 板块类型 (industry/concept)
            sectors: 板块列表
        
        Returns:
            bool: 是否成功
        """
        if sector_type not in self.SECTOR_TYPES:
            print(f"不支持的板块类型: {sector_type}")
            return False
        
        with self._lock:
            try:
                data = {
                    'type': sector_type,
                    'type_name': self.SECTOR_TYPES[sector_type],
                    'count': len(sectors),
                    'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'sectors': sectors
                }
                
                filepath = self._get_sector_filepath(sector_type)
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                
                return True
                
            except Exception as e:
                print(f"保存板块数据失败: {e}")
                return False
    
    def load_sectors(self, sector_type):
        """
        加载板块列表
        
        Args:
            sector_type: 板块类型
        
        Returns:
            list: 板块列表
        """
        if sector_type not in self.SECTOR_TYPES:
            return []
        
        filepath = self._get_sector_filepath(sector_type)
        if not os.path.exists(filepath):
            return []
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data.get('sectors', [])
        except Exception as e:
            print(f"加载板块数据失败: {e}")
            return []
    
    def get_sector_info(self, sector_type):
        """
        获取板块数据概览信息
        """
        if sector_type not in self.SECTOR_TYPES:
            return None
        
        filepath = self._get_sector_filepath(sector_type)
        if not os.path.exists(filepath):
            return None
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return {
                'type': sector_type,
                'type_name': data.get('type_name', ''),
                'count': data.get('count', 0),
                'update_time': data.get('update_time', '')
            }
        except:
            return None
    
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
        
        with self._lock:
            try:
                data = {
                    'sector_type': sector_type,
                    'sector_code': sector_code,
                    'sector_name': sector_name,
                    'count': len(stocks),
                    'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'stocks': stocks
                }
                
                filepath = self.get_filepath(sector_type, sector_code)
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                
                return True
                
            except Exception as e:
                print(f"保存成分股数据失败 {sector_name}: {e}")
                return False
    
    def load_sector_stocks(self, sector_type, sector_code):
        """
        加载板块成分股
        
        Args:
            sector_type: 板块类型
            sector_code: 板块代码
        
        Returns:
            list: 成分股列表
        """
        filepath = self.get_filepath(sector_type, sector_code)
        if not os.path.exists(filepath):
            return []
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data.get('stocks', [])
        except Exception as e:
            print(f"加载成分股数据失败: {e}")
            return []
    
    def get_sector_stocks_info(self, sector_type, sector_code):
        """
        获取板块成分股概览信息
        """
        filepath = self.get_filepath(sector_type, sector_code)
        if not os.path.exists(filepath):
            return None
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return {
                'sector_code': sector_code,
                'sector_name': data.get('sector_name', ''),
                'count': data.get('count', 0),
                'update_time': data.get('update_time', '')
            }
        except:
            return None
    
    def save(self, key, data, **kwargs):
        sector_type = kwargs.get('sector_type')
        if sector_type:
            sector_code = kwargs.get('sector_code')
            sector_name = kwargs.get('sector_name', '')
            if sector_code:
                return self.save_sector_stocks(sector_type, sector_code, sector_name, data)
            return self.save_sectors(sector_type, data)
        return False
    
    def load(self, key, **kwargs):
        sector_type = kwargs.get('sector_type')
        if sector_type:
            sector_code = kwargs.get('sector_code')
            if sector_code:
                return self.load_sector_stocks(sector_type, sector_code)
            return self.load_sectors(sector_type)
        return None
    
    def exists(self, key, **kwargs):
        sector_type = kwargs.get('sector_type')
        if sector_type:
            sector_code = kwargs.get('sector_code')
            filepath = self.get_filepath(sector_type, sector_code)
            return os.path.exists(filepath)
        return False
    
    def delete(self, key, **kwargs):
        with self._lock:
            try:
                sector_type = kwargs.get('sector_type')
                if sector_type:
                    sector_code = kwargs.get('sector_code')
                    filepath = self.get_filepath(sector_type, sector_code)
                    if os.path.exists(filepath):
                        os.remove(filepath)
                    return True
                return False
            except Exception as e:
                print(f"删除板块数据失败: {e}")
                return False
    
    def get_statistics(self):
        """
        获取统计数据
        """
        stats = {}
        for sector_type, type_name in self.SECTOR_TYPES.items():
            sector_info = self.get_sector_info(sector_type)
            stocks_dir = self._get_stocks_dirpath(sector_type)
            
            stock_files = 0
            if os.path.exists(stocks_dir):
                stock_files = len([f for f in os.listdir(stocks_dir) if f.endswith('.json')])
            
            stats[sector_type] = {
                'type_name': type_name,
                'sector_count': sector_info['count'] if sector_info else 0,
                'update_time': sector_info['update_time'] if sector_info else '',
                'stocks_files': stock_files
            }
        
        return stats
    
    def get_root_sectors(self, sector_type):
        """
        获取根节点板块（没有父分类的板块）
        
        Args:
            sector_type: 板块类型
        
        Returns:
            list: 根节点板块列表
        """
        sectors = self.load_sectors(sector_type)
        return [s for s in sectors if not s.get('parent_code')]
    
    def get_child_sectors(self, sector_type, parent_code):
        """
        获取指定板块的子板块
        
        Args:
            sector_type: 板块类型
            parent_code: 父板块代码
        
        Returns:
            list: 子板块列表
        """
        sectors = self.load_sectors(sector_type)
        return [s for s in sectors if s.get('parent_code') == parent_code]
    
    def get_sector_by_code(self, sector_type, sector_code):
        """
        根据代码获取板块信息
        
        Args:
            sector_type: 板块类型
            sector_code: 板块代码
        
        Returns:
            dict: 板块信息，未找到返回 None
        """
        sectors = self.load_sectors(sector_type)
        for sector in sectors:
            if sector.get('code') == sector_code:
                return sector
        return None
    
    def build_sector_tree(self, sector_type):
        """
        构建板块树形结构
        
        Args:
            sector_type: 板块类型
        
        Returns:
            list: 树形结构数据，每项包含 sector 和 children
        """
        sectors = self.load_sectors(sector_type)
        sector_map = {s.get('code'): s for s in sectors}
        
        def build_node(sector):
            node = {
                'sector': sector,
                'children': []
            }
            code = sector.get('code')
            for s in sectors:
                if s.get('parent_code') == code:
                    node['children'].append(build_node(s))
            return node
        
        root_sectors = [s for s in sectors if not s.get('parent_code')]
        tree = [build_node(s) for s in root_sectors]
        
        return tree
