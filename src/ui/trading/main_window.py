import tkinter as tk
from tkinter import ttk, messagebox
import finnhub
import requests
import threading
from datetime import datetime

from config import FINNHUB_API_KEY
from datamgr import StockDataManager


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


class TradingApp:
    """
    实盘交易模块主窗口
    
    功能:
    - 行情监控
    - 自选股管理
    - 交易执行
    - 持仓管理
    """
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("股票实盘交易系统")
        self.root.geometry("1200x800")
        self.root.minsize(800, 600)
        
        self.finnhub_client = None
        if FINNHUB_API_KEY:
            self.finnhub_client = finnhub.Client(api_key=FINNHUB_API_KEY)
        
        self.eastmoney_client = EastMoneyAPI()
        self.data_manager = StockDataManager()
        
        self._create_menu()
        self._create_main_frame()
    
    def _create_menu(self):
        menubar = tk.Menu(self.root)
        
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="账户设置", command=self._open_account_settings)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.root.quit)
        menubar.add_cascade(label="文件", menu=file_menu)
        
        trade_menu = tk.Menu(menubar, tearoff=0)
        trade_menu.add_command(label="买入", command=self._open_buy)
        trade_menu.add_command(label="卖出", command=self._open_sell)
        trade_menu.add_separator()
        trade_menu.add_command(label="委托查询", command=self._open_orders)
        menubar.add_cascade(label="交易", menu=trade_menu)
        
        monitor_menu = tk.Menu(menubar, tearoff=0)
        monitor_menu.add_command(label="自选股管理", command=self._open_watchlist)
        monitor_menu.add_command(label="价格预警", command=self._open_alerts)
        menubar.add_cascade(label="监控", menu=monitor_menu)
        
        self.root.config(menu=menubar)
    
    def _create_main_frame(self):
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self._create_dashboard()
    
    def _create_dashboard(self):
        for widget in self.main_frame.winfo_children():
            widget.destroy()
        
        self.root.title("股票实盘交易系统 - 控制面板")
        
        title_label = ttk.Label(self.main_frame, text="实盘交易控制面板", 
                               font=('Microsoft YaHei', 16, 'bold'))
        title_label.pack(pady=(0, 20))
        
        account_frame = ttk.LabelFrame(self.main_frame, text="账户概览", padding=10)
        account_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(account_frame, text="总资产:").grid(row=0, column=0, padx=5, pady=5)
        ttk.Label(account_frame, text="--", font=('Microsoft YaHei', 12, 'bold')).grid(row=0, column=1, padx=5)
        
        ttk.Label(account_frame, text="可用资金:").grid(row=0, column=2, padx=5, pady=5)
        ttk.Label(account_frame, text="--", font=('Microsoft YaHei', 12)).grid(row=0, column=3, padx=5)
        
        ttk.Label(account_frame, text="持仓市值:").grid(row=0, column=4, padx=5, pady=5)
        ttk.Label(account_frame, text="--", font=('Microsoft YaHei', 12)).grid(row=0, column=5, padx=5)
        
        ttk.Label(account_frame, text="今日盈亏:").grid(row=0, column=6, padx=5, pady=5)
        ttk.Label(account_frame, text="--", font=('Microsoft YaHei', 12)).grid(row=0, column=7, padx=5)
        
        position_frame = ttk.LabelFrame(self.main_frame, text="持仓列表", padding=10)
        position_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        columns = ('symbol', 'name', 'quantity', 'cost', 'price', 'market_value', 'profit', 'profit_pct')
        self.position_tree = ttk.Treeview(position_frame, columns=columns, show='headings', height=10)
        
        self.position_tree.heading('symbol', text='代码')
        self.position_tree.heading('name', text='名称')
        self.position_tree.heading('quantity', text='持仓')
        self.position_tree.heading('cost', text='成本')
        self.position_tree.heading('price', text='现价')
        self.position_tree.heading('market_value', text='市值')
        self.position_tree.heading('profit', text='盈亏')
        self.position_tree.heading('profit_pct', text='盈亏%')
        
        for col in columns:
            self.position_tree.column(col, width=100, anchor='center')
        
        self.position_tree.pack(fill=tk.BOTH, expand=True)
        
        watchlist_frame = ttk.LabelFrame(self.main_frame, text="自选股", padding=10)
        watchlist_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        watch_columns = ('symbol', 'name', 'price', 'change', 'change_pct')
        self.watch_tree = ttk.Treeview(watchlist_frame, columns=watch_columns, show='headings', height=8)
        
        self.watch_tree.heading('symbol', text='代码')
        self.watch_tree.heading('name', text='名称')
        self.watch_tree.heading('price', text='现价')
        self.watch_tree.heading('change', text='涨跌')
        self.watch_tree.heading('change_pct', text='涨跌幅')
        
        for col in watch_columns:
            self.watch_tree.column(col, width=100, anchor='center')
        
        self.watch_tree.pack(fill=tk.BOTH, expand=True)
        
        self._load_watchlist()
    
    def _load_watchlist(self):
        for item in self.watch_tree.get_children():
            self.watch_tree.delete(item)
        
        stocks = self.data_manager.get_stock_list()
        for stock in stocks:
            self.watch_tree.insert('', tk.END, values=(
                stock.get('symbol', ''),
                stock.get('name', ''),
                '--',
                '--',
                '--'
            ))
    
    def _open_account_settings(self):
        messagebox.showinfo("提示", "账户设置功能开发中...")
    
    def _open_buy(self):
        messagebox.showinfo("提示", "买入功能开发中...")
    
    def _open_sell(self):
        messagebox.showinfo("提示", "卖出功能开发中...")
    
    def _open_orders(self):
        messagebox.showinfo("提示", "委托查询功能开发中...")
    
    def _open_watchlist(self):
        messagebox.showinfo("提示", "自选股管理功能开发中...")
    
    def _open_alerts(self):
        messagebox.showinfo("提示", "价格预警功能开发中...")
    
    def run(self):
        self.root.mainloop()


def main():
    app = TradingApp()
    app.run()


if __name__ == "__main__":
    main()
