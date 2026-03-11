import os
from .store import KLineStore
from .cache import KLineCache


class KLineManager:
    """
    K线数据管理器
    
    功能:
    1. 检查本地K线数据是否存在
    2. 加载/保存K线数据
    3. 管理K线数据缓存
    
    目录结构:
    data/kline_data/
    ├── CN_600519/
    │   ├── 1min.csv
    │   ├── 5min.csv
    │   ├── 15min.csv
    │   ├── 1hour.csv
    │   └── daily.csv
    """
    
    PERIODS = {
        '1min': {'days': 5, 'name': '1分钟'},
        '5min': {'days': 10, 'name': '5分钟'},
        '15min': {'days': 20, 'name': '15分钟'},
        '1hour': {'days': 30, 'name': '1小时'},
        'daily': {'days': 365, 'name': '日线'}
    }
    
    COLUMNS = [
        'date', 'open', 'close', 'high', 'low',
        'volume', 'amount', 'amplitude', 'change_pct', 'change', 'turnover'
    ]
    
    def __init__(self, data_dir=None):
        if data_dir is None:
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            data_dir = os.path.join(project_root, 'data', 'kline_data')
        
        self.store = KLineStore(data_dir)
        self.cache = KLineCache()
    
    def get_data(self, symbol, market, period, limit=None):
        """
        获取K线数据
        
        Args:
            symbol: 股票代码
            market: 市场
            period: 周期
            limit: 返回最近N条数据
        
        Returns:
            DataFrame: K线数据
        """
        cached = self.cache.get_kline(symbol, market, period)
        if cached is not None:
            if limit and len(cached) > limit:
                return cached.tail(limit).reset_index(drop=True)
            return cached.copy()
        
        df = self.store.load(symbol, market, period, limit)
        if df is not None and not df.empty:
            self.cache.set_kline(symbol, market, period, df)
        return df
    
    def save_data(self, symbol, market, period, data):
        """
        保存K线数据
        
        Args:
            symbol: 股票代码
            market: 市场
            period: 周期
            data: K线数据列表或DataFrame
        
        Returns:
            bool: 是否成功
        """
        success = self.store.save(symbol, market, period, data)
        if success:
            self.cache.delete_kline(symbol, market, period)
        return success
    
    def append_data(self, symbol, market, period, data):
        """
        追加K线数据
        
        Args:
            symbol: 股票代码
            market: 市场
            period: 周期
            data: 单条K线数据字典或列表
        
        Returns:
            bool: 是否成功
        """
        success = self.store.append(symbol, market, period, data)
        if success:
            self.cache.delete_kline(symbol, market, period)
        return success
    
    def exists(self, symbol, market, period):
        """
        检查K线数据是否存在
        """
        return self.store.exists(symbol, market, period)
    
    def delete(self, symbol, market, period=None):
        """
        删除K线数据
        
        Args:
            symbol: 股票代码
            market: 市场
            period: 周期，None表示删除该股票所有周期数据
        """
        return self.store.delete(symbol, market, period)
    
    def get_latest_date(self, symbol, market, period):
        """
        获取K线数据最新日期
        """
        return self.store.get_latest_date(symbol, market, period)
    
    def get_data_info(self, symbol, market, period):
        """
        获取K线数据信息
        """
        return self.store.get_data_info(symbol, market, period)
    
    def is_data_sufficient(self, symbol, market, period, min_records=None):
        """
        检查数据是否充足
        
        Args:
            symbol: 股票代码
            market: 市场
            period: 周期
            min_records: 最小记录数
        
        Returns:
            tuple: (是否充足, 数据信息)
        """
        local_info = self.get_data_info(symbol, market, period)
        
        if not local_info['exists']:
            return False, local_info
        
        if min_records is None:
            min_records = self.PERIODS.get(period, {}).get('days', 30)
        
        if local_info['count'] < min_records * 0.5:
            return False, local_info
        
        if local_info['latest_date']:
            from datetime import datetime
            try:
                latest_str = str(local_info['latest_date'])
                if ' ' in latest_str:
                    latest = datetime.strptime(latest_str.split('.')[0], '%Y-%m-%d %H:%M:%S')
                else:
                    latest = datetime.strptime(latest_str, '%Y-%m-%d')
                days_ago = (datetime.now() - latest).days
                
                if period == 'daily' and days_ago > 7:
                    return False, local_info
                elif period != 'daily' and days_ago > 3:
                    return False, local_info
            except:
                pass
        
        return True, local_info
    
    def get_all_periods_data(self, symbol, market):
        """
        获取所有周期的K线数据
        
        Args:
            symbol: 股票代码
            market: 市场
        
        Returns:
            dict: {period: DataFrame}
        """
        result = {}
        for period in self.PERIODS.keys():
            df = self.get_data(symbol, market, period)
            if df is not None and not df.empty:
                result[period] = df
        return result
    
    def list_stocks(self):
        """
        列出所有有K线数据的股票
        """
        return self.store.list_stocks()
    
    def clear_cache(self):
        """
        清空内存缓存
        """
        self.cache.clear()
