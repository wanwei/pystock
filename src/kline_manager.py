import os
import json
import pandas as pd
from datetime import datetime, timedelta
from config import STOCKS_CONFIG_PATH
from downloaders.eastmoney_downloader import EastMoneyDownloader


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
    
    def __init__(self, data_dir='data/kline_data'):
        self.data_dir = data_dir
        self.config_path = STOCKS_CONFIG_PATH
        self.downloader = EastMoneyDownloader()
        self.stock_list = []
        self.kline_data = {}
        
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
    
    def load_stock_list(self):
        if not os.path.exists(self.config_path):
            print(f"配置文件不存在: {self.config_path}")
            return []
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            self.stock_list = config.get('stocks', [])
            print(f"已加载 {len(self.stock_list)} 只股票")
            return self.stock_list
            
        except Exception as e:
            print(f"加载配置文件失败: {e}")
            return []
    
    def _get_stock_dir(self, symbol, market):
        market_code = 'US' if market == '美股' else 'CN'
        stock_dir = os.path.join(self.data_dir, f"{market_code}_{symbol}")
        return stock_dir
    
    def _get_data_filepath(self, symbol, market, period):
        stock_dir = self._get_stock_dir(symbol, market)
        filename = f"{period}.csv"
        return os.path.join(stock_dir, filename)
    
    def _ensure_stock_dir(self, symbol, market):
        stock_dir = self._get_stock_dir(symbol, market)
        if not os.path.exists(stock_dir):
            os.makedirs(stock_dir)
        return stock_dir
    
    def check_local_data(self, symbol, market, period):
        filepath = self._get_data_filepath(symbol, market, period)
        
        if not os.path.exists(filepath):
            return {
                'exists': False,
                'count': 0,
                'latest_date': None,
                'filepath': None
            }
        
        try:
            df = pd.read_csv(filepath)
            count = len(df)
            latest_date = df['date'].max() if 'date' in df.columns else None
            
            return {
                'exists': True,
                'count': count,
                'latest_date': latest_date,
                'filepath': filepath
            }
        except Exception as e:
            print(f"读取文件失败 {filepath}: {e}")
            return {
                'exists': False,
                'count': 0,
                'latest_date': None,
                'filepath': None
            }
    
    def is_data_sufficient(self, symbol, market, period, min_records=None):
        local_info = self.check_local_data(symbol, market, period)
        
        if not local_info['exists']:
            return False, local_info
        
        if min_records is None:
            min_records = self.PERIODS.get(period, {}).get('days', 30)
        
        if local_info['count'] < min_records * 0.5:
            return False, local_info
        
        if local_info['latest_date']:
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
        filepath = self._get_data_filepath(symbol, market, period)
        
        if not os.path.exists(filepath):
            return None
        
        try:
            df = pd.read_csv(filepath)
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])
                df = df.sort_values('date')
            return df
        except Exception as e:
            print(f"加载数据失败 {filepath}: {e}")
            return None
    
    def download_kline_data(self, symbol, market, period):
        period_name = self.PERIODS.get(period, {}).get('name', period)
        days = self.PERIODS.get(period, {}).get('days', 365)
        
        print(f"正在下载 {symbol} ({market}) {period_name} 数据...")
        
        if market == 'A股':
            data = self.downloader.download_kline(symbol, period=period, days=days)
            if data is not None:
                self._save_kline_data(symbol, 'CN', period, data)
                return True
        else:
            print(f"暂不支持 {market} 市场的数据下载")
            return False
        
        return False
    
    def _save_kline_data(self, symbol, market, period, data):
        if not data:
            return
        
        stock_dir = self._ensure_stock_dir(symbol, '美股' if market == 'US' else 'A股')
        filename = f"{period}.csv"
        filepath = os.path.join(stock_dir, filename)
        
        df = pd.DataFrame(data)
        df.to_csv(filepath, index=False, encoding='utf-8')
        print(f"数据已保存: {filepath}")
    
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
        key = f"{symbol}_{market}_{period}"
        
        if key in self.kline_data:
            return self.kline_data[key]
        
        df = self.load_kline_data(symbol, market, period)
        
        if df is not None:
            self.kline_data[key] = df
        
        return df
    
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
        if not os.path.exists(self.data_dir):
            return []
        
        stock_dirs = []
        for item in os.listdir(self.data_dir):
            item_path = os.path.join(self.data_dir, item)
            if os.path.isdir(item_path):
                stock_dirs.append(item)
        
        return sorted(stock_dirs)


if __name__ == "__main__":
    manager = KLineManager()
    
    print("="*60)
    print("K线数据管理器")
    print("数据源: 东方财富API")
    print("="*60)
    
    while True:
        print("\n请选择操作:")
        print("1. 查看数据状态")
        print("2. 同步所有股票数据")
        print("3. 下载单只股票数据")
        print("4. 强制重新下载所有数据")
        print("5. 查看本地股票目录")
        print("6. 退出")
        
        choice = input("\n请输入选项 (1-6): ").strip()
        
        if choice == '1':
            manager.show_data_status()
        
        elif choice == '2':
            print("\n选择要同步的周期:")
            print("1. 全部周期 (1分、5分、15分、1小时、日线)")
            print("2. 仅日线")
            print("3. 日线 + 1小时")
            print("4. 自定义")
            
            sub_choice = input("请选择 (1-4): ").strip()
            
            if sub_choice == '1':
                periods = None
            elif sub_choice == '2':
                periods = ['daily']
            elif sub_choice == '3':
                periods = ['daily', '1hour']
            elif sub_choice == '4':
                custom = input("输入周期 (用逗号分隔，如: daily,1hour,15min): ").strip()
                periods = [p.strip() for p in custom.split(',')]
            else:
                periods = None
            
            manager.sync_all_stocks(periods=periods)
        
        elif choice == '3':
            manager.load_stock_list()
            symbol = input("请输入股票代码: ").strip()
            market = input("请输入市场 (美股/A股): ").strip() or 'A股'
            
            print("\n可选周期: 1min, 5min, 15min, 1hour, daily")
            custom = input("输入周期 (用逗号分隔，默认全部): ").strip()
            if custom:
                periods = [p.strip() for p in custom.split(',')]
            else:
                periods = None
            
            manager.ensure_kline_data(symbol, market, periods)
        
        elif choice == '4':
            confirm = input("确定要强制重新下载所有数据吗? (y/n): ").strip().lower()
            if confirm == 'y':
                manager.sync_all_stocks(force_download=True)
        
        elif choice == '5':
            stock_dirs = manager.list_stock_directories()
            if stock_dirs:
                print(f"\n本地股票数据目录 ({len(stock_dirs)} 个):")
                for d in stock_dirs:
                    print(f"  - {d}")
            else:
                print("\n暂无本地数据目录")
        
        elif choice == '6':
            print("再见！")
            break
        
        else:
            print("无效选项")
