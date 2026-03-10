import requests
import time
from datetime import datetime, timedelta


class EastMoneyDownloader:
    """
    东方财富K线数据下载器
    
    支持:
    - A股日线、分钟线数据
    - 通过东方财富API直接获取
    
    K线周期:
    - daily: 日线 (klt=101)
    - weekly: 周线 (klt=102)
    - monthly: 月线 (klt=103)
    - 1min: 1分钟 (klt=5)
    - 5min: 5分钟 (klt=15)
    - 15min: 15分钟 (klt=30)
    - 30min: 30分钟 (klt=60)
    - 60min: 60分钟 (klt=101, 需要特殊处理)
    """
    
    PERIOD_MAP = {
        '1min': '5',
        '5min': '15',
        '15min': '30',
        '30min': '60',
        '1hour': '60',
        'daily': '101',
        'weekly': '102',
        'monthly': '103'
    }
    
    PERIOD_NAMES = {
        '1min': '1分钟',
        '5min': '5分钟',
        '15min': '15分钟',
        '30min': '30分钟',
        '1hour': '1小时',
        'daily': '日线',
        'weekly': '周线',
        'monthly': '月线'
    }
    
    API_URL = "http://push2his.eastmoney.com/api/qt/stock/kline/get"
    
    def __init__(self, timeout=30, retry_times=3, retry_delay=1):
        self.timeout = timeout
        self.retry_times = retry_times
        self.retry_delay = retry_delay
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'http://quote.eastmoney.com/'
        }
    
    def _get_secid(self, symbol):
        """
        获取东方财富证券代码
        
        Args:
            symbol: 6位股票代码
        
        Returns:
            str: 东方财富格式代码 (如 1.600519 或 0.000001)
        """
        if symbol.startswith('6'):
            return f"1.{symbol}"
        else:
            return f"0.{symbol}"
    
    def _build_params(self, symbol, period, start_date, end_date):
        """
        构建请求参数
        """
        klt = self.PERIOD_MAP.get(period, '101')
        secid = self._get_secid(symbol)
        
        params = {
            'secid': secid,
            'fields1': 'f1,f2,f3,f4,f5,f6',
            'fields2': 'f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61',
            'klt': klt,
            'fqt': '1',
            'beg': start_date,
            'end': end_date,
            'ut': 'fa5fd1943c7b386f172d6893dbfba10b',
            'cb': '',
        }
        
        return params
    
    def _parse_kline(self, klines):
        """
        解析K线数据
        
        Args:
            klines: 原始K线数据列表
        
        Returns:
            list: 解析后的K线数据
        """
        result = []
        for kline in klines:
            parts = kline.split(',')
            if len(parts) >= 11:
                result.append({
                    'date': parts[0],
                    'open': float(parts[1]),
                    'close': float(parts[2]),
                    'high': float(parts[3]),
                    'low': float(parts[4]),
                    'volume': int(parts[5]),
                    'amount': float(parts[6]),
                    'amplitude': float(parts[7]),
                    'change_pct': float(parts[8]),
                    'change': float(parts[9]),
                    'turnover': float(parts[10])
                })
        return result
    
    def download_kline(self, symbol, period='daily', start_date=None, end_date=None, days=None):
        """
        下载K线数据
        
        Args:
            symbol: 股票代码 (6位数字)
            period: 周期 (1min, 5min, 15min, 30min, 1hour, daily, weekly, monthly)
            start_date: 开始日期 (格式: '20200101')
            end_date: 结束日期 (格式: '20231231')
            days: 获取最近多少天的数据 (与start_date/end_date二选一)
        
        Returns:
            list: K线数据列表，失败返回None
        """
        if end_date is None:
            end_date = datetime.now().strftime('%Y%m%d')
        
        if start_date is None:
            if days is None:
                days = 365 if period == 'daily' else 30
            start_date = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')
        
        params = self._build_params(symbol, period, start_date, end_date)
        period_name = self.PERIOD_NAMES.get(period, period)
        
        for attempt in range(self.retry_times):
            try:
                response = requests.get(
                    self.API_URL,
                    params=params,
                    headers=self.headers,
                    timeout=self.timeout
                )
                
                data = response.json()
                
                if not data or 'data' not in data or not data['data']:
                    if attempt < self.retry_times - 1:
                        time.sleep(self.retry_delay)
                        continue
                    print(f"获取 {symbol} {period_name} 数据失败: 无数据返回")
                    return None
                
                klines = data['data'].get('klines', [])
                if not klines:
                    if attempt < self.retry_times - 1:
                        time.sleep(self.retry_delay)
                        continue
                    print(f"获取 {symbol} {period_name} 数据失败: K线数据为空")
                    return None
                
                result = self._parse_kline(klines)
                print(f"成功获取 {symbol} {period_name} 数据，共 {len(result)} 条")
                return result
                
            except requests.exceptions.Timeout:
                if attempt < self.retry_times - 1:
                    print(f"获取 {symbol} {period_name} 数据超时，重试 {attempt + 2}/{self.retry_times}")
                    time.sleep(self.retry_delay)
                    continue
                print(f"获取 {symbol} {period_name} 数据失败: 请求超时")
                return None
                
            except requests.exceptions.RequestException as e:
                if attempt < self.retry_times - 1:
                    time.sleep(self.retry_delay)
                    continue
                print(f"获取 {symbol} {period_name} 数据失败: {e}")
                return None
                
            except Exception as e:
                print(f"获取 {symbol} {period_name} 数据失败: {e}")
                return None
        
        return None
    
    def download_daily(self, symbol, start_date=None, end_date=None, days=365):
        """
        下载日线数据
        """
        return self.download_kline(symbol, 'daily', start_date, end_date, days)
    
    def download_1min(self, symbol, start_date=None, end_date=None, days=5):
        """
        下载1分钟数据
        """
        return self.download_kline(symbol, '1min', start_date, end_date, days)
    
    def download_5min(self, symbol, start_date=None, end_date=None, days=10):
        """
        下载5分钟数据
        """
        return self.download_kline(symbol, '5min', start_date, end_date, days)
    
    def download_15min(self, symbol, start_date=None, end_date=None, days=20):
        """
        下载15分钟数据
        """
        return self.download_kline(symbol, '15min', start_date, end_date, days)
    
    def download_1hour(self, symbol, start_date=None, end_date=None, days=30):
        """
        下载1小时数据
        """
        return self.download_kline(symbol, '1hour', start_date, end_date, days)


if __name__ == "__main__":
    downloader = EastMoneyDownloader()
    
    print("="*60)
    print("东方财富K线数据下载器测试")
    print("="*60)
    
    symbol = "600519"
    
    print(f"\n测试下载 {symbol} 日线数据...")
    data = downloader.download_daily(symbol, days=30)
    if data:
        print(f"前5条数据:")
        for item in data[:5]:
            print(f"  {item['date']}: 开{item['open']:.2f} 高{item['high']:.2f} 低{item['low']:.2f} 收{item['close']:.2f}")
    
    print(f"\n测试下载 {symbol} 5分钟数据...")
    data = downloader.download_5min(symbol, days=3)
    if data:
        print(f"前5条数据:")
        for item in data[:5]:
            print(f"  {item['date']}: 开{item['open']:.2f} 高{item['high']:.2f} 低{item['low']:.2f} 收{item['close']:.2f}")
