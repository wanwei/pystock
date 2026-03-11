"""
东方财富板块分类数据下载器

功能:
1. 下载概念板块列表及成分股
2. 下载地域板块列表及成分股
3. 下载行业板块列表及成分股
4. 获取股票的行业分级信息（东财一级行业、二级行业、三级行业）
5. 建立行业层级关系

数据源: 东方财富网 API

API说明:
- 板块列表: https://push2.eastmoney.com/api/qt/clist/get
  - 概念板块: fs=m:90+t:2
  - 地域板块: fs=m:90+t:1
  - 行业板块: fs=m:90+t:3

- 板块成分股: https://push2.eastmoney.com/api/qt/clist/get
  - fs=b:{board_code}+f:!50

- 股票行业信息: https://push2.eastmoney.com/api/qt/stock/get
  - f127: 行业（如 白酒Ⅱ、银行Ⅱ）
  - f128: 地域（如 贵州板块）
  - f129: 概念（逗号分隔）
"""

import time
import json
import requests
import os
from datetime import datetime
from collections import defaultdict


class BoardCategoryDownloader:
    """东方财富板块分类数据下载器"""
    
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://quote.eastmoney.com/'
    }
    
    BOARD_TYPES = {
        'concept': {'name': '概念板块', 'fs': 'm:90+t:2'},
        'region': {'name': '地域板块', 'fs': 'm:90+t:1'},
        'industry': {'name': '行业板块', 'fs': 'm:90+t:3'},
    }
    
    CLIST_URL = 'https://push2.eastmoney.com/api/qt/clist/get'
    STOCK_URL = 'https://push2.eastmoney.com/api/qt/stock/get'
    
    def __init__(self, output_dir='data/board_category'):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        self.boards = {}
        self.industry_hierarchy = {}
        self.stock_industries = {}
    
    def _request_with_retry(self, url, params, max_retries=3, timeout=10):
        """带重试的请求"""
        for i in range(max_retries):
            try:
                response = requests.get(url, params=params, headers=self.HEADERS, timeout=timeout)
                response.encoding = 'utf-8'
                return response.json()
            except Exception as e:
                if i < max_retries - 1:
                    time.sleep(1)
                else:
                    print(f"请求失败: {e}")
                    return None
    
    def get_all_boards(self, board_type, page_size=500):
        """获取指定类型的所有板块"""
        if board_type not in self.BOARD_TYPES:
            print(f"不支持的板块类型: {board_type}")
            return []
        
        type_info = self.BOARD_TYPES[board_type]
        print(f"\n正在获取{type_info['name']}列表...")
        
        all_boards = []
        page = 1
        
        while True:
            params = {
                'pn': str(page),
                'pz': str(page_size),
                'po': '1',
                'np': '1',
                'fltt': '2',
                'invt': '2',
                'fid': 'f3',
                'fs': type_info['fs'],
                'fields': 'f12,f13,f14,f2,f3,f4,f5,f6',
            }
            
            data = self._request_with_retry(self.CLIST_URL, params)
            
            if not data or not data.get('data') or not data['data'].get('diff'):
                break
            
            boards = data['data']['diff']
            for item in boards:
                all_boards.append({
                    'code': item.get('f12', ''),
                    'name': item.get('f14', ''),
                    'price': item.get('f2', 0),
                    'change_pct': item.get('f3', 0),
                    'change': item.get('f4', 0),
                    'volume': item.get('f5', 0),
                    'amount': item.get('f6', 0),
                })
            
            if len(boards) < page_size:
                break
            
            page += 1
            time.sleep(0.2)
        
        print(f"获取到 {len(all_boards)} 个{type_info['name']}")
        self.boards[board_type] = all_boards
        return all_boards
    
    def get_board_stocks(self, board_code, page_size=500):
        """获取板块成分股"""
        all_stocks = []
        page = 1
        
        while True:
            params = {
                'pn': str(page),
                'pz': str(page_size),
                'po': '1',
                'np': '1',
                'fltt': '2',
                'invt': '2',
                'fid': 'f3',
                'fs': f'b:{board_code}+f:!50',
                'fields': 'f12,f13,f14,f2,f3,f4,f5,f6',
            }
            
            data = self._request_with_retry(self.CLIST_URL, params)
            
            if not data or not data.get('data') or not data['data'].get('diff'):
                break
            
            stocks = data['data']['diff']
            for item in stocks:
                all_stocks.append({
                    'code': item.get('f12', ''),
                    'name': item.get('f14', ''),
                    'price': item.get('f2', 0),
                    'change_pct': item.get('f3', 0),
                    'change': item.get('f4', 0),
                    'volume': item.get('f5', 0),
                    'amount': item.get('f6', 0),
                })
            
            if len(stocks) < page_size:
                break
            
            page += 1
            time.sleep(0.1)
        
        return all_stocks
    
    def get_stock_industry_info(self, secid):
        """获取股票的行业信息"""
        params = {
            'secid': secid,
            'fields': 'f12,f14,f127,f128,f129',
        }
        
        data = self._request_with_retry(self.STOCK_URL, params)
        
        if not data or not data.get('data'):
            return None
        
        result = data['data']
        return {
            'code': result.get('f12', ''),
            'name': result.get('f14', ''),
            'industry': result.get('f127', ''),
            'region': result.get('f128', ''),
            'concepts': result.get('f129', ''),
        }
    
    def get_all_stocks_industry_info(self, market='all', page_size=500):
        """获取所有股票的行业信息"""
        print("\n正在获取所有股票的行业信息...")
        
        fs_map = {
            'all': 'm:0+t:6,m:1+t:23,m:0+t:80',
            'sh': 'm:1+t:23',
            'sz': 'm:0+t:6',
            'bj': 'm:0+t:80',
        }
        
        fs = fs_map.get(market, fs_map['all'])
        
        all_stocks = {}
        page = 1
        
        while True:
            params = {
                'pn': str(page),
                'pz': str(page_size),
                'po': '1',
                'np': '1',
                'fltt': '2',
                'invt': '2',
                'fid': 'f3',
                'fs': fs,
                'fields': 'f12,f13,f14',
            }
            
            data = self._request_with_retry(self.CLIST_URL, params)
            
            if not data or not data.get('data') or not data['data'].get('diff'):
                break
            
            stocks = data['data']['diff']
            for item in stocks:
                code = item.get('f12', '')
                market_code = item.get('f13', 0)
                secid = f"{market_code}.{code}"
                all_stocks[code] = {
                    'secid': secid,
                    'name': item.get('f14', ''),
                }
            
            if len(stocks) < page_size:
                break
            
            page += 1
            time.sleep(0.2)
        
        print(f"获取到 {len(all_stocks)} 只股票")
        
        print("正在获取股票行业详情...")
        count = 0
        total = len(all_stocks)
        
        for code, info in all_stocks.items():
            count += 1
            if count % 100 == 0:
                print(f"  进度: {count}/{total}")
            
            secid = info['secid']
            industry_info = self.get_stock_industry_info(secid)
            
            if industry_info:
                info['industry'] = industry_info.get('industry', '')
                info['region'] = industry_info.get('region', '')
                info['concepts'] = industry_info.get('concepts', '')
            
            time.sleep(0.05)
        
        self.stock_industries = all_stocks
        return all_stocks
    
    def build_industry_hierarchy(self):
        """构建行业层级关系"""
        print("\n正在分析行业层级关系...")
        
        industries = defaultdict(int)
        for code, info in self.stock_industries.items():
            industry = info.get('industry', '')
            if industry and isinstance(industry, str):
                industries[industry] += 1
        
        level1 = []
        level2 = []
        level3 = []
        other = []
        
        for ind, count in industries.items():
            if ind.endswith('Ⅰ'):
                level1.append({'name': ind, 'count': count})
            elif ind.endswith('Ⅱ'):
                level2.append({'name': ind, 'count': count})
            elif ind.endswith('Ⅲ'):
                level3.append({'name': ind, 'count': count})
            else:
                other.append({'name': ind, 'count': count})
        
        hierarchy = {
            'level1': sorted(level1, key=lambda x: x['name']),
            'level2': sorted(level2, key=lambda x: x['name']),
            'level3': sorted(level3, key=lambda x: x['name']),
            'other': sorted(other, key=lambda x: -x['count']),
            'relations': {},
        }
        
        for l2 in level2:
            base_name = l2['name'][:-1]
            l1_name = base_name + 'Ⅰ'
            
            found = False
            for l1 in level1:
                if l1['name'] == l1_name:
                    if l1['name'] not in hierarchy['relations']:
                        hierarchy['relations'][l1['name']] = []
                    hierarchy['relations'][l1['name']].append(l2['name'])
                    found = True
                    break
            
            if not found:
                if '未分类' not in hierarchy['relations']:
                    hierarchy['relations']['未分类'] = []
                hierarchy['relations']['未分类'].append(l2['name'])
        
        self.industry_hierarchy = hierarchy
        
        print(f"行业统计:")
        print(f"  一级行业: {len(level1)} 个")
        print(f"  二级行业: {len(level2)} 个")
        print(f"  三级行业: {len(level3)} 个")
        print(f"  其他行业: {len(other)} 个")
        
        return hierarchy
    
    def download_all_boards(self, include_stocks=True, sleep_interval=0.3):
        """下载所有板块数据"""
        print("=" * 60)
        print("东方财富板块分类数据下载")
        print("=" * 60)
        
        results = {}
        
        for board_type, type_info in self.BOARD_TYPES.items():
            print(f"\n--- {type_info['name']} ---")
            
            boards = self.get_all_boards(board_type)
            results[board_type] = {
                'board_count': len(boards),
                'stocks_downloaded': 0,
            }
            
            if include_stocks and boards:
                stocks_dir = os.path.join(self.output_dir, f'{board_type}_stocks')
                os.makedirs(stocks_dir, exist_ok=True)
                
                total_stocks = 0
                for i, board in enumerate(boards, 1):
                    code = board['code']
                    name = board['name']
                    
                    print(f"[{i}/{len(boards)}] {name}...", end=" ")
                    
                    stocks = self.get_board_stocks(code)
                    
                    if stocks:
                        total_stocks += len(stocks)
                        print(f"OK {len(stocks)}只")
                        
                        filepath = os.path.join(stocks_dir, f"{code}.json")
                        with open(filepath, 'w', encoding='utf-8') as f:
                            json.dump({
                                'code': code,
                                'name': name,
                                'stocks': stocks,
                                'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            }, f, ensure_ascii=False, indent=2)
                    else:
                        print("FAIL")
                    
                    time.sleep(sleep_interval)
                
                results[board_type]['stocks_downloaded'] = total_stocks
        
        return results
    
    def save_all_data(self):
        """保存所有数据到文件"""
        print("\n正在保存数据...")
        
        for board_type, boards in self.boards.items():
            filepath = os.path.join(self.output_dir, f'{board_type}_boards.json')
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump({
                    'type': board_type,
                    'type_name': self.BOARD_TYPES[board_type]['name'],
                    'count': len(boards),
                    'boards': boards,
                    'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                }, f, ensure_ascii=False, indent=2)
            print(f"  已保存: {filepath}")
        
        if self.stock_industries:
            filepath = os.path.join(self.output_dir, 'stock_industries.json')
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump({
                    'count': len(self.stock_industries),
                    'stocks': self.stock_industries,
                    'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                }, f, ensure_ascii=False, indent=2)
            print(f"  已保存: {filepath}")
        
        if self.industry_hierarchy:
            filepath = os.path.join(self.output_dir, 'industry_hierarchy.json')
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump({
                    'hierarchy': self.industry_hierarchy,
                    'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                }, f, ensure_ascii=False, indent=2)
            print(f"  已保存: {filepath}")
        
        summary = {
            'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'board_counts': {t: len(b) for t, b in self.boards.items()},
            'stock_count': len(self.stock_industries),
        }
        filepath = os.path.join(self.output_dir, 'summary.json')
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        print(f"  已保存: {filepath}")
    
    def print_summary(self):
        """打印汇总信息"""
        print("\n" + "=" * 60)
        print("下载完成汇总")
        print("=" * 60)
        
        for board_type, boards in self.boards.items():
            type_name = self.BOARD_TYPES[board_type]['name']
            print(f"\n{type_name}: {len(boards)} 个")
        
        if self.stock_industries:
            print(f"\n股票行业信息: {len(self.stock_industries)} 只")
        
        if self.industry_hierarchy:
            print(f"\n行业层级:")
            print(f"  一级行业: {len(self.industry_hierarchy.get('level1', []))} 个")
            print(f"  二级行业: {len(self.industry_hierarchy.get('level2', []))} 个")
            print(f"  三级行业: {len(self.industry_hierarchy.get('level3', []))} 个")
            print(f"  其他行业: {len(self.industry_hierarchy.get('other', []))} 个")


def main():
    """主函数"""
    print("=" * 60)
    print("东方财富板块分类数据下载器")
    print("=" * 60)
    
    print("\n选择操作:")
    print("1. 下载所有板块数据（含成分股）")
    print("2. 仅下载板块列表（不含成分股）")
    print("3. 下载板块列表 + 股票行业信息")
    print("4. 仅获取股票行业信息")
    print("5. 全量下载（板块 + 成分股 + 行业信息）")
    
    choice = input("\n请输入选项 (1-5): ").strip()
    
    downloader = BoardCategoryDownloader()
    
    if choice == '1':
        downloader.download_all_boards(include_stocks=True)
        downloader.save_all_data()
    
    elif choice == '2':
        downloader.download_all_boards(include_stocks=False)
        downloader.save_all_data()
    
    elif choice == '3':
        downloader.download_all_boards(include_stocks=False)
        downloader.get_all_stocks_industry_info()
        downloader.build_industry_hierarchy()
        downloader.save_all_data()
    
    elif choice == '4':
        downloader.get_all_stocks_industry_info()
        downloader.build_industry_hierarchy()
        downloader.save_all_data()
    
    elif choice == '5':
        downloader.download_all_boards(include_stocks=True)
        downloader.get_all_stocks_industry_info()
        downloader.build_industry_hierarchy()
        downloader.save_all_data()
    
    else:
        print("无效选项")
        return
    
    downloader.print_summary()
    print(f"\n数据保存目录: {downloader.output_dir}")


if __name__ == '__main__':
    main()
