import os
import json
from datetime import datetime
from .base_store import BaseStore


class BoardCategoryStore(BaseStore):
    """
    板块分类数据存储类
    
    目录结构:
    data/board_category/
    ├── concept_boards.json       # 概念板块列表
    ├── region_boards.json        # 地域板块列表
    ├── industry_boards.json     # 行业板块列表
    ├── stock_industries.json    # 股票行业信息
    ├── industry_hierarchy.json  # 行业层级关系
    ├── concept_stocks/          # 概念板块成分股
    ├── region_stocks/           # 地域板块成分股
    ├── industry_stocks/         # 行业板块成分股
    └── summary.json             # 汇总信息
    """
    
    BOARD_TYPES = {
        'concept': '概念板块',
        'region': '地域板块',
        'industry': '行业板块'
    }
    
    def __init__(self, base_dir='data/board_category'):
        super().__init__(base_dir)
        self._ensure_subdirectories()
    
    def _ensure_subdirectories(self):
        """确保子目录存在"""
        for board_type in self.BOARD_TYPES:
            stocks_dir = os.path.join(self.base_dir, f'{board_type}_stocks')
            if not os.path.exists(stocks_dir):
                os.makedirs(stocks_dir)
    
    def _get_boards_filepath(self, board_type):
        """获取板块列表文件路径"""
        return os.path.join(self.base_dir, f'{board_type}_boards.json')
    
    def _get_stocks_dirpath(self, board_type):
        """获取成分股目录路径"""
        return os.path.join(self.base_dir, f'{board_type}_stocks')
    
    def _get_stocks_filepath(self, board_type, board_code):
        """获取成分股文件路径"""
        return os.path.join(self._get_stocks_dirpath(board_type), f'{board_code}.json')
    
    def _get_stock_industries_filepath(self):
        """获取股票行业信息文件路径"""
        return os.path.join(self.base_dir, 'stock_industries.json')
    
    def _get_industry_hierarchy_filepath(self):
        """获取行业层级关系文件路径"""
        return os.path.join(self.base_dir, 'industry_hierarchy.json')
    
    def _get_summary_filepath(self):
        """获取汇总信息文件路径"""
        return os.path.join(self.base_dir, 'summary.json')
    
    def save_boards(self, board_type, boards):
        """
        保存板块列表
        
        Args:
            board_type: 板块类型 (concept/region/industry)
            boards: 板块列表
        
        Returns:
            bool: 是否成功
        """
        if board_type not in self.BOARD_TYPES:
            print(f"不支持的板块类型: {board_type}")
            return False
        
        with self._lock:
            try:
                data = {
                    'type': board_type,
                    'type_name': self.BOARD_TYPES[board_type],
                    'count': len(boards),
                    'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'boards': boards
                }
                
                filepath = self._get_boards_filepath(board_type)
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                
                return True
            except Exception as e:
                print(f"保存板块列表失败 ({board_type}): {e}")
                return False
    
    def load_boards(self, board_type):
        """
        加载板块列表
        
        Args:
            board_type: 板块类型
        
        Returns:
            list: 板块列表
        """
        if board_type not in self.BOARD_TYPES:
            return []
        
        filepath = self._get_boards_filepath(board_type)
        if not os.path.exists(filepath):
            return []
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('boards', [])
        except Exception as e:
            print(f"加载板块列表失败 ({board_type}): {e}")
            return []
    
    def save_board_stocks(self, board_type, board_code, sector_name, stocks):
        """
        保存板块成分股
        
        Args:
            board_type: 板块类型
            board_code: 板块代码
            sector_name: 板块名称
            stocks: 成分股列表
        
        Returns:
            bool: 是否成功
        """
        if board_type not in self.BOARD_TYPES:
            return False
        
        with self._lock:
            try:
                data = {
                    'board_type': board_type,
                    'board_code': board_code,
                    'board_name': sector_name,
                    'count': len(stocks),
                    'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'stocks': stocks
                }
                
                filepath = self._get_stocks_filepath(board_type, board_code)
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                
                return True
            except Exception as e:
                print(f"保存成分股失败 ({board_type}/{board_code}): {e}")
                return False
    
    def load_board_stocks(self, board_type, board_code):
        """
        加载板块成分股
        
        Args:
            board_type: 板块类型
            board_code: 板块代码
        
        Returns:
            list: 成分股列表
        """
        filepath = self._get_stocks_filepath(board_type, board_code)
        if not os.path.exists(filepath):
            return []
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('stocks', [])
        except Exception as e:
            print(f"加载成分股失败 ({board_type}/{board_code}): {e}")
            return []
    
    def save_stock_industries(self, stocks):
        """
        保存股票行业信息
        
        Args:
            stocks: 股票行业信息字典 {code: {secid, name, industry, region, concepts}}
        
        Returns:
            bool: 是否成功
        """
        with self._lock:
            try:
                data = {
                    'count': len(stocks),
                    'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'stocks': stocks
                }
                
                filepath = self._get_stock_industries_filepath()
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                
                return True
            except Exception as e:
                print(f"保存股票行业信息失败: {e}")
                return False
    
    def load_stock_industries(self):
        """
        加载股票行业信息
        
        Returns:
            dict: 股票行业信息字典
        """
        filepath = self._get_stock_industries_filepath()
        if not os.path.exists(filepath):
            return {}
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('stocks', {})
        except Exception as e:
            print(f"加载股票行业信息失败: {e}")
            return {}
    
    def save_industry_hierarchy(self, hierarchy):
        """
        保存行业层级关系
        
        Args:
            hierarchy: 行业层级关系字典
        
        Returns:
            bool: 是否成功
        """
        with self._lock:
            try:
                data = {
                    'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'hierarchy': hierarchy
                }
                
                filepath = self._get_industry_hierarchy_filepath()
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                
                return True
            except Exception as e:
                print(f"保存行业层级关系失败: {e}")
                return False
    
    def load_industry_hierarchy(self):
        """
        加载行业层级关系
        
        Returns:
            dict: 行业层级关系字典
        """
        filepath = self._get_industry_hierarchy_filepath()
        if not os.path.exists(filepath):
            return None
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('hierarchy', {})
        except Exception as e:
            print(f"加载行业层级关系失败: {e}")
            return None
    
    def save_summary(self, summary):
        """
        保存汇总信息
        
        Args:
            summary: 汇总信息字典
        
        Returns:
            bool: 是否成功
        """
        with self._lock:
            try:
                data = {
                    'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'summary': summary
                }
                
                filepath = self._get_summary_filepath()
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                
                return True
            except Exception as e:
                print(f"保存汇总信息失败: {e}")
                return False
    
    def load_summary(self):
        """
        加载汇总信息
        
        Returns:
            dict: 汇总信息字典
        """
        filepath = self._get_summary_filepath()
        if not os.path.exists(filepath):
            return None
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('summary', {})
        except Exception as e:
            print(f"加载汇总信息失败: {e}")
            return None
    
    def get_boards_info(self, board_type):
        """
        获取板块列表信息
        
        Args:
            board_type: 板块类型
        
        Returns:
            dict: 板块列表信息
        """
        if board_type not in self.BOARD_TYPES:
            return None
        
        filepath = self._get_boards_filepath(board_type)
        if not os.path.exists(filepath):
            return None
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return {
                    'type': data.get('type', ''),
                    'type_name': data.get('type_name', ''),
                    'count': data.get('count', 0),
                    'update_time': data.get('update_time', '')
                }
        except Exception as e:
            print(f"获取板块列表信息失败 ({board_type}): {e}")
            return None
    
    def get_board_stocks_info(self, board_type, board_code):
        """
        获取板块成分股信息
        
        Args:
            board_type: 板块类型
            board_code: 板块代码
        
        Returns:
            dict: 成分股信息
        """
        filepath = self._get_stocks_filepath(board_type, board_code)
        if not os.path.exists(filepath):
            return None
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return {
                    'board_code': data.get('board_code', ''),
                    'board_name': data.get('board_name', ''),
                    'count': data.get('count', 0),
                    'update_time': data.get('update_time', '')
                }
        except Exception as e:
            print(f"获取成分股信息失败 ({board_type}/{board_code}): {e}")
            return None
    
    def get_statistics(self):
        """
        获取统计数据
        
        Returns:
            dict: 统计信息
        """
        stats = {}
        
        for board_type, type_name in self.BOARD_TYPES.items():
            boards_info = self.get_boards_info(board_type)
            if boards_info:
                stocks_dir = self._get_stocks_dirpath(board_type)
                stock_files = 0
                if os.path.exists(stocks_dir):
                    stock_files = len([f for f in os.listdir(stocks_dir) if f.endswith('.json')])
                
                stats[board_type] = {
                    'type_name': type_name,
                    'sector_count': boards_info.get('count', 0),
                    'update_time': boards_info.get('update_time', ''),
                    'stocks_files': stock_files
                }
        
        # 股票行业信息
        stock_industries_filepath = self._get_stock_industries_filepath()
        if os.path.exists(stock_industries_filepath):
            try:
                with open(stock_industries_filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    stats['stock_industries'] = {
                        'count': data.get('count', 0),
                        'update_time': data.get('update_time', '')
                    }
            except:
                pass
        
        # 行业层级关系
        hierarchy_filepath = self._get_industry_hierarchy_filepath()
        if os.path.exists(hierarchy_filepath):
            try:
                with open(hierarchy_filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    hierarchy = data.get('hierarchy', {})
                    stats['industry_hierarchy'] = {
                        'level1_count': len(hierarchy.get('level1', [])),
                        'level2_count': len(hierarchy.get('level2', [])),
                        'level3_count': len(hierarchy.get('level3', [])),
                        'other_count': len(hierarchy.get('other', [])),
                        'update_time': data.get('update_time', '')
                    }
            except:
                pass
        
        return stats
    
    def save(self, key, data, **kwargs):
        """
        保存数据（实现抽象方法）
        
        Args:
            key: 数据键，格式如 'boards:concept' 或 'stocks:concept:BK1320'
            data: 要保存的数据
        
        Returns:
            bool: 是否成功
        """
        parts = key.split(':')
        if len(parts) < 2:
            return False
        
        data_type = parts[0]
        
        if data_type == 'boards':
            board_type = parts[1]
            return self.save_boards(board_type, data)
        
        elif data_type == 'stocks':
            if len(parts) < 3:
                return False
            board_type = parts[1]
            board_code = parts[2]
            board_name = kwargs.get('board_name', '')
            return self.save_board_stocks(board_type, board_code, board_name, data)
        
        elif data_type == 'stock_industries':
            return self.save_stock_industries(data)
        
        elif data_type == 'industry_hierarchy':
            return self.save_industry_hierarchy(data)
        
        elif data_type == 'summary':
            return self.save_summary(data)
        
        return False
    
    def load(self, key, **kwargs):
        """
        加载数据（实现抽象方法）
        
        Args:
            key: 数据键
        
        Returns:
            加载的数据
        """
        parts = key.split(':')
        if len(parts) < 2:
            return None
        
        data_type = parts[0]
        
        if data_type == 'boards':
            board_type = parts[1]
            return self.load_boards(board_type)
        
        elif data_type == 'stocks':
            if len(parts) < 3:
                return None
            board_type = parts[1]
            board_code = parts[2]
            return self.load_board_stocks(board_type, board_code)
        
        elif data_type == 'stock_industries':
            return self.load_stock_industries()
        
        elif data_type == 'industry_hierarchy':
            return self.load_industry_hierarchy()
        
        elif data_type == 'summary':
            return self.load_summary()
        
        return None
    
    def exists(self, key, **kwargs):
        """
        检查数据是否存在（实现抽象方法）
        
        Args:
            key: 数据键
        
        Returns:
            bool: 是否存在
        """
        parts = key.split(':')
        if len(parts) < 2:
            return False
        
        data_type = parts[0]
        
        if data_type == 'boards':
            board_type = parts[1]
            filepath = self._get_boards_filepath(board_type)
            return os.path.exists(filepath)
        
        elif data_type == 'stocks':
            if len(parts) < 3:
                return False
            board_type = parts[1]
            board_code = parts[2]
            filepath = self._get_stocks_filepath(board_type, board_code)
            return os.path.exists(filepath)
        
        elif data_type == 'stock_industries':
            filepath = self._get_stock_industries_filepath()
            return os.path.exists(filepath)
        
        elif data_type == 'industry_hierarchy':
            filepath = self._get_industry_hierarchy_filepath()
            return os.path.exists(filepath)
        
        elif data_type == 'summary':
            filepath = self._get_summary_filepath()
            return os.path.exists(filepath)
        
        return False
    
    def delete(self, key, **kwargs):
        """
        删除数据（实现抽象方法）
        
        Args:
            key: 数据键
        
        Returns:
            bool: 是否成功
        """
        parts = key.split(':')
        if len(parts) < 2:
            return False
        
        data_type = parts[0]
        
        with self._lock:
            try:
                if data_type == 'boards':
                    board_type = parts[1]
                    filepath = self._get_boards_filepath(board_type)
                    if os.path.exists(filepath):
                        os.remove(filepath)
                    return True
                
                elif data_type == 'stocks':
                    if len(parts) < 3:
                        return False
                    board_type = parts[1]
                    board_code = parts[2]
                    filepath = self._get_stocks_filepath(board_type, board_code)
                    if os.path.exists(filepath):
                        os.remove(filepath)
                    return True
                
                elif data_type == 'stock_industries':
                    filepath = self._get_stock_industries_filepath()
                    if os.path.exists(filepath):
                        os.remove(filepath)
                    return True
                
                elif data_type == 'industry_hierarchy':
                    filepath = self._get_industry_hierarchy_filepath()
                    if os.path.exists(filepath):
                        os.remove(filepath)
                    return True
                
                elif data_type == 'summary':
                    filepath = self._get_summary_filepath()
                    if os.path.exists(filepath):
                        os.remove(filepath)
                    return True
                
            except Exception as e:
                print(f"删除数据失败 ({key}): {e}")
                return False
        
        return False
