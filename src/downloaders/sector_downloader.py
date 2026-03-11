import time
import json
import requests
from datetime import datetime

AKSHARE_AVAILABLE = True
try:
    import akshare as ak
except ImportError:
    AKSHARE_AVAILABLE = False

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from datamgr.sector_manager import SectorManager


class SectorDownloader:
    """
    股票分类数据下载器
    
    功能:
    1. 下载行业板块列表及成分股
    2. 下载概念板块列表及成分股
    3. 自动保存到 SectorManager
    4. 支持板块层级关系
    
    数据源: AkShare (东方财富)
    
    层级关系说明:
    - 东方财富的行业板块数据本身是扁平的，没有直接的层级关系
    - 可以通过配置文件或手动方式设置层级关系
    - 层级关系通过 parent_code 字段表示
    """
    
    SECTOR_TYPES = {
        'industry': '行业板块',
        'concept': '概念板块'
    }
    
    SECTOR_HIERARCHY_FILE = 'sector_hierarchy.json'
    
    def __init__(self, data_dir='data'):
        self.manager = SectorManager(data_dir)
        self.data_dir = data_dir
        self.akshare_available = AKSHARE_AVAILABLE
        
        if not self.akshare_available:
            print("警告: akshare 未安装，请先安装: pip install akshare")
        
        self._hierarchy_cache = None
    
    def _get_hierarchy_filepath(self):
        return os.path.join(self.data_dir, 'sector', self.SECTOR_HIERARCHY_FILE)
    
    def load_hierarchy_config(self):
        """
        加载层级关系配置
        
        Returns:
            dict: 层级关系配置 {sector_type: {sector_code: parent_code}}
        """
        if self._hierarchy_cache is not None:
            return self._hierarchy_cache
        
        filepath = self._get_hierarchy_filepath()
        if not os.path.exists(filepath):
            self._hierarchy_cache = {}
            return self._hierarchy_cache
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                self._hierarchy_cache = json.load(f)
            return self._hierarchy_cache
        except Exception as e:
            print(f"加载层级配置失败: {e}")
            self._hierarchy_cache = {}
            return self._hierarchy_cache
    
    def save_hierarchy_config(self, hierarchy):
        """
        保存层级关系配置
        
        Args:
            hierarchy: 层级关系配置
        
        Returns:
            bool: 是否成功
        """
        filepath = self._get_hierarchy_filepath()
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(hierarchy, f, ensure_ascii=False, indent=2)
            self._hierarchy_cache = hierarchy
            return True
        except Exception as e:
            print(f"保存层级配置失败: {e}")
            return False
    
    def set_sector_parent(self, sector_type, sector_code, parent_code):
        """
        设置板块的父级关系
        
        Args:
            sector_type: 板块类型
            sector_code: 板块代码
            parent_code: 父板块代码 (None表示根节点)
        
        Returns:
            bool: 是否成功
        """
        hierarchy = self.load_hierarchy_config()
        
        if sector_type not in hierarchy:
            hierarchy[sector_type] = {}
        
        if parent_code is None:
            if sector_code in hierarchy[sector_type]:
                del hierarchy[sector_type][sector_code]
        else:
            hierarchy[sector_type][sector_code] = parent_code
        
        return self.save_hierarchy_config(hierarchy)
    
    def _apply_hierarchy_to_sectors(self, sector_type, sectors):
        """
        应用层级关系到板块列表
        
        Args:
            sector_type: 板块类型
            sectors: 板块列表
        
        Returns:
            list: 带有层级信息的板块列表
        """
        hierarchy = self.load_hierarchy_config()
        sector_hierarchy = hierarchy.get(sector_type, {})
        
        sector_map = {s.get('code'): s for s in sectors}
        
        for sector in sectors:
            code = sector.get('code')
            parent_code = sector_hierarchy.get(code)
            sector['parent_code'] = parent_code
            
            if parent_code and parent_code in sector_map:
                sector['parent_name'] = sector_map[parent_code].get('name', '')
            else:
                sector['parent_name'] = ''
        
        return sectors
    
    def download_industry_sectors(self):
        """
        下载行业板块列表
        
        Returns:
            list: 板块列表
        """
        if not self.akshare_available:
            print("AkShare 不可用")
            return []
        
        try:
            print("正在下载行业板块列表...")
            df = ak.stock_board_industry_name_em()
            
            if df is None or df.empty:
                print("下载失败: 无数据返回")
                return []
            
            sectors = []
            for _, row in df.iterrows():
                sectors.append({
                    'code': str(row.get('板块代码', '')),
                    'name': str(row.get('板块名称', '')),
                    'change_pct': row.get('涨跌幅', 0),
                    'change': row.get('涨跌额', 0),
                    'price': row.get('最新价', 0),
                    'volume': row.get('成交量', 0),
                    'amount': row.get('成交额', 0),
                    'leading_stock': row.get('领涨股票', ''),
                    'leading_code': row.get('领涨股票-涨跌幅', 0)
                })
            
            self.manager.save_sectors('industry', sectors)
            print(f"成功下载 {len(sectors)} 个行业板块")
            
            return sectors
            
        except Exception as e:
            print(f"下载行业板块失败: {e}")
            return []
    
    def download_concept_sectors(self):
        """
        下载概念板块列表
        
        Returns:
            list: 板块列表
        """
        if not self.akshare_available:
            print("AkShare 不可用")
            return []
        
        try:
            print("正在下载概念板块列表...")
            df = ak.stock_board_concept_name_em()
            
            if df is None or df.empty:
                print("下载失败: 无数据返回")
                return []
            
            sectors = []
            for _, row in df.iterrows():
                sectors.append({
                    'code': str(row.get('板块代码', '')),
                    'name': str(row.get('板块名称', '')),
                    'change_pct': row.get('涨跌幅', 0),
                    'change': row.get('涨跌额', 0),
                    'price': row.get('最新价', 0),
                    'volume': row.get('成交量', 0),
                    'amount': row.get('成交额', 0),
                    'leading_stock': row.get('领涨股票', ''),
                    'leading_code': row.get('领涨股票-涨跌幅', 0)
                })
            
            self.manager.save_sectors('concept', sectors)
            print(f"成功下载 {len(sectors)} 个概念板块")
            
            return sectors
            
        except Exception as e:
            print(f"下载概念板块失败: {e}")
            return []
    
    def download_sector_stocks(self, sector_type, sector_code, sector_name):
        """
        下载板块成分股
        
        Args:
            sector_type: 板块类型 (industry/concept)
            sector_code: 板块代码
            sector_name: 板块名称
        
        Returns:
            list: 成分股列表
        """
        if not self.akshare_available:
            return []
        
        try:
            if sector_type == 'industry':
                df = ak.stock_board_industry_cons_em(symbol=sector_name)
            elif sector_type == 'concept':
                df = ak.stock_board_concept_cons_em(symbol=sector_name)
            else:
                return []
            
            if df is None or df.empty:
                return []
            
            stocks = []
            for _, row in df.iterrows():
                stocks.append({
                    'code': str(row.get('代码', '')),
                    'name': str(row.get('名称', '')),
                    'change_pct': row.get('涨跌幅', 0),
                    'change': row.get('涨跌额', 0),
                    'price': row.get('最新价', 0),
                    'volume': row.get('成交量', 0),
                    'amount': row.get('成交额', 0),
                    'turnover': row.get('换手率', 0)
                })
            
            self.manager.save_sector_stocks(sector_type, sector_code, sector_name, stocks)
            
            return stocks
            
        except Exception as e:
            print(f"下载 {sector_name} 成分股失败: {e}")
            return []
    
    def download_all_sector_stocks(self, sector_type, sleep_interval=0.5):
        """
        下载某类型所有板块的成分股
        
        Args:
            sector_type: 板块类型
            sleep_interval: 每次请求间隔(秒)
        
        Returns:
            dict: 下载结果统计
        """
        sectors = self.manager.load_sectors(sector_type)
        if not sectors:
            print(f"请先下载{self.SECTOR_TYPES[sector_type]}列表")
            return None
        
        print(f"\n开始下载{self.SECTOR_TYPES[sector_type]}成分股...")
        print(f"共 {len(sectors)} 个板块")
        
        success_count = 0
        failed_count = 0
        total_stocks = 0
        
        for i, sector in enumerate(sectors, 1):
            code = sector.get('code')
            name = sector.get('name')
            
            print(f"[{i}/{len(sectors)}] {name}...", end=" ")
            
            stocks = self.download_sector_stocks(sector_type, code, name)
            
            if stocks:
                success_count += 1
                total_stocks += len(stocks)
                print(f"✓ {len(stocks)}只")
            else:
                failed_count += 1
                print("✗")
            
            if sleep_interval > 0:
                time.sleep(sleep_interval)
        
        print(f"\n下载完成!")
        print(f"成功: {success_count}, 失败: {failed_count}, 共 {total_stocks} 只股票")
        
        return {
            'success': success_count,
            'failed': failed_count,
            'total_stocks': total_stocks
        }
    
    def download_all(self, include_stocks=True, sleep_interval=0.5):
        """
        下载所有分类数据
        
        Args:
            include_stocks: 是否下载成分股
            sleep_interval: 请求间隔
        
        Returns:
            dict: 下载结果
        """
        print("=" * 60)
        print("股票分类数据下载")
        print("=" * 60)
        
        results = {}
        
        for sector_type in self.SECTOR_TYPES:
            print(f"\n--- {self.SECTOR_TYPES[sector_type]} ---")
            
            if sector_type == 'industry':
                sectors = self.download_industry_sectors()
            elif sector_type == 'concept':
                sectors = self.download_concept_sectors()
            
            results[sector_type] = {
                'sector_count': len(sectors),
                'stocks_downloaded': 0
            }
            
            if include_stocks and sectors:
                stock_result = self.download_all_sector_stocks(sector_type, sleep_interval)
                if stock_result:
                    results[sector_type]['stocks_downloaded'] = stock_result['total_stocks']
        
        print("\n" + "=" * 60)
        print("全部下载完成!")
        print("=" * 60)
        
        for sector_type, info in results.items():
            print(f"{self.SECTOR_TYPES[sector_type]}: {info['sector_count']}个板块, {info['stocks_downloaded']}只股票")
        
        return results
    
    def show_statistics(self):
        """显示统计数据"""
        stats = self.manager.get_statistics()
        
        print("\n" + "=" * 50)
        print("股票分类数据统计")
        print("=" * 50)
        
        for sector_type, info in stats.items():
            print(f"\n{info['type_name']}:")
            print(f"  板块数量: {info['sector_count']}")
            print(f"  成分股文件: {info['stocks_files']}")
            print(f"  更新时间: {info['update_time']}")


if __name__ == "__main__":
    downloader = SectorDownloader()
    
    if not downloader.akshare_available:
        print("请先安装 akshare: pip install akshare")
        exit(1)
    
    downloader.show_statistics()
    
    print("\n选择操作:")
    print("1. 下载所有分类数据（含成分股）")
    print("2. 仅下载板块列表")
    print("3. 下载行业板块")
    print("4. 下载概念板块")
    
    choice = input("\n请输入选项 (1-4): ").strip()
    
    if choice == '1':
        downloader.download_all(include_stocks=True)
    elif choice == '2':
        downloader.download_all(include_stocks=False)
    elif choice == '3':
        downloader.download_industry_sectors()
        downloader.download_all_sector_stocks('industry')
    elif choice == '4':
        downloader.download_concept_sectors()
        downloader.download_all_sector_stocks('concept')
    
    downloader.show_statistics()
