import requests
import csv
import os
from datetime import datetime, timedelta
from ..config import FINNHUB_API_KEY
import finnhub


class KLineDownloader:
    """
    股票历史K线数据下载器
    
    支持:
    - 美股: 通过 Finnhub API
    - A股: 通过东方财富 API
    """
    
    def __init__(self, output_dir='kline_data'):
        self.output_dir = output_dir
        self.finnhub_client = None
        if FINNHUB_API_KEY:
            self.finnhub_client = finnhub.Client(api_key=FINNHUB_API_KEY)
        
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
    
    def _get_market_code(self, symbol):
        if symbol.startswith('6'):
            return f"1.{symbol}"
        else:
            return f"0.{symbol}"
    
    def download_us_stock_kline(self, symbol, resolution='D', days=365, save_to_file=True):
        """
        下载美股K线数据
        
        Args:
            symbol: 股票代码 (如 AAPL)
            resolution: 周期 (1, 5, 15, 30, 60, D, W, M)
            days: 获取最近多少天的数据
            save_to_file: 是否保存到文件
        
        Returns:
            list: K线数据列表
        """
        if not self.finnhub_client:
            print("错误: 未配置 Finnhub API Key，无法获取美股K线数据")
            return None
        
        try:
            end_time = int(datetime.now().timestamp())
            start_time = int((datetime.now() - timedelta(days=days)).timestamp())
            
            candles = self.finnhub_client.stock_candles(symbol, resolution, start_time, end_time)
            
            if candles.get('s') != 'ok':
                print(f"获取 {symbol} K线数据失败: 无数据")
                return None
            
            kline_data = []
            timestamps = candles['t']
            opens = candles['o']
            highs = candles['h']
            lows = candles['l']
            closes = candles['c']
            volumes = candles['v']
            
            for i in range(len(timestamps)):
                kline_data.append({
                    'date': datetime.fromtimestamp(timestamps[i]).strftime('%Y-%m-%d'),
                    'open': opens[i],
                    'high': highs[i],
                    'low': lows[i],
                    'close': closes[i],
                    'volume': volumes[i]
                })
            
            print(f"成功获取 {symbol} K线数据，共 {len(kline_data)} 条记录")
            
            if save_to_file:
                self._save_to_csv(symbol, kline_data, market='US')
            
            return kline_data
            
        except Exception as e:
            print(f"下载 {symbol} K线数据失败: {e}")
            return None
    
    def download_cn_stock_kline(self, symbol, period='daily', days=365, save_to_file=True):
        """
        下载A股K线数据
        
        Args:
            symbol: 股票代码 (如 600519)
            period: 周期 (daily=日K, weekly=周K, monthly=月K)
            days: 获取最近多少天的数据
            save_to_file: 是否保存到文件
        
        Returns:
            list: K线数据列表
        """
        try:
            secid = self._get_market_code(symbol)
            
            period_map = {
                'daily': '101',
                'weekly': '102',
                'monthly': '103'
            }
            klt = period_map.get(period, '101')
            
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')
            
            url = "http://push2his.eastmoney.com/api/qt/stock/kline/get"
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
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, params=params, headers=headers, timeout=30)
            data = response.json()
            
            if not data or 'data' not in data or not data['data']:
                print(f"获取 {symbol} K线数据失败: 无数据")
                return None
            
            klines = data['data'].get('klines', [])
            kline_data = []
            
            for kline in klines:
                parts = kline.split(',')
                kline_data.append({
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
            
            print(f"成功获取 {symbol} K线数据，共 {len(kline_data)} 条记录")
            
            if save_to_file:
                self._save_to_csv(symbol, kline_data, market='CN', extra_fields=True)
            
            return kline_data
            
        except Exception as e:
            print(f"下载 {symbol} K线数据失败: {e}")
            return None
    
    def download_kline(self, symbol, market='美股', period='daily', days=365, save_to_file=True):
        """
        下载K线数据（统一接口）
        
        Args:
            symbol: 股票代码
            market: 市场类型 ('美股' 或 'A股')
            period: 周期
            days: 获取最近多少天的数据
            save_to_file: 是否保存到文件
        
        Returns:
            list: K线数据列表
        """
        if market == 'A股':
            return self.download_cn_stock_kline(symbol, period, days, save_to_file)
        else:
            resolution_map = {
                'daily': 'D',
                'weekly': 'W',
                'monthly': 'M'
            }
            resolution = resolution_map.get(period, 'D')
            return self.download_us_stock_kline(symbol, resolution, days, save_to_file)
    
    def _save_to_csv(self, symbol, kline_data, market='US', extra_fields=False):
        """
        保存K线数据到CSV文件
        
        Args:
            symbol: 股票代码
            kline_data: K线数据列表
            market: 市场类型
            extra_fields: 是否包含额外字段
        """
        if not kline_data:
            return
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{market}_{symbol}_{timestamp}.csv"
        filepath = os.path.join(self.output_dir, filename)
        
        if extra_fields:
            fieldnames = ['date', 'open', 'close', 'high', 'low', 'volume', 
                         'amount', 'amplitude', 'change_pct', 'change', 'turnover']
        else:
            fieldnames = ['date', 'open', 'high', 'low', 'close', 'volume']
        
        try:
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for row in kline_data:
                    filtered_row = {k: row[k] for k in fieldnames if k in row}
                    writer.writerow(filtered_row)
            
            print(f"数据已保存到: {filepath}")
            
        except Exception as e:
            print(f"保存文件失败: {e}")
    
    def batch_download(self, stock_list, period='daily', days=365):
        """
        批量下载K线数据
        
        Args:
            stock_list: 股票列表，每个元素为 {'symbol': '代码', 'market': '市场'}
            period: 周期
            days: 获取最近多少天的数据
        
        Returns:
            dict: 下载结果统计
        """
        results = {
            'success': [],
            'failed': []
        }
        
        total = len(stock_list)
        for i, stock in enumerate(stock_list, 1):
            symbol = stock.get('symbol')
            market = stock.get('market', '美股')
            
            print(f"\n[{i}/{total}] 正在下载 {symbol} ({market})...")
            
            data = self.download_kline(symbol, market, period, days)
            
            if data:
                results['success'].append(symbol)
            else:
                results['failed'].append(symbol)
        
        print(f"\n{'='*50}")
        print("批量下载完成")
        print(f"成功: {len(results['success'])} 只")
        print(f"失败: {len(results['failed'])} 只")
        if results['failed']:
            print(f"失败股票: {', '.join(results['failed'])}")
        print(f"{'='*50}")
        
        return results


if __name__ == "__main__":
    downloader = KLineDownloader()
    
    print("="*60)
    print("股票K线数据下载器")
    print("="*60)
    
    while True:
        print("\n请选择操作:")
        print("1. 下载美股K线数据")
        print("2. 下载A股K线数据")
        print("3. 批量下载配置文件中的股票")
        print("4. 退出")
        
        choice = input("\n请输入选项 (1-4): ").strip()
        
        if choice == '1':
            symbol = input("请输入美股代码 (如 AAPL): ").strip().upper()
            if not symbol:
                continue
            
            print("\n可选周期: daily(日K), weekly(周K), monthly(月K)")
            period = input("请输入周期 (默认 daily): ").strip().lower() or 'daily'
            
            try:
                days = int(input("请输入获取天数 (默认 365): ").strip() or '365')
            except ValueError:
                days = 365
            
            downloader.download_us_stock_kline(symbol, 
                                               resolution={'daily': 'D', 'weekly': 'W', 'monthly': 'M'}.get(period, 'D'),
                                               days=days)
        
        elif choice == '2':
            symbol = input("请输入A股代码 (如 600519): ").strip()
            if not symbol:
                continue
            
            print("\n可选周期: daily(日K), weekly(周K), monthly(月K)")
            period = input("请输入周期 (默认 daily): ").strip().lower() or 'daily'
            
            try:
                days = int(input("请输入获取天数 (默认 365): ").strip() or '365')
            except ValueError:
                days = 365
            
            downloader.download_cn_stock_kline(symbol, period=period, days=days)
        
        elif choice == '3':
            import json
            from ..config import STOCKS_CONFIG_PATH
            
            if os.path.exists(STOCKS_CONFIG_PATH):
                with open(STOCKS_CONFIG_PATH, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                stocks = config.get('stocks', [])
                if stocks:
                    print(f"\n将下载 {len(stocks)} 只股票的K线数据")
                    
                    print("\n可选周期: daily(日K), weekly(周K), monthly(月K)")
                    period = input("请输入周期 (默认 daily): ").strip().lower() or 'daily'
                    
                    try:
                        days = int(input("请输入获取天数 (默认 365): ").strip() or '365')
                    except ValueError:
                        days = 365
                    
                    downloader.batch_download(stocks, period, days)
                else:
                    print("配置文件中没有股票")
            else:
                print("配置文件不存在")
        
        elif choice == '4':
            print("再见！")
            break
        
        else:
            print("无效选项")
