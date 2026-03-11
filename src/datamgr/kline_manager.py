import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import STOCKS_CONFIG_PATH
from downloaders.eastmoney_downloader import EastMoneyDownloader
from .store import KLineStore, ConfigStore
from .cache import KLineCache, ConfigCache


class KLineManager:
    """
    K线数据管理器
    
    功能:
    1. 从配置文件获取股票列表
    2. 检查本地K线数据是否存在
    3. 加载本地K线数据
    4. 自动下载缺失或不足的K线数据
    
    数据源: 东方财富API
    
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
        self.downloader = EastMoneyDownloader()
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
    
    def download_kline_data(self, symbol, market, period):
        period_name = self.PERIODS.get(period, {}).get('name', period)
        days = self.PERIODS.get(period, {}).get('days', 365)
        
        print(f"正在下载 {symbol} ({market}) {period_name} 数据...")
        
        if market == 'A股':
            data = self.downloader.download_kline(symbol, period=period, days=days)
            if data is not None:
                self.store.save(symbol, 'CN', period, data)
                self.kline_cache.delete_kline(symbol, market, period)
                return True
        else:
            print(f"暂不支持 {market} 市场的数据下载")
            return False
        
        return False
    
    def _parse_latest_date(self, latest_date_str, period):
        from datetime import datetime
        
        if not latest_date_str:
            return None
        
        try:
            latest_str = str(latest_date_str).strip()
            
            if ' ' not in latest_str:
                return datetime.strptime(latest_str, '%Y-%m-%d')
            
            if '.' in latest_str:
                latest_str = latest_str.split('.')[0]
            
            time_formats = [
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%d %H:%M',
            ]
            
            for fmt in time_formats:
                try:
                    return datetime.strptime(latest_str, fmt)
                except ValueError:
                    continue
            
            print(f"解析日期失败: {latest_date_str}, 不支持的格式")
            return None
            
        except Exception as e:
            print(f"解析日期失败: {latest_date_str}, {e}")
            return None
    
    def _calc_start_date(self, latest_date, period):
        from datetime import timedelta
        
        if latest_date is None:
            return None
        
        if period == 'daily':
            start_date = latest_date + timedelta(days=1)
        else:
            start_date = latest_date + timedelta(minutes=1)
        
        return start_date.strftime('%Y%m%d')
    
    def _need_update(self, latest_date, period, filepath=None):
        from datetime import datetime, timedelta
        
        if latest_date is None:
            return True
        
        now = datetime.now()
        
        if period == 'daily':
            today_end = datetime(now.year, now.month, now.day, 15, 0, 0)
            if latest_date >= today_end:
                return False
            if now.hour < 15 and latest_date.date() == now.date():
                return False
            
            if filepath and os.path.exists(filepath):
                file_mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
                cutoff_time = datetime(now.year, now.month, now.day, 15, 30, 0)
                
                if (latest_date.date() == now.date() and 
                    file_mtime >= cutoff_time):
                    return False
        else:
            if latest_date >= now - timedelta(minutes=5):
                return False
            
            if filepath and os.path.exists(filepath):
                file_mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
                cutoff_time = datetime(now.year, now.month, now.day, 15, 30, 0)
                
                latest_date_str = latest_date.strftime('%Y-%m-%d')
                today_str = now.strftime('%Y-%m-%d')
                
                if (latest_date_str == today_str and 
                    file_mtime >= cutoff_time):
                    return False
        
        return True
    
    def _merge_and_save(self, symbol, market, period, new_data):
        import pandas as pd
        
        if not new_data:
            print(f"{symbol} {period} 无新数据需要合并")
            return False
        
        filepath = self.store.get_filepath(symbol, market, period)
        
        try:
            old_df = None
            if os.path.exists(filepath):
                old_df = pd.read_csv(filepath)
            
            new_df = pd.DataFrame(new_data)
            
            if old_df is not None and len(old_df) > 0:
                combined_df = pd.concat([old_df, new_df], ignore_index=True)
                combined_df['date'] = combined_df['date'].astype(str)
                combined_df = combined_df.drop_duplicates(subset=['date'], keep='last')
                combined_df = combined_df.sort_values('date')
            else:
                combined_df = new_df
                combined_df['date'] = combined_df['date'].astype(str)
                combined_df = combined_df.sort_values('date')
            
            self.store.save(symbol, market, period, combined_df)
            self.kline_cache.delete_kline(symbol, market, period)
            
            print(f"{symbol} {period} 增量更新完成: 新增 {len(new_data)} 条，合并后共 {len(combined_df)} 条")
            return True
            
        except Exception as e:
            print(f"合并数据失败: {e}")
            return False
    
    def update_kline_data(self, symbol, market, period):
        period_name = self.PERIODS.get(period, {}).get('name', period)
        
        if market != 'A股':
            print(f"暂不支持 {market} 市场的增量更新")
            return False
        
        local_info = self.check_local_data(symbol, market, period)
        
        if not local_info['exists'] or not local_info['latest_date']:
            print(f"{symbol} {period_name} 本地无数据，执行全量下载...")
            return self.download_kline_data(symbol, market, period)
        
        latest_date = self._parse_latest_date(local_info['latest_date'], period)
        
        if latest_date is None:
            print(f"{symbol} {period_name} 解析日期失败，执行全量下载...")
            return self.download_kline_data(symbol, market, period)
        
        filepath = local_info.get('filepath')
        if not self._need_update(latest_date, period, filepath):
            print(f"{symbol} {period_name} 数据已是最新，跳过更新")
            return True
        
        start_date = self._calc_start_date(latest_date, period)
        from datetime import datetime
        end_date = datetime.now().strftime('%Y%m%d')
        
        print(f"{symbol} {period_name} 增量更新: {start_date} -> {end_date}")
        
        new_data = self.downloader.download_kline(
            symbol, 
            period=period, 
            start_date=start_date, 
            end_date=end_date
        )
        
        if new_data is None or len(new_data) == 0:
            print(f"{symbol} {period_name} 无新数据")
            return True
        
        return self._merge_and_save(symbol, market, period, new_data)
    
    def sync_all_stocks_incremental(self, periods=None):
        if not self.stock_list:
            self.load_stock_list()
        
        if not self.stock_list:
            print("没有配置任何股票")
            return {}
        
        if periods is None:
            periods = list(self.PERIODS.keys())
        
        results = {
            'success': [],
            'failed': [],
            'skipped': [],
            'details': {}
        }
        
        total = len(self.stock_list)
        
        for i, stock in enumerate(self.stock_list, 1):
            symbol = stock.get('symbol')
            market = stock.get('market', 'A股')
            name = stock.get('name', '')
            
            print(f"\n{'='*60}")
            print(f"[{i}/{total}] 增量更新: {symbol} - {name} ({market})")
            print(f"{'='*60}")
            
            stock_result = {'market': market, 'periods': {}}
            all_success = True
            all_skipped = True
            
            for period in periods:
                period_name = self.PERIODS.get(period, {}).get('name', period)
                
                try:
                    local_info = self.check_local_data(symbol, market, period)
                    
                    if not local_info['exists']:
                        print(f"{symbol} {period_name} 本地无数据，执行全量下载...")
                        success = self.download_kline_data(symbol, market, period)
                        all_skipped = False
                    else:
                        success = self.update_kline_data(symbol, market, period)
                    
                    stock_result['periods'][period] = success
                    
                    if not success:
                        all_success = False
                        all_skipped = False
                        
                except Exception as e:
                    print(f"{symbol} {period_name} 更新失败: {e}")
                    stock_result['periods'][period] = False
                    all_success = False
                    all_skipped = False
            
            if all_success:
                if all_skipped:
                    results['skipped'].append(symbol)
                else:
                    results['success'].append(symbol)
            else:
                results['failed'].append(symbol)
            
            results['details'][symbol] = stock_result
        
        print(f"\n{'='*60}")
        print("增量同步完成")
        print(f"成功: {len(results['success'])} 只")
        print(f"跳过: {len(results['skipped'])} 只 (已是最新)")
        print(f"失败: {len(results['failed'])} 只")
        if results['failed']:
            print(f"失败股票: {', '.join(results['failed'][:20])}{'...' if len(results['failed']) > 20 else ''}")
        print(f"{'='*60}")
        
        return results
    
    def ensure_kline_data(self, symbol, market, periods=None, force_download=False):
        if periods is None:
            periods = list(self.PERIODS.keys())
        
        results = {}
        
        for period in periods:
            if force_download:
                need_download = True
            else:
                is_sufficient, local_info = self.is_data_sufficient(symbol, market, period)
                need_download = not is_sufficient
                
                if not is_sufficient:
                    period_name = self.PERIODS.get(period, {}).get('name', period)
                    print(f"{symbol} {period_name}数据不足 (现有{local_info['count']}条)，需要下载")
            
            if need_download:
                success = self.download_kline_data(symbol, market, period)
                if not success:
                    results[period] = None
                    continue
            
            df = self.load_kline_data(symbol, market, period)
            results[period] = df
        
        return results
    
    def sync_all_stocks(self, periods=None, force_download=False):
        if not self.stock_list:
            self.load_stock_list()
        
        if not self.stock_list:
            print("没有配置任何股票")
            return {}
        
        results = {
            'success': [],
            'failed': [],
            'details': {}
        }
        
        total = len(self.stock_list)
        
        for i, stock in enumerate(self.stock_list, 1):
            symbol = stock.get('symbol')
            market = stock.get('market', 'A股')
            name = stock.get('name', '')
            
            print(f"\n{'='*60}")
            print(f"[{i}/{total}] 处理: {symbol} - {name} ({market})")
            print(f"{'='*60}")
            
            try:
                data = self.ensure_kline_data(symbol, market, periods, force_download)
                
                all_success = all(df is not None for df in data.values())
                
                if all_success:
                    results['success'].append(symbol)
                else:
                    results['failed'].append(symbol)
                
                results['details'][symbol] = {
                    'market': market,
                    'periods': {p: df is not None for p, df in data.items()}
                }
                
            except Exception as e:
                print(f"处理失败: {e}")
                results['failed'].append(symbol)
                results['details'][symbol] = {'error': str(e)}
        
        print(f"\n{'='*60}")
        print("同步完成")
        print(f"成功: {len(results['success'])} 只")
        print(f"失败: {len(results['failed'])} 只")
        if results['failed']:
            print(f"失败股票: {', '.join(results['failed'])}")
        print(f"{'='*60}")
        
        return results
    
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
