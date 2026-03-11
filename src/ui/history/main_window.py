import tkinter as tk
from tkinter import ttk, messagebox
import finnhub
import requests
import threading
from datetime import datetime

from config import FINNHUB_API_KEY
from datamgr import StockDataManager, KLineManager
from ui.widgets import StockListWidget, KLineChartWidget


class EastMoneyAPI:
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


class HistoryAnalysisApp:
    """
    历史分析模块主窗口
    
    功能:
    - 股票列表浏览
    - K线图查看
    - 策略回测
    - 形态扫描
    """
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("股票历史分析系统")
        self.root.geometry("1200x800")
        self.root.minsize(800, 600)
        self.root.state('zoomed')
        
        self.finnhub_client = None
        if FINNHUB_API_KEY:
            self.finnhub_client = finnhub.Client(api_key=FINNHUB_API_KEY)
        
        self.eastmoney_client = EastMoneyAPI()
        self.data_manager = StockDataManager()
        self.kline_manager = KLineManager()
        
        self.current_symbol = None
        self.current_name = None
        self.current_market = None
        self.current_stock_index = -1
        
        self._create_menu()
        self._create_main_frame()
    
    def _create_menu(self):
        menubar = tk.Menu(self.root)
        
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="导入股票列表", command=self._import_stock_list)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.root.quit)
        menubar.add_cascade(label="文件", menu=file_menu)
        
        data_menu = tk.Menu(menubar, tearoff=0)
        data_menu.add_command(label="更新K线数据", command=self._update_kline_data)
        data_menu.add_command(label="数据状态", command=self._show_data_status)
        menubar.add_cascade(label="数据", menu=data_menu)
        
        strategy_menu = tk.Menu(menubar, tearoff=0)
        strategy_menu.add_command(label="策略回测", command=self._open_backtest)
        strategy_menu.add_command(label="形态扫描", command=self._open_scanner)
        menubar.add_cascade(label="策略", menu=strategy_menu)
        
        self.root.config(menu=menubar)
    
    def _create_main_frame(self):
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self._show_stock_list_view()
    
    def _show_stock_list_view(self):
        for widget in self.main_frame.winfo_children():
            widget.destroy()
        
        self.root.title("股票历史分析系统 - 股票列表")
        
        title_label = ttk.Label(self.main_frame, text="股票列表", font=('Microsoft YaHei', 16, 'bold'))
        title_label.pack(pady=(0, 10))
        
        self.stock_list = StockListWidget(
            self.main_frame,
            self.data_manager,
            on_double_click=self._on_stock_double_click
        )
        self.stock_list.pack(fill=tk.BOTH, expand=True)
        
        self.stock_list.start_refresh_quotes(self._get_stock_quote)
    
    def _on_stock_double_click(self, values):
        self.current_symbol = values[0]
        self.current_name = values[1]
        self.current_market = values[2]
        self._show_kline_view()
    
    def _show_kline_view(self):
        for widget in self.main_frame.winfo_children():
            widget.destroy()
        
        self.root.title(f"股票历史分析系统 - {self.current_name} ({self.current_symbol})")
        
        header_frame = ttk.Frame(self.main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(header_frame, 
                  text=f"{self.current_name} ({self.current_symbol}) - {self.current_market}",
                  font=('Microsoft YaHei', 16, 'bold')).pack(side=tk.LEFT)
        
        btn_frame = ttk.Frame(self.main_frame)
        btn_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(btn_frame, text="返回列表", command=self._show_stock_list_view).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="刷新数据", command=self._refresh_kline).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="回测", command=self._open_backtest).pack(side=tk.LEFT, padx=5)
        
        self.kline_chart = KLineChartWidget(
            self.main_frame,
            on_period_change=self._on_period_change
        )
        self.kline_chart.pack(fill=tk.BOTH, expand=True)
        self.kline_chart.bind_keys(self.root)
        
        self._load_kline_data()
    
    def _on_period_change(self, period):
        self._load_kline_data(period)
    
    def _load_kline_data(self, period='daily'):
        self.kline_chart.status_label.config(text="正在加载...")
        
        thread = threading.Thread(
            target=self._fetch_kline_thread,
            args=(period,),
            daemon=True
        )
        thread.start()
    
    def _fetch_kline_thread(self, period):
        kline_data = self._get_stock_kline(self.current_symbol, self.current_market, period)
        self.root.after(0, lambda: self.kline_chart.set_data(kline_data, period))
    
    def _refresh_kline(self):
        self.kline_manager.download_kline_data(
            self.current_symbol, 
            self.current_market, 
            self.kline_chart.current_period
        )
        self._load_kline_data(self.kline_chart.current_period)
    
    def _get_stock_quote(self, symbol, market='美股'):
        if market == 'A股':
            return self.eastmoney_client.get_quote(symbol)
        else:
            if not self.finnhub_client:
                return None
            try:
                return self.finnhub_client.quote(symbol)
            except Exception as e:
                print(f"获取 {symbol} 报价失败: {e}")
                return None
    
    def _get_stock_kline(self, symbol, market, period='daily'):
        try:
            df = self.kline_manager.get_kline_data(symbol, market, period)
            
            if df is None:
                is_sufficient, _ = self.kline_manager.is_data_sufficient(symbol, market, period)
                if not is_sufficient:
                    self.kline_manager.download_kline_data(symbol, market, period)
                    df = self.kline_manager.get_kline_data(symbol, market, period)
            
            if df is None:
                return None
            
            kline_data = []
            for _, row in df.iterrows():
                date_str = str(row['date'])
                if ' ' in date_str:
                    date_str = date_str.split(' ')[0]
                kline_data.append({
                    'date': date_str,
                    'open': float(row['open']),
                    'high': float(row['high']),
                    'low': float(row['low']),
                    'close': float(row['close']),
                    'volume': int(row['volume'])
                })
            
            return kline_data
            
        except Exception as e:
            print(f"获取 {symbol} K线数据失败: {e}")
            return None
    
    def _import_stock_list(self):
        from tkinter import filedialog
        import json
        import os
        
        file_path = filedialog.askopenfilename(
            title="选择配置文件",
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")],
            initialdir=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'config')
        )
        
        if not file_path:
            return
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            if 'stocks' not in config_data:
                messagebox.showerror("错误", "配置文件格式错误：缺少stocks字段")
                return
            
            self.data_manager._config_cache = config_data
            messagebox.showinfo("成功", f"已导入 {len(config_data['stocks'])} 只股票")
            self._show_stock_list_view()
            
        except Exception as e:
            messagebox.showerror("错误", f"导入配置文件失败: {str(e)}")
    
    def _update_kline_data(self):
        messagebox.showinfo("提示", "请在命令行运行 update_kline_data.py 更新数据")
    
    def _show_data_status(self):
        self.kline_manager.show_data_status()
    
    def _open_backtest(self):
        messagebox.showinfo("提示", "回测功能开发中...")
    
    def _open_scanner(self):
        messagebox.showinfo("提示", "扫描功能开发中...")
    
    def run(self):
        self.root.mainloop()


def main():
    app = HistoryAnalysisApp()
    app.run()


if __name__ == "__main__":
    main()
