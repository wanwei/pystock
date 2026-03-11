from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field


@dataclass
class FilterCondition:
    search: str = ''
    markets: List[str] = field(default_factory=list)
    sectors: List[Dict[str, str]] = field(default_factory=list)
    exclude_st: bool = True
    min_price: Optional[float] = None
    max_price: Optional[float] = None


class StockFilter:
    """
    股票筛选器
    
    第一阶段筛选：通过代码/名称/板块/市场等条件过滤股票
    
    使用示例:
        filter = StockFilter(stock_manager, sector_manager)
        
        condition = FilterCondition(
            search='茅台',
            markets=['A股'],
            sectors=[{'type': 'industry', 'code': 'BK0475'}]
        )
        
        results = filter.filter(condition)
    """
    
    MARKETS = ['A股', '美股', '港股']
    
    ST_PREFIXES = ('ST', '*ST', 'S*ST', 'SST', 'S')
    
    def __init__(self, stock_manager, sector_manager=None):
        self.stock_manager = stock_manager
        self.sector_manager = sector_manager
        self._all_stocks_cache: Optional[List[Dict]] = None
    
    def _get_all_stocks(self) -> List[Dict]:
        if self._all_stocks_cache is not None:
            return self._all_stocks_cache
        
        stocks = self.stock_manager.get_stock_list()
        self._all_stocks_cache = stocks
        return stocks
    
    def refresh_cache(self):
        self._all_stocks_cache = None
    
    def filter(self, condition: FilterCondition) -> List[Dict]:
        stocks = self._get_all_stocks()
        
        if condition.search:
            stocks = self._filter_by_search(stocks, condition.search)
        
        if condition.markets:
            stocks = self._filter_by_markets(stocks, condition.markets)
        
        if condition.sectors:
            stocks = self._filter_by_sectors(stocks, condition.sectors)
        
        if condition.exclude_st:
            stocks = self._filter_exclude_st(stocks)
        
        if condition.min_price is not None or condition.max_price is not None:
            stocks = self._filter_by_price_range(
                stocks, 
                condition.min_price, 
                condition.max_price
            )
        
        return stocks
    
    def _filter_by_search(self, stocks: List[Dict], keyword: str) -> List[Dict]:
        if not keyword:
            return stocks
        
        keyword = keyword.strip().lower()
        results = []
        
        for stock in stocks:
            symbol = str(stock.get('symbol', '')).lower()
            name = str(stock.get('name', '')).lower()
            
            if keyword in symbol or keyword in name:
                results.append(stock)
        
        return results
    
    def _filter_by_markets(self, stocks: List[Dict], markets: List[str]) -> List[Dict]:
        if not markets:
            return stocks
        
        return [s for s in stocks if s.get('market') in markets]
    
    def _filter_by_sectors(self, stocks: List[Dict], sectors: List[Dict]) -> List[Dict]:
        if not sectors or not self.sector_manager:
            return stocks
        
        sector_stock_codes = set()
        
        for sector in sectors:
            sector_type = sector.get('type', 'industry')
            sector_code = sector.get('code')
            
            if not sector_code:
                continue
            
            sector_stocks = self.sector_manager.load_sector_stocks(sector_type, sector_code)
            for s in sector_stocks:
                code = s.get('code', '')
                if code:
                    sector_stock_codes.add(code)
        
        if not sector_stock_codes:
            return stocks
        
        results = []
        for stock in stocks:
            symbol = stock.get('symbol', '')
            if symbol in sector_stock_codes:
                results.append(stock)
        
        return results
    
    def _filter_exclude_st(self, stocks: List[Dict]) -> List[Dict]:
        results = []
        
        for stock in stocks:
            name = stock.get('name', '')
            if not name:
                results.append(stock)
                continue
            
            is_st = False
            for prefix in self.ST_PREFIXES:
                if name.startswith(prefix):
                    is_st = True
                    break
            
            if not is_st:
                results.append(stock)
        
        return results
    
    def _filter_by_price_range(
        self, 
        stocks: List[Dict], 
        min_price: Optional[float], 
        max_price: Optional[float]
    ) -> List[Dict]:
        results = []
        
        for stock in stocks:
            price = stock.get('price')
            
            if price is None:
                continue
            
            try:
                price = float(price)
            except (ValueError, TypeError):
                continue
            
            if min_price is not None and price < min_price:
                continue
            
            if max_price is not None and price > max_price:
                continue
            
            results.append(stock)
        
        return results
    
    def filter_with_callback(
        self, 
        condition: FilterCondition,
        callback: Callable[[int, int, List[Dict]], None] = None
    ) -> List[Dict]:
        stocks = self._get_all_stocks()
        total = len(stocks)
        results = stocks
        
        step = 0
        total_steps = sum([
            1 if condition.search else 0,
            1 if condition.markets else 0,
            1 if condition.sectors else 0,
            1 if condition.exclude_st else 0,
            1 if (condition.min_price or condition.max_price) else 0
        ])
        
        if callback:
            callback(step, total_steps, results)
        
        if condition.search:
            results = self._filter_by_search(results, condition.search)
            step += 1
            if callback:
                callback(step, total_steps, results)
        
        if condition.markets:
            results = self._filter_by_markets(results, condition.markets)
            step += 1
            if callback:
                callback(step, total_steps, results)
        
        if condition.sectors:
            results = self._filter_by_sectors(results, condition.sectors)
            step += 1
            if callback:
                callback(step, total_steps, results)
        
        if condition.exclude_st:
            results = self._filter_exclude_st(results)
            step += 1
            if callback:
                callback(step, total_steps, results)
        
        if condition.min_price is not None or condition.max_price is not None:
            results = self._filter_by_price_range(
                results, 
                condition.min_price, 
                condition.max_price
            )
            step += 1
            if callback:
                callback(step, total_steps, results)
        
        return results
    
    def get_available_markets(self) -> List[str]:
        return self.MARKETS.copy()
    
    def get_available_sectors(self, sector_type: str = 'industry') -> List[Dict]:
        if not self.sector_manager:
            return []
        
        return self.sector_manager.load_sectors(sector_type)
    
    def get_filter_statistics(self, condition: FilterCondition) -> Dict[str, Any]:
        all_stocks = self._get_all_stocks()
        
        stats = {
            'total': len(all_stocks),
            'filtered': 0,
            'filters_applied': [],
            'by_market': {},
            'by_sector': {}
        }
        
        for market in self.MARKETS:
            count = len([s for s in all_stocks if s.get('market') == market])
            stats['by_market'][market] = count
        
        results = self.filter(condition)
        stats['filtered'] = len(results)
        
        if condition.search:
            stats['filters_applied'].append(f"搜索: {condition.search}")
        if condition.markets:
            stats['filters_applied'].append(f"市场: {', '.join(condition.markets)}")
        if condition.sectors:
            sector_names = [s.get('name', s.get('code', '')) for s in condition.sectors]
            stats['filters_applied'].append(f"板块: {', '.join(sector_names)}")
        if condition.exclude_st:
            stats['filters_applied'].append("排除ST")
        if condition.min_price is not None:
            stats['filters_applied'].append(f"最低价: {condition.min_price}")
        if condition.max_price is not None:
            stats['filters_applied'].append(f"最高价: {condition.max_price}")
        
        return stats


if __name__ == "__main__":
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    from datamgr.stock_manager import StockDataManager
    from datamgr.sector_manager import SectorManager
    
    print("=" * 60)
    print("股票筛选器测试")
    print("=" * 60)
    
    stock_mgr = StockDataManager()
    sector_mgr = SectorManager()
    
    filter_obj = StockFilter(stock_mgr, sector_mgr)
    
    print("\n1. 测试基础搜索...")
    condition = FilterCondition(search='茅台')
    results = filter_obj.filter(condition)
    print(f"   搜索'茅台': 找到 {len(results)} 只股票")
    for r in results[:5]:
        print(f"   - {r.get('symbol')} {r.get('name')}")
    
    print("\n2. 测试市场筛选...")
    condition = FilterCondition(markets=['A股'])
    results = filter_obj.filter(condition)
    print(f"   A股市场: 找到 {len(results)} 只股票")
    
    print("\n3. 测试组合筛选...")
    condition = FilterCondition(
        markets=['A股'],
        exclude_st=True
    )
    results = filter_obj.filter(condition)
    print(f"   A股 + 排除ST: 找到 {len(results)} 只股票")
    
    print("\n4. 测试筛选统计...")
    stats = filter_obj.get_filter_statistics(condition)
    print(f"   总股票数: {stats['total']}")
    print(f"   筛选后数量: {stats['filtered']}")
    print(f"   应用条件: {stats['filters_applied']}")
