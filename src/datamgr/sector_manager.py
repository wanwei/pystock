import os
import json
import pandas as pd
from datetime import datetime
from threading import Lock


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
    
    SECTOR_COLUMNS = ['code', 'name', 'change_pct', 'change', 'price', 
                      'volume', 'amount', 'leading_stock', 'leading_code']
    
    STOCK_COLUMNS = ['code', 'name', 'change_pct', 'change', 'price',
                     'volume', 'amount', 'turnover']
    
    def __init__(self, base_dir='data'):
        self.base_dir = base_dir
        self.sector_dir = os.path.join(base_dir, 'sector')
        
        self._cache = {}
        self._lock = Lock()
        
        self._ensure_directories()
    
    def _ensure_directories(self):
        dirs = [
            self.sector_dir,
            os.path.join(self.sector_dir, 'industry_stocks'),
            os.path.join(self.sector_dir, 'concept_stocks')
        ]
        for d in dirs:
            if not os.path.exists(d):
                os.makedirs(d)
    
    def _get_sector_filepath(self, sector_type):
        return os.path.join(self.sector_dir, f'{sector_type}.json')
    
    def _get_stocks_dirpath(self, sector_type):
        return os.path.join(self.sector_dir, f'{sector_type}_stocks')
    
    def _get_stocks_filepath(self, sector_type, sector_code):
        dirpath = self._get_stocks_dirpath(sector_type)
        return os.path.join(dirpath, f'{sector_code}.json')
    
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
                
                self._cache[sector_type] = data
                print(f"已保存 {len(sectors)} 个{self.SECTOR_TYPES[sector_type]}")
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
            print(f"不支持的板块类型: {sector_type}")
            return []
        
        if sector_type in self._cache:
            return self._cache[sector_type].get('sectors', [])
        
        filepath = self._get_sector_filepath(sector_type)
        if not os.path.exists(filepath):
            return []
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self._cache[sector_type] = data
            return data.get('sectors', [])
        except Exception as e:
            print(f"加载板块数据失败: {e}")
            return []
    
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
        
        if sector_type in self._cache:
            data = self._cache[sector_type]
            return {
                'type': sector_type,
                'type_name': data.get('type_name', ''),
                'count': data.get('count', 0),
                'update_time': data.get('update_time', '')
            }
        
        filepath = self._get_sector_filepath(sector_type)
        if not os.path.exists(filepath):
            return None
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self._cache[sector_type] = data
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
                
                filepath = self._get_stocks_filepath(sector_type, sector_code)
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                
                cache_key = f"{sector_type}_{sector_code}"
                self._cache[cache_key] = data
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
        cache_key = f"{sector_type}_{sector_code}"
        if cache_key in self._cache:
            return self._cache[cache_key].get('stocks', [])
        
        filepath = self._get_stocks_filepath(sector_type, sector_code)
        if not os.path.exists(filepath):
            return []
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self._cache[cache_key] = data
            return data.get('stocks', [])
        except Exception as e:
            print(f"加载成分股数据失败: {e}")
            return []
    
    def get_sector_stocks_info(self, sector_type, sector_code):
        """
        获取板块成分股概览信息
        """
        cache_key = f"{sector_type}_{sector_code}"
        if cache_key in self._cache:
            data = self._cache[cache_key]
            return {
                'sector_code': sector_code,
                'sector_name': data.get('sector_name', ''),
                'count': data.get('count', 0),
                'update_time': data.get('update_time', '')
            }
        
        filepath = self._get_stocks_filepath(sector_type, sector_code)
        if not os.path.exists(filepath):
            return None
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self._cache[cache_key] = data
            return {
                'sector_code': sector_code,
                'sector_name': data.get('sector_name', ''),
                'count': data.get('count', 0),
                'update_time': data.get('update_time', '')
            }
        except:
            return None
    
    def get_stock_sectors(self, stock_code):
        """
        获取股票所属的所有板块
        
        Args:
            stock_code: 股票代码
        
        Returns:
            dict: {'industry': [...], 'concept': [...], 'region': [...]}
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
        with self._lock:
            self._cache.clear()
    
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
