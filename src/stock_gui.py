import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import os
from datetime import datetime, timedelta
import requests
import finnhub
import threading
from config import FINNHUB_API_KEY
from data_manager import StockDataManager
from kline_manager import KLineManager


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


class StockGUI:
    PERIODS = {
        '1min': '1分钟',
        '5min': '5分钟',
        '15min': '15分钟',
        '1hour': '1小时',
        'daily': '日线'
    }
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("股票行情系统")
        self.root.geometry("1000x700")
        self.root.minsize(800, 600)
        
        self.finnhub_client = None
        if FINNHUB_API_KEY:
            self.finnhub_client = finnhub.Client(api_key=FINNHUB_API_KEY)
        
        self.eastmoney_client = EastMoneyAPI()
        self.data_manager = StockDataManager()
        self.kline_manager = KLineManager()
        
        self.current_frame = None
        self.cached_quotes = {}
        self.current_kline_data = None
        self.current_period = 'daily'
        self.current_symbol = None
        self.current_name = None
        self.current_market = None
        
        self.display_count = 120
        self.display_start = 0
        self.crosshair_x = None
        self.crosshair_y = None
        self.crosshair_items = []
        self.info_label_items = []
        self.current_stock_index = -1
        
        self.current_page = 1
        self.page_size = 100
        self.total_stocks = 0
        self.all_stocks_data = []
        self.message_log = []
        
        self.show_stock_list()
    
    def clear_frame(self):
        if self.current_frame:
            self.current_frame.destroy()
    
    def show_stock_list(self):
        self.clear_frame()
        self.root.title("股票行情系统 - 股票列表")
        
        self.current_frame = ttk.Frame(self.root, padding="10")
        self.current_frame.pack(fill=tk.BOTH, expand=True)
        
        title_label = ttk.Label(self.current_frame, text="股票列表", font=('Microsoft YaHei', 16, 'bold'))
        title_label.pack(pady=(0, 10))
        
        btn_frame = ttk.Frame(self.current_frame)
        btn_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.refresh_btn = ttk.Button(btn_frame, text="刷新行情", command=self.start_refresh_quotes)
        self.refresh_btn.pack(side=tk.LEFT, padx=5)
        
        kline_btn = ttk.Button(btn_frame, text="查看K线", command=self.view_kline)
        kline_btn.pack(side=tk.LEFT, padx=5)
        
        load_btn = ttk.Button(btn_frame, text="装载列表", command=self.load_config_file)
        load_btn.pack(side=tk.LEFT, padx=5)
        
        main_frame = ttk.Frame(self.current_frame)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        left_frame = ttk.Frame(main_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        columns = ('symbol', 'name', 'market', 'price', 'change', 'change_pct')
        self.tree = ttk.Treeview(left_frame, columns=columns, show='headings', height=20)
        
        self.tree.heading('symbol', text='代码')
        self.tree.heading('name', text='名称')
        self.tree.heading('market', text='市场')
        self.tree.heading('price', text='当前价')
        self.tree.heading('change', text='涨跌额')
        self.tree.heading('change_pct', text='涨跌幅')
        
        self.tree.column('symbol', width=100, anchor='center')
        self.tree.column('name', width=120, anchor='center')
        self.tree.column('market', width=80, anchor='center')
        self.tree.column('price', width=100, anchor='center')
        self.tree.column('change', width=100, anchor='center')
        self.tree.column('change_pct', width=100, anchor='center')
        
        scrollbar = ttk.Scrollbar(left_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.tree.bind('<Double-1>', self.on_double_click)
        self.tree.bind('<Return>', self.on_enter_key)
        
        right_frame = ttk.Frame(main_frame, width=250)
        right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
        right_frame.pack_propagate(False)
        
        msg_title = ttk.Label(right_frame, text="消息栏", font=('Microsoft YaHei', 11, 'bold'))
        msg_title.pack(pady=(0, 5))
        
        self.msg_text = tk.Text(right_frame, wrap=tk.WORD, font=('Microsoft YaHei', 9), state='disabled')
        msg_scrollbar = ttk.Scrollbar(right_frame, orient=tk.VERTICAL, command=self.msg_text.yview)
        self.msg_text.configure(yscrollcommand=msg_scrollbar.set)
        
        self.msg_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        msg_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        page_frame = ttk.Frame(self.current_frame)
        page_frame.pack(fill=tk.X, pady=5)
        
        self.page_label = ttk.Label(page_frame, text="", font=('Microsoft YaHei', 10))
        self.page_label.pack(side=tk.LEFT, padx=10)
        
        self.prev_btn = ttk.Button(page_frame, text="上一页", command=self.prev_page)
        self.prev_btn.pack(side=tk.LEFT, padx=5)
        
        self.next_btn = ttk.Button(page_frame, text="下一页", command=self.next_page)
        self.next_btn.pack(side=tk.LEFT, padx=5)
        
        self.status_label = ttk.Label(page_frame, text="", font=('Microsoft YaHei', 10))
        self.status_label.pack(side=tk.LEFT, padx=20)
        
        self._init_page_data()
    
    def _init_page_data(self):
        stocks = self.data_manager.get_stock_list()
        self.total_stocks = len(stocks)
        self.all_stocks_data = []
        
        for stock in stocks:
            symbol = stock.get('symbol', '')
            name = stock.get('name', '')
            market = stock.get('market', '美股')
            cache_key = f"{symbol}_{market}"
            
            if cache_key in self.cached_quotes:
                cached = self.cached_quotes[cache_key]
                self.all_stocks_data.append({
                    'symbol': symbol,
                    'name': name,
                    'market': market,
                    'price': cached['price'],
                    'change': cached['change'],
                    'change_pct': cached['change_pct']
                })
            else:
                self.all_stocks_data.append({
                    'symbol': symbol,
                    'name': name,
                    'market': market,
                    'price': '加载中...',
                    'change': '加载中...',
                    'change_pct': '加载中'
                })
        
        self.current_page = 1
        self._update_page_display()
        self._update_page_buttons()
        self.add_message(f"已加载 {self.total_stocks} 只股票")
    
    def _update_page_display(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        start_idx = (self.current_page - 1) * self.page_size
        end_idx = min(start_idx + self.page_size, self.total_stocks)
        
        for i in range(start_idx, end_idx):
            data = self.all_stocks_data[i]
            self.tree.insert('', tk.END, values=(
                data['symbol'], data['name'], data['market'],
                data['price'], data['change'], data['change_pct']
            ))
        
        total_pages = (self.total_stocks + self.page_size - 1) // self.page_size
        self.page_label.config(text=f"第 {self.current_page}/{total_pages} 页 (共 {self.total_stocks} 只股票)")
    
    def _update_page_buttons(self):
        total_pages = (self.total_stocks + self.page_size - 1) // self.page_size
        self.prev_btn.config(state='normal' if self.current_page > 1 else 'disabled')
        self.next_btn.config(state='normal' if self.current_page < total_pages else 'disabled')
    
    def prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self._update_page_display()
            self._update_page_buttons()
    
    def next_page(self):
        total_pages = (self.total_stocks + self.page_size - 1) // self.page_size
        if self.current_page < total_pages:
            self.current_page += 1
            self._update_page_display()
            self._update_page_buttons()
    
    def add_message(self, msg):
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.message_log.append(f"[{timestamp}] {msg}")
        
        self.msg_text.config(state='normal')
        self.msg_text.insert(tk.END, f"[{timestamp}] {msg}\n")
        self.msg_text.see(tk.END)
        self.msg_text.config(state='disabled')
    
    def load_config_file(self):
        file_path = filedialog.askopenfilename(
            title="选择配置文件",
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")],
            initialdir=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config')
        )
        
        if not file_path:
            return
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            if 'stocks' not in config_data:
                messagebox.showerror("错误", "配置文件格式错误：缺少stocks字段")
                return
            
            config = self.data_manager.load_stocks_config()
            config['stocks'] = config_data['stocks']
            self.data_manager.save_stocks_config(config)
            self.data_manager._config_cache = None
            
            self.cached_quotes = {}
            self.add_message(f"已从 {os.path.basename(file_path)} 装载 {len(config_data['stocks'])} 只股票")
            
            self._init_page_data()
            self.start_refresh_quotes()
            
        except Exception as e:
            messagebox.showerror("错误", f"装载配置文件失败: {str(e)}")
            self.add_message(f"装载失败: {str(e)}")
    
    def _display_cached_quotes(self):
        self._init_page_data()
    
    def start_refresh_quotes(self):
        self.refresh_btn.config(state='disabled')
        self.status_label.config(text="正在刷新...")
        self.add_message("开始刷新行情数据...")
        
        thread = threading.Thread(target=self._fetch_quotes_thread, daemon=True)
        thread.start()
    
    def _fetch_quotes_thread(self):
        stocks = self.data_manager.get_stock_list()
        results = []
        
        for stock in stocks:
            symbol = stock.get('symbol', '')
            name = stock.get('name', '')
            market = stock.get('market', '美股')
            
            quote = self.get_stock_quote(symbol, market)
            
            if quote and quote.get('c') is not None:
                price = f"{quote['c']:.2f}"
                change = quote['d']
                change_pct = quote['dp']
                
                change_str = f"+{change:.2f}" if change >= 0 else f"{change:.2f}"
                change_pct_str = f"+{change_pct:.2f}%" if change_pct >= 0 else f"{change_pct:.2f}%"
            else:
                price = 'N/A'
                change_str = 'N/A'
                change_pct_str = 'N/A'
            
            cache_key = f"{symbol}_{market}"
            self.cached_quotes[cache_key] = {
                'price': price,
                'change': change_str,
                'change_pct': change_pct_str
            }
            
            results.append((symbol, name, market, price, change_str, change_pct_str))
        
        self.root.after(0, lambda: self._update_quotes_ui(results))
    
    def _update_quotes_ui(self, results):
        self.all_stocks_data = []
        for data in results:
            self.all_stocks_data.append({
                'symbol': data[0],
                'name': data[1],
                'market': data[2],
                'price': data[3],
                'change': data[4],
                'change_pct': data[5]
            })
        
        self._update_page_display()
        
        self.refresh_btn.config(state='normal')
        self.status_label.config(text=f"刷新完成 {datetime.now().strftime('%H:%M:%S')}")
        self.add_message(f"行情刷新完成，共 {len(results)} 只股票")
    
    def get_stock_quote(self, symbol, market='美股'):
        if market == 'A股':
            return self.eastmoney_client.get_quote(symbol)
        else:
            if not self.finnhub_client:
                return None
            try:
                quote = self.finnhub_client.quote(symbol)
                return quote
            except Exception as e:
                print(f"获取 {symbol} 报价失败: {e}")
                return None
    
    def get_stock_kline(self, symbol, market='美股', period='daily'):
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
    
    def on_double_click(self, event):
        self.view_kline()
    
    def on_enter_key(self, event):
        self.view_kline()
    
    def view_kline(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("提示", "请先选择一只股票")
            return
        
        item_id = selected[0]
        children = self.tree.get_children()
        self.current_stock_index = children.index(item_id)
        
        item = self.tree.item(item_id)
        values = item['values']
        
        self.current_symbol = values[0]
        self.current_name = values[1]
        self.current_market = values[2]
        self.current_period = 'daily'
        self.display_count = 120
        self.display_start = 0
        
        self.show_kline_chart()
    
    def show_kline_chart(self):
        self.clear_frame()
        self.root.title(f"股票行情系统 - {self.current_name} ({self.current_symbol}) K线图")
        
        self.current_frame = ttk.Frame(self.root, padding="10")
        self.current_frame.pack(fill=tk.BOTH, expand=True)
        
        title_label = ttk.Label(self.current_frame, text=f"{self.current_name} ({self.current_symbol}) - {self.current_market}", font=('Microsoft YaHei', 16, 'bold'))
        title_label.pack(pady=(0, 5))
        
        toolbar = ttk.Frame(self.current_frame)
        toolbar.pack(fill=tk.X, pady=5)
        
        ttk.Label(toolbar, text="周期:", font=('Microsoft YaHei', 10)).pack(side=tk.LEFT, padx=5)
        
        self.period_var = tk.StringVar(value=self.current_period)
        for period_key, period_name in self.PERIODS.items():
            rb = ttk.Radiobutton(
                toolbar, text=period_name, value=period_key,
                variable=self.period_var, command=self._on_period_change
            )
            rb.pack(side=tk.LEFT, padx=3)
        
        ttk.Label(toolbar, text="  |  ↑↓键缩放  鼠标移动显示十字线", font=('Microsoft YaHei', 9), foreground='gray').pack(side=tk.LEFT, padx=10)
        
        self.kline_canvas = tk.Canvas(self.current_frame, bg='white', highlightthickness=1, highlightbackground='gray')
        self.kline_canvas.pack(fill=tk.BOTH, expand=True)
        
        self.kline_canvas.bind('<Configure>', self._on_canvas_resize)
        self.kline_canvas.bind('<Motion>', self._on_mouse_move)
        self.kline_canvas.bind('<Leave>', self._on_mouse_leave)
        self.root.bind('<Up>', self._on_key_up)
        self.root.bind('<Down>', self._on_key_down)
        self.root.bind('<Left>', self._on_key_left)
        self.root.bind('<Right>', self._on_key_right)
        self.root.bind('<Prior>', self._on_page_up)
        self.root.bind('<Next>', self._on_page_down)
        self.root.bind('<Escape>', self._on_escape)
        
        btn_frame = ttk.Frame(self.current_frame)
        btn_frame.pack(fill=tk.X, pady=10)
        
        back_btn = ttk.Button(btn_frame, text="返回列表", command=self._back_to_list)
        back_btn.pack(side=tk.LEFT, padx=5)
        
        refresh_btn = ttk.Button(btn_frame, text="刷新数据", command=self._refresh_kline_data)
        refresh_btn.pack(side=tk.LEFT, padx=5)
        
        self.kline_status_label = ttk.Label(btn_frame, text="", font=('Microsoft YaHei', 10))
        self.kline_status_label.pack(side=tk.LEFT, padx=20)
        
        self._load_kline_data()
    
    def _back_to_list(self):
        self.root.unbind('<Up>')
        self.root.unbind('<Down>')
        self.root.unbind('<Left>')
        self.root.unbind('<Right>')
        self.root.unbind('<Prior>')
        self.root.unbind('<Next>')
        self.root.unbind('<Escape>')
        self.show_stock_list()
    
    def _on_escape(self, event):
        self._back_to_list()
    
    def _on_page_up(self, event):
        self._switch_stock(-1)
    
    def _on_page_down(self, event):
        self._switch_stock(1)
    
    def _switch_stock(self, direction):
        stocks = self.data_manager.get_stock_list()
        if not stocks:
            return
        
        new_index = self.current_stock_index + direction
        if new_index < 0:
            new_index = len(stocks) - 1
        elif new_index >= len(stocks):
            new_index = 0
        
        self.current_stock_index = new_index
        stock = stocks[new_index]
        
        self.current_symbol = stock.get('symbol', '')
        self.current_name = stock.get('name', '')
        self.current_market = stock.get('market', '美股')
        self.display_count = 120
        self.display_start = 0
        
        self.root.title(f"股票行情系统 - {self.current_name} ({self.current_symbol}) K线图")
        
        for widget in self.current_frame.winfo_children():
            if isinstance(widget, ttk.Label) and 'bold' in str(widget.cget('font')):
                widget.config(text=f"{self.current_name} ({self.current_symbol}) - {self.current_market}")
                break
        
        self._load_kline_data()
    
    def _on_period_change(self):
        new_period = self.period_var.get()
        if new_period != self.current_period:
            self.current_period = new_period
            self.display_count = 120
            self.display_start = 0
            self._load_kline_data()
    
    def _load_kline_data(self):
        self.kline_status_label.config(text="正在加载...")
        self.kline_canvas.delete('all')
        self.kline_loading_label = ttk.Label(self.kline_canvas, text="正在加载K线数据...", font=('Microsoft YaHei', 12))
        self.kline_canvas.create_window(400, 250, window=self.kline_loading_label)
        
        thread = threading.Thread(target=self._fetch_kline_thread, daemon=True)
        thread.start()
    
    def _fetch_kline_thread(self):
        kline_data = self.get_stock_kline(self.current_symbol, self.current_market, period=self.current_period)
        self.root.after(0, lambda: self._update_kline_ui(kline_data))
    
    def _refresh_kline_data(self):
        self.kline_manager.download_kline_data(self.current_symbol, self.current_market, self.current_period)
        self._load_kline_data()
    
    def _on_canvas_resize(self, event):
        if self.current_kline_data:
            self.root.after(100, self._redraw_kline)
    
    def _redraw_kline(self):
        if self.current_kline_data and hasattr(self, 'kline_canvas'):
            self.kline_canvas.delete('all')
            self.draw_candlestick(self.kline_canvas, self._get_display_data())
    
    def _get_display_data(self):
        if not self.current_kline_data:
            return []
        
        total = len(self.current_kline_data)
        if self.display_start < 0:
            self.display_start = 0
        if self.display_start >= total:
            self.display_start = max(0, total - self.display_count)
        
        end_idx = min(self.display_start + self.display_count, total)
        return self.current_kline_data[self.display_start:end_idx]
    
    def _on_key_up(self, event):
        if self.current_kline_data:
            total = len(self.current_kline_data)
            old_end = min(self.display_start + self.display_count, total)
            self.display_count = max(20, self.display_count - 20)
            self.display_start = max(0, old_end - self.display_count)
            self._redraw_kline()
            self._update_status_with_count()
    
    def _on_key_down(self, event):
        if self.current_kline_data:
            total = len(self.current_kline_data)
            old_end = min(self.display_start + self.display_count, total)
            self.display_count = min(total, self.display_count + 20)
            self.display_start = max(0, old_end - self.display_count)
            self._redraw_kline()
            self._update_status_with_count()
    
    def _on_key_left(self, event):
        if self.current_kline_data:
            if self.display_start > 0:
                self.display_start = max(0, self.display_start - 10)
                self._redraw_kline()
                self._update_status_with_count()
    
    def _on_key_right(self, event):
        if self.current_kline_data:
            total = len(self.current_kline_data)
            if self.display_start + self.display_count < total:
                self.display_start = min(total - self.display_count, self.display_start + 10)
                self._redraw_kline()
                self._update_status_with_count()
    
    def _update_status_with_count(self):
        if self.current_kline_data:
            total = len(self.current_kline_data)
            end_idx = min(self.display_start + self.display_count, total)
            period_name = self.PERIODS.get(self.current_period, self.current_period)
            self.kline_status_label.config(text=f"{period_name} 显示 {self.display_start+1}-{end_idx}/{total} 根K线")
    
    def _on_mouse_move(self, event):
        if not self.current_kline_data:
            return
        
        self._clear_crosshair()
        
        canvas = self.kline_canvas
        x, y = event.x, event.y
        
        canvas_width = canvas.winfo_width()
        canvas_height = canvas.winfo_height()
        
        margin_left = 80
        margin_right = 20
        margin_top = 40
        margin_bottom = 60
        
        if x < margin_left or x > canvas_width - margin_right:
            return
        if y < margin_top or y > canvas_height - margin_bottom:
            return
        
        chart_width = canvas_width - margin_left - margin_right
        chart_height = canvas_height - margin_top - margin_bottom
        
        display_data = self._get_display_data()
        if not display_data:
            return
        
        candle_gap = chart_width / len(display_data)
        candle_index = int((x - margin_left) / candle_gap)
        
        if candle_index < 0 or candle_index >= len(display_data):
            return
        
        data = display_data[candle_index]
        
        v_line = canvas.create_line(x, margin_top, x, canvas_height - margin_bottom, fill='#666666', width=1, dash=(3, 3))
        h_line = canvas.create_line(margin_left, y, canvas_width - margin_right, y, fill='#666666', width=1, dash=(3, 3))
        self.crosshair_items.extend([v_line, h_line])
        
        prices = []
        for d in display_data:
            prices.extend([d['high'], d['low']])
        min_price = min(prices)
        max_price = max(prices)
        price_range = max_price - min_price if max_price != min_price else 1
        
        price_at_y = max_price - (y - margin_top) / chart_height * price_range
        
        price_text = canvas.create_text(canvas_width - margin_right + 5, y, text=f"{price_at_y:.2f}", anchor='w', font=('Arial', 9), fill='#0066cc')
        self.crosshair_items.append(price_text)
        
        info_text = f"日期:{data['date']} 开:{data['open']:.2f} 高:{data['high']:.2f} 低:{data['low']:.2f} 收:{data['close']:.2f}"
        info_bg = canvas.create_rectangle(margin_left, margin_top - 25, margin_left + 380, margin_top - 5, fill='#ffffcc', outline='#cccc00')
        info_label = canvas.create_text(margin_left + 5, margin_top - 15, text=info_text, anchor='w', font=('Microsoft YaHei', 9), fill='#333333')
        self.crosshair_items.extend([info_bg, info_label])
    
    def _on_mouse_leave(self, event):
        self._clear_crosshair()
    
    def _clear_crosshair(self):
        for item in self.crosshair_items:
            try:
                self.kline_canvas.delete(item)
            except:
                pass
        self.crosshair_items = []
    
    def _update_kline_ui(self, kline_data):
        self.current_kline_data = kline_data
        self.kline_canvas.delete('all')
        
        if not kline_data:
            error_label = ttk.Label(self.kline_canvas, text="无法获取K线数据", font=('Microsoft YaHei', 12), foreground='red')
            self.kline_canvas.create_window(400, 250, window=error_label)
            self.kline_status_label.config(text="加载失败")
        else:
            total = len(kline_data)
            self.display_start = max(0, total - self.display_count)
            self.draw_candlestick(self.kline_canvas, self._get_display_data())
            self._update_status_with_count()
    
    def draw_candlestick(self, canvas, kline_data):
        canvas.update_idletasks()
        canvas_width = canvas.winfo_width()
        canvas_height = canvas.winfo_height()
        
        if canvas_width < 100 or canvas_height < 100:
            canvas_width = 900
            canvas_height = 500
        
        margin_left = 80
        margin_right = 20
        margin_top = 40
        margin_bottom = 60
        
        chart_width = canvas_width - margin_left - margin_right
        chart_height = canvas_height - margin_top - margin_bottom
        
        if not kline_data or chart_width <= 0 or chart_height <= 0:
            return
        
        prices = []
        for d in kline_data:
            prices.extend([d['high'], d['low']])
        
        min_price = min(prices)
        max_price = max(prices)
        price_range = max_price - min_price
        
        if price_range == 0:
            price_range = 1
        
        candle_width = max(3, chart_width / len(kline_data) - 2)
        candle_gap = chart_width / len(kline_data)
        
        period_name = self.PERIODS.get(self.current_period, self.current_period)
        canvas.create_text(canvas_width // 2, 15, text=f"K线图 ({period_name})", font=('Microsoft YaHei', 12, 'bold'))
        
        for i in range(5):
            y = margin_top + i * chart_height / 4
            price = max_price - (price_range * i / 4)
            canvas.create_line(margin_left, y, canvas_width - margin_right, y, fill='#e0e0e0', dash=(2, 2))
            canvas.create_text(margin_left - 10, y, text=f"{price:.2f}", anchor='e', font=('Arial', 9))
        
        for i, data in enumerate(kline_data):
            x = margin_left + i * candle_gap + candle_gap / 2
            
            open_price = data['open']
            close_price = data['close']
            high_price = data['high']
            low_price = data['low']
            
            y_open = margin_top + (max_price - open_price) / price_range * chart_height
            y_close = margin_top + (max_price - close_price) / price_range * chart_height
            y_high = margin_top + (max_price - high_price) / price_range * chart_height
            y_low = margin_top + (max_price - low_price) / price_range * chart_height
            
            if close_price >= open_price:
                color = '#ff4444'
                fill_color = '#ff4444'
            else:
                color = '#00aa00'
                fill_color = '#00aa00'
            
            canvas.create_line(x, y_high, x, y_low, fill=color, width=1)
            
            body_top = min(y_open, y_close)
            body_height = max(abs(y_close - y_open), 1)
            
            canvas.create_rectangle(
                x - candle_width/2, body_top,
                x + candle_width/2, body_top + body_height,
                fill=fill_color, outline=color
            )
            
            if i % max(1, len(kline_data) // 6) == 0:
                date_str = data['date']
                if len(date_str) > 5:
                    date_str = date_str[5:]
                canvas.create_text(x, canvas_height - margin_bottom + 15, text=date_str, anchor='n', font=('Arial', 8))
        
        canvas.create_text(margin_left - 40, margin_top + chart_height / 2, text="价格", anchor='center', font=('Microsoft YaHei', 10), angle=90)
        canvas.create_text(canvas_width // 2, canvas_height - 15, text="日期", anchor='center', font=('Microsoft YaHei', 10))
    
    def run(self):
        self.root.mainloop()


def main():
    app = StockGUI()
    app.run()


if __name__ == "__main__":
    main()
