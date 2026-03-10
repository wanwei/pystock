import finnhub
from config import FINNHUB_API_KEY, STOCKS_CONFIG_PATH
from tabulate import tabulate
from datetime import datetime
import sys
import json
import time
import os
import requests


class EastMoneyAPI:
    """
    A股实时行情接口
    
    沪市代码前缀: 1 (如 1.600519)
    深市代码前缀: 0 (如 0.000858)
    """
    
    def __init__(self):
        self.base_url = "http://push2.eastmoney.com/api/qt/stock/get"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    
    def _get_market_code(self, symbol):
        if symbol.startswith('6'):
            return f"1.{symbol}"
        else:
            return f"0.{symbol}"
    
    def get_quote(self, symbol):
        try:
            secid = self._get_market_code(symbol)
            params = {
                'secid': secid,
                'fields': 'f43,f44,f45,f46,f47,f48,f50,f51,f52,f58,f60,f169,f170',
                'ut': 'fa5fd1943c7b386f172d6893dbfba10b'
            }
            
            response = requests.get(self.base_url, params=params, headers=self.headers, timeout=10)
            data = response.json()
            
            if data and 'data' in data and data['data']:
                d = data['data']
                return {
                    'c': d.get('f43', 0) / 100 if d.get('f43') else None,
                    'o': d.get('f46', 0) / 100 if d.get('f46') else None,
                    'h': d.get('f44', 0) / 100 if d.get('f44') else None,
                    'l': d.get('f45', 0) / 100 if d.get('f45') else None,
                    'pc': d.get('f60', 0) / 100 if d.get('f60') else None,
                    'd': (d.get('f43', 0) - d.get('f60', 0)) / 100 if d.get('f43') and d.get('f60') else None,
                    'dp': ((d.get('f43', 0) - d.get('f60', 0)) / d.get('f60', 1)) * 100 if d.get('f43') and d.get('f60') else None,
                    'name': d.get('f58', '')
                }
            return None
        except Exception as e:
            print(f"东方财富获取 {symbol} 报价失败: {e}")
            return None


class StockApp:
    def __init__(self):
        self.finnhub_client = None
        if FINNHUB_API_KEY:
            self.finnhub_client = finnhub.Client(api_key=FINNHUB_API_KEY)
        
        self.eastmoney_client = EastMoneyAPI()
        self.stocks_config = self.load_stocks_config()
    
    def load_stocks_config(self):
        if os.path.exists(STOCKS_CONFIG_PATH):
            try:
                with open(STOCKS_CONFIG_PATH, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"加载股票配置文件失败: {e}")
                return {"stocks": [], "refresh_interval": 5}
        return {"stocks": [], "refresh_interval": 5}
    
    def save_stocks_config(self):
        try:
            with open(STOCKS_CONFIG_PATH, 'w', encoding='utf-8') as f:
                json.dump(self.stocks_config, f, ensure_ascii=False, indent=4)
            print("配置已保存")
        except Exception as e:
            print(f"保存配置文件失败: {e}")
    
    def get_stock_quote(self, symbol, market='美股'):
        if market == 'A股':
            return self.eastmoney_client.get_quote(symbol)
        else:
            if not self.finnhub_client:
                print("警告: 未配置 Finnhub API Key，无法获取美股数据")
                return None
            try:
                quote = self.finnhub_client.quote(symbol)
                return quote
            except Exception as e:
                print(f"获取 {symbol} 报价失败: {e}")
                return None
    
    def get_stock_info(self, symbol, market='美股'):
        if market == 'A股':
            return {'name': '', 'industry': '', 'description': ''}
        if not self.finnhub_client:
            return None
        try:
            company_info = self.finnhub_client.company_profile2(symbol=symbol)
            return company_info
        except Exception as e:
            print(f"获取 {symbol} 公司信息失败: {e}")
            return None
    
    def get_stock_candles(self, symbol, resolution='D', count=30, market='美股'):
        if market == 'A股':
            print("A股K线数据暂不支持")
            return None
        if not self.finnhub_client:
            return None
        try:
            from datetime import datetime, timedelta
            end_time = int(datetime.now().timestamp())
            start_time = int((datetime.now() - timedelta(days=count)).timestamp())
            
            candles = self.finnhub_client.stock_candles(symbol, resolution, start_time, end_time)
            return candles
        except Exception as e:
            print(f"获取 {symbol} K线数据失败: {e}")
            return None
    
    def display_quote(self, symbol, market='美股'):
        print(f"\n{'='*60}")
        print(f"股票代码: {symbol} ({market})")
        print(f"{'='*60}")
        
        quote = self.get_stock_quote(symbol, market)
        if not quote or quote.get('c') is None:
            print("无法获取股票报价数据")
            return
        
        current_price = quote['c']
        change = quote['d']
        change_percent = quote['dp']
        high = quote['h']
        low = quote['l']
        open_price = quote['o']
        prev_close = quote['pc']
        
        change_str = f"+{change:.2f}" if change >= 0 else f"{change:.2f}"
        change_percent_str = f"+{change_percent:.2f}%" if change_percent >= 0 else f"{change_percent:.2f}%"
        
        data = [
            ['当前价格', f"{current_price:.2f}"],
            ['涨跌额', change_str],
            ['涨跌幅', change_percent_str],
            ['开盘价', f"{open_price:.2f}"],
            ['最高价', f"{high:.2f}"],
            ['最低价', f"{low:.2f}"],
            ['昨收价', f"{prev_close:.2f}"]
        ]
        
        print(tabulate(data, headers=['指标', '数值'], tablefmt='grid'))
        
        if market != 'A股':
            company_info = self.get_stock_info(symbol, market)
            if company_info:
                print(f"\n公司名称: {company_info.get('name', 'N/A')}")
                print(f"所属行业: {company_info.get('industry', 'N/A')}")
                print(f"公司简介: {company_info.get('description', 'N/A')[:100]}...")
    
    def display_candles(self, symbol, resolution='D', count=30, market='美股'):
        print(f"\n{'='*60}")
        print(f"{symbol} K线数据 ({resolution}, 最近{count}个周期)")
        print(f"{'='*60}")
        
        candles = self.get_stock_candles(symbol, resolution, count, market)
        if not candles or candles.get('s') != 'ok':
            print("无法获取K线数据")
            return
        
        data = []
        timestamps = candles['t']
        opens = candles['o']
        highs = candles['h']
        lows = candles['l']
        closes = candles['c']
        volumes = candles['v']
        
        for i in range(len(timestamps)):
            date = datetime.fromtimestamp(timestamps[i]).strftime('%Y-%m-%d')
            data.append([
                date,
                f"{opens[i]:.2f}",
                f"{highs[i]:.2f}",
                f"{lows[i]:.2f}",
                f"{closes[i]:.2f}",
                f"{volumes[i]:,}"
            ])
        
        headers = ['日期', '开盘价', '最高价', '最低价', '收盘价', '成交量']
        print(tabulate(data, headers=headers, tablefmt='grid'))
    
    def track_realtime_quotes(self):
        stocks = self.stocks_config.get('stocks', [])
        if not stocks:
            print("\n配置文件中没有股票，请先添加股票")
            return
        
        refresh_interval = self.stocks_config.get('refresh_interval', 5)
        
        print(f"\n开始实时跟踪 {len(stocks)} 只股票 (每 {refresh_interval} 秒刷新)")
        print("按 Ctrl+C 停止跟踪\n")
        
        try:
            while True:
                os.system('cls' if os.name == 'nt' else 'clear')
                print(f"{'='*80}")
                print(f"股票实时行情 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"{'='*80}")
                
                table_data = []
                for stock in stocks:
                    symbol = stock['symbol']
                    name = stock.get('name', 'N/A')
                    market = stock.get('market', '美股')
                    
                    quote = self.get_stock_quote(symbol, market)
                    if quote and quote.get('c') is not None:
                        current_price = quote['c']
                        change = quote['d']
                        change_percent = quote['dp']
                        
                        change_str = f"+{change:.2f}" if change >= 0 else f"{change:.2f}"
                        change_percent_str = f"+{change_percent:.2f}%" if change_percent >= 0 else f"{change_percent:.2f}%"
                        
                        table_data.append([
                            symbol,
                            name,
                            market,
                            f"{current_price:.2f}",
                            change_str,
                            change_percent_str
                        ])
                    else:
                        table_data.append([symbol, name, market, 'N/A', 'N/A', 'N/A'])
                
                headers = ['代码', '名称', '市场', '当前价', '涨跌额', '涨跌幅']
                print(tabulate(table_data, headers=headers, tablefmt='grid'))
                print(f"\n刷新间隔: {refresh_interval}秒 | 按 Ctrl+C 停止")
                
                time.sleep(refresh_interval)
                
        except KeyboardInterrupt:
            print("\n\n已停止实时跟踪")
    
    def manage_stocks(self):
        while True:
            print(f"\n{'='*60}")
            print("股票配置管理")
            print(f"{'='*60}")
            print("1. 查看当前股票列表")
            print("2. 添加股票")
            print("3. 删除股票")
            print("4. 设置刷新间隔")
            print("5. 返回主菜单")
            print(f"{'='*60}")
            
            choice = input("\n请输入选项 (1-5): ").strip()
            
            if choice == '1':
                stocks = self.stocks_config.get('stocks', [])
                if not stocks:
                    print("\n当前没有配置任何股票")
                else:
                    print(f"\n当前股票列表 (共 {len(stocks)} 只):")
                    table_data = []
                    for i, stock in enumerate(stocks, 1):
                        table_data.append([
                            i,
                            stock.get('symbol', 'N/A'),
                            stock.get('name', 'N/A'),
                            stock.get('market', 'N/A')
                        ])
                    headers = ['序号', '代码', '名称', '市场']
                    print(tabulate(table_data, headers=headers, tablefmt='grid'))
            
            elif choice == '2':
                symbol = input("请输入股票代码 (如 AAPL 或 600519.SS): ").strip().upper()
                if not symbol:
                    print("股票代码不能为空")
                    continue
                
                for stock in self.stocks_config.get('stocks', []):
                    if stock['symbol'] == symbol:
                        print(f"股票 {symbol} 已存在")
                        break
                else:
                    name = input("请输入股票名称: ").strip()
                    market = input("请输入市场 (美股/A股/港股): ").strip() or '美股'
                    
                    self.stocks_config.setdefault('stocks', []).append({
                        'symbol': symbol,
                        'name': name,
                        'market': market
                    })
                    self.save_stocks_config()
                    print(f"已添加股票: {symbol} - {name}")
            
            elif choice == '3':
                stocks = self.stocks_config.get('stocks', [])
                if not stocks:
                    print("\n当前没有配置任何股票")
                    continue
                
                print(f"\n当前股票列表:")
                for i, stock in enumerate(stocks, 1):
                    print(f"  {i}. {stock['symbol']} - {stock.get('name', 'N/A')}")
                
                try:
                    index = int(input("\n请输入要删除的股票序号: ").strip())
                    if 1 <= index <= len(stocks):
                        removed = stocks.pop(index - 1)
                        self.save_stocks_config()
                        print(f"已删除股票: {removed['symbol']} - {removed.get('name', 'N/A')}")
                    else:
                        print("无效序号")
                except ValueError:
                    print("请输入有效数字")
            
            elif choice == '4':
                try:
                    interval = int(input(f"请输入刷新间隔秒数 (当前: {self.stocks_config.get('refresh_interval', 5)}): ").strip())
                    if interval >= 1:
                        self.stocks_config['refresh_interval'] = interval
                        self.save_stocks_config()
                        print(f"刷新间隔已设置为 {interval} 秒")
                    else:
                        print("刷新间隔必须大于等于1秒")
                except ValueError:
                    print("请输入有效数字")
            
            elif choice == '5':
                break
            
            else:
                print("无效选项，请重新选择")
    
    def run(self):
        print("="*60)
        print("股票行情查询系统")
        print("数据源: 美股-Finnhub | A股-东方财富")
        print("="*60)
        print("\nA股代码示例: 600519 (贵州茅台), 000858 (五粮液)")
        print("美股代码示例: AAPL (苹果), TSLA (特斯拉)")
        
        while True:
            print("\n" + "="*60)
            print("请选择操作:")
            print("1. 查询实时报价")
            print("2. 查询K线数据 (仅美股)")
            print("3. 实时跟踪股票行情")
            print("4. 管理股票配置")
            print("5. 退出")
            print("="*60)
            
            choice = input("\n请输入选项 (1-5): ").strip()
            
            if choice == '1':
                market = input("请选择市场 (1.美股 2.A股): ").strip()
                market = 'A股' if market == '2' else '美股'
                symbol = input(f"请输入股票代码: ").strip().upper()
                if symbol:
                    self.display_quote(symbol, market)
            
            elif choice == '2':
                symbol = input("请输入美股代码 (如 AAPL): ").strip().upper()
                if symbol:
                    print("\n可选周期: 1, 5, 15, 30, 60, D, W, M")
                    resolution = input("请输入周期 (默认 D): ").strip().upper() or 'D'
                    try:
                        count = int(input("请输入获取数量 (默认 30): ").strip() or '30')
                    except ValueError:
                        count = 30
                    self.display_candles(symbol, resolution, count, '美股')
            
            elif choice == '3':
                self.track_realtime_quotes()
            
            elif choice == '4':
                self.manage_stocks()
            
            elif choice == '5':
                print("感谢使用，再见！")
                break
            
            else:
                print("无效选项，请重新选择")


def main():
    app = StockApp()
    app.run()


if __name__ == "__main__":
    main()
