import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .store import KLineStore, ConfigStore
from .cache import KLineCache, ConfigCache


class KLineManager:
    """
    K线数据管理器
    
    功能:
    1. 从配置文件获取股票列表
    2. 检查本地K线数据是否存在
    3. 加载本地K线数据
    4. 管理K线数据缓存
    
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
    
    def __init__(self, data_dir=None):
        if data_dir is None:
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            data_dir = os.path.join(project_root, 'data', 'kline_data')
            config_dir = os.path.join(project_root, 'config')
        else:
            config_dir = os.path.dirname(data_dir)
        
        self.store = KLineStore(data_dir)
        self.config_store = ConfigStore(config_dir)
        self.kline_cache = KLineCache()
        self.config_cache = ConfigCache()
        self.stock_list = []
        
    def load_stock_list(self):
        config = self.config_store.load()
        self.stock_list = config.get('stocks', [])
        print(f"已加载 {len(self.stock_list)} 只股票")
        return self.stock_list
    
    def check_local_data(self, symbol, market, period):
        return self.store.get_data_info(symbol, market, period)
    
    def is_data_sufficient(self, symbol, market, period, min_records=None):
        local_info = self.check_local_data(symbol, market, period)
        
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
    
    def load_kline_data(self, symbol, market, period):
        cached = self.kline_cache.get_kline(symbol, market, period)
        if cached is not None:
            return cached
        
        df = self.store.load(symbol, market, period)
        if df is not None and not df.empty:
            self.kline_cache.set_kline(symbol, market, period, df)
        return df
    
    def save_kline_data(self, symbol, market, period, data):
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
            self.kline_cache.delete_kline(symbol, market, period)
        return success
    
    def get_kline_data(self, symbol, market, period):
        return self.load_kline_data(symbol, market, period)
    
    def get_all_kline_data(self, symbol, market):
        result = {}
        for period in self.PERIODS.keys():
            df = self.get_kline_data(symbol, market, period)
            if df is not None:
                result[period] = df
        return result
    
    def show_data_status(self):
        if not self.stock_list:
            self.load_stock_list()
        
        print(f"\n{'='*100}")
        print(f"{'代码':<10} {'名称':<12} {'市场':<8} {'1分钟':<10} {'5分钟':<10} {'15分钟':<10} {'1小时':<10} {'日线':<10}")
        print(f"{'='*100}")
        
        for stock in self.stock_list:
            symbol = stock.get('symbol')
            name = stock.get('name', '')
            market = stock.get('market', 'A股')
            
            status = []
            for period in ['1min', '5min', '15min', '1hour', 'daily']:
                is_sufficient, info = self.is_data_sufficient(symbol, market, period)
                if is_sufficient:
                    status.append(f"OK {info['count']}")
                elif info['exists']:
                    status.append(f"~ {info['count']}")
                else:
                    status.append("X None")
            
            print(f"{symbol:<10} {name:<12} {market:<8} {status[0]:<10} {status[1]:<10} {status[2]:<10} {status[3]:<10} {status[4]:<10}")
        
        print(f"{'='*100}")
        print("Status: OK=sufficient, ~=insufficient, X=none")
    
    def list_stock_directories(self):
        return self.store.list_stocks()
    
    def clear_cache(self):
        self.kline_cache.clear()
        self.config_cache.clear()
