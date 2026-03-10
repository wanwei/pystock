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
    
    def _parse_latest_date(self, latest_date_str, period):
        """
        解析最新日期字符串，区分日线和分钟线格式
        
        Args:
            latest_date_str: 日期字符串
            period: 周期
            
        Returns:
            datetime: 解析后的日期时间对象
        """
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
        """
        计算增量下载的起始日期
        
        Args:
            latest_date: 本地最新日期 (datetime)
            period: 周期
            
        Returns:
            str: 起始日期字符串 (格式: '20240115')
        """
        if latest_date is None:
            return None
        
        if period == 'daily':
            start_date = latest_date + timedelta(days=1)
        else:
            start_date = latest_date + timedelta(minutes=1)
        
        return start_date.strftime('%Y%m%d')
    
    def _need_update(self, latest_date, period, filepath=None):
        """
        判断是否需要更新数据
        
        核心判断逻辑：
        1. 如果本地数据的最后交易日就是当前交易日（今天）
        2. 且数据文件的最后修改时间已超过当日15:30
        3. 则说明今天收盘后的数据已经下载完成，无需再次更新
        
        原理说明：
        - A股交易日收盘时间为15:00
        - 数据源通常在收盘后30分钟内（约15:30）完成数据整理
        - 如果文件在15:30之后被修改过，且数据日期是今天，说明数据已完整
        - 此判断可避免重复下载已完成的数据，节省API调用次数
        
        Args:
            latest_date: 本地最新日期 (datetime)
            period: 周期
            filepath: 数据文件路径，用于检查文件修改时间
            
        Returns:
            bool: 是否需要更新
        """
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
        """
        合并新旧数据并保存
        
        Args:
            symbol: 股票代码
            market: 市场
            period: 周期
            new_data: 新下载的数据列表
            
        Returns:
            bool: 是否成功
        """
        if not new_data:
            print(f"{symbol} {period} 无新数据需要合并")
            return False
        
        filepath = self._get_data_filepath(symbol, market, period)
        
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
            
            stock_dir = self._ensure_stock_dir(symbol, market)
            combined_df.to_csv(filepath, index=False, encoding='utf-8')
            
            print(f"{symbol} {period} 增量更新完成: 新增 {len(new_data)} 条，合并后共 {len(combined_df)} 条")
            return True
            
        except Exception as e:
            print(f"合并数据失败: {e}")
            return False
    
    def update_kline_data(self, symbol, market, period):
        """
        增量更新K线数据
        
        Args:
            symbol: 股票代码
            market: 市场
            period: 周期
            
        Returns:
            bool: 是否成功
        """
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
        """
        增量同步所有股票数据
        
        Args:
            periods: 要同步的周期列表，None表示全部周期
            
        Returns:
            dict: 同步结果
        """
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
                        if success:
                            local_info_after = self.check_local_data(symbol, market, period)
                            if local_info['latest_date'] == local_info_after['latest_date']:
                                pass
                    
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
        print("2. 增量同步所有股票数据 (推荐)")
        print("3. 全量同步所有股票数据")
        print("4. 下载/更新单只股票数据")
        print("5. 强制重新下载所有数据")
        print("6. 查看本地股票目录")
        print("7. 退出")
        
        choice = input("\n请输入选项 (1-7): ").strip()
        
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
            
            manager.sync_all_stocks_incremental(periods=periods)
        
        elif choice == '3':
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
        
        elif choice == '4':
            manager.load_stock_list()
            symbol = input("请输入股票代码: ").strip()
            market = input("请输入市场 (美股/A股): ").strip() or 'A股'
            
            print("\n更新模式:")
            print("1. 增量更新 (推荐)")
            print("2. 全量下载")
            update_mode = input("请选择 (1-2，默认1): ").strip() or '1'
            
            print("\n可选周期: 1min, 5min, 15min, 1hour, daily")
            custom = input("输入周期 (用逗号分隔，默认全部): ").strip()
            if custom:
                periods = [p.strip() for p in custom.split(',')]
            else:
                periods = None
            
            if update_mode == '2':
                for period in (periods or list(manager.PERIODS.keys())):
                    manager.download_kline_data(symbol, market, period)
            else:
                for period in (periods or list(manager.PERIODS.keys())):
                    manager.update_kline_data(symbol, market, period)
        
        elif choice == '5':
            confirm = input("确定要强制重新下载所有数据吗? (y/n): ").strip().lower()
            if confirm == 'y':
                manager.sync_all_stocks(force_download=True)
        
        elif choice == '6':
            stock_dirs = manager.list_stock_directories()
            if stock_dirs:
                print(f"\n本地股票数据目录 ({len(stock_dirs)} 个):")
                for d in stock_dirs:
                    print(f"  - {d}")
            else:
                print("\n暂无本地数据目录")
        
        elif choice == '7':
            print("再见！")
            break
        
        else:
            print("无效选项")
