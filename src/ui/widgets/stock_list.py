import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import os
from datetime import datetime
import threading


class StockListWidget(ttk.Frame):
    """
    股票列表组件
    
    可复用的股票列表显示组件，支持：
    - 分页显示
    - 搜索筛选
    - 双击/回车选择
    - 批量选中
    """
    
    def __init__(self, parent, data_manager, on_select=None, on_double_click=None, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.data_manager = data_manager
        self.on_select = on_select
        self.on_double_click = on_double_click
        
        self.current_page = 1
        self.page_size = 100
        self.total_stocks = 0
        self.all_stocks_data = []
        self.cached_quotes = {}
        
        self._create_widgets()
        self._init_data()
    
    def _create_widgets(self):
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, pady=(0, 5))
        
        self.refresh_btn = ttk.Button(btn_frame, text="刷新行情", command=self.start_refresh_quotes)
        self.refresh_btn.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(btn_frame, text="搜索:").pack(side=tk.LEFT, padx=(10, 2))
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(btn_frame, textvariable=self.search_var, width=15)
        self.search_entry.pack(side=tk.LEFT, padx=2)
        self.search_entry.bind('<Return>', self._on_search)
        
        ttk.Button(btn_frame, text="搜索", command=self._on_search).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="重置", command=self._reset_search).pack(side=tk.LEFT, padx=2)
        
        list_frame = ttk.Frame(self)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        columns = ('symbol', 'name', 'market', 'price', 'change', 'change_pct')
        self.tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=20)
        
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
        
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.tree.bind('<<TreeviewSelect>>', self._on_tree_select)
        self.tree.bind('<Double-1>', self._on_tree_double_click)
        self.tree.bind('<Return>', self._on_tree_double_click)
        
        page_frame = ttk.Frame(self)
        page_frame.pack(fill=tk.X, pady=5)
        
        self.page_label = ttk.Label(page_frame, text="", font=('Microsoft YaHei', 10))
        self.page_label.pack(side=tk.LEFT, padx=10)
        
        self.prev_btn = ttk.Button(page_frame, text="上一页", command=self.prev_page)
        self.prev_btn.pack(side=tk.LEFT, padx=5)
        
        self.next_btn = ttk.Button(page_frame, text="下一页", command=self.next_page)
        self.next_btn.pack(side=tk.LEFT, padx=5)
        
        self.status_label = ttk.Label(page_frame, text="", font=('Microsoft YaHei', 10))
        self.status_label.pack(side=tk.LEFT, padx=20)
    
    def _init_data(self):
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
    
    def _on_search(self, event=None):
        keyword = self.search_var.get().strip().lower()
        if not keyword:
            self._init_data()
            return
        
        filtered = []
        for stock in self.data_manager.get_stock_list():
            symbol = stock.get('symbol', '').lower()
            name = stock.get('name', '').lower()
            if keyword in symbol or keyword in name:
                market = stock.get('market', '美股')
                cache_key = f"{stock.get('symbol')}_{market}"
                if cache_key in self.cached_quotes:
                    cached = self.cached_quotes[cache_key]
                    filtered.append({
                        'symbol': stock.get('symbol'),
                        'name': stock.get('name'),
                        'market': market,
                        'price': cached['price'],
                        'change': cached['change'],
                        'change_pct': cached['change_pct']
                    })
                else:
                    filtered.append({
                        'symbol': stock.get('symbol'),
                        'name': stock.get('name'),
                        'market': market,
                        'price': '-',
                        'change': '-',
                        'change_pct': '-'
                    })
        
        self.all_stocks_data = filtered
        self.total_stocks = len(filtered)
        self.current_page = 1
        self._update_page_display()
        self._update_page_buttons()
    
    def _reset_search(self):
        self.search_var.set('')
        self._init_data()
    
    def _on_tree_select(self, event):
        if self.on_select:
            selected = self.tree.selection()
            if selected:
                item = self.tree.item(selected[0])
                self.on_select(item['values'])
    
    def _on_tree_double_click(self, event):
        if self.on_double_click:
            selected = self.tree.selection()
            if selected:
                item = self.tree.item(selected[0])
                self.on_double_click(item['values'])
    
    def get_selected_stock(self):
        selected = self.tree.selection()
        if not selected:
            return None
        item = self.tree.item(selected[0])
        values = item['values']
        return {
            'symbol': values[0],
            'name': values[1],
            'market': values[2]
        }
    
    def start_refresh_quotes(self, quote_fetcher=None):
        self.refresh_btn.config(state='disabled')
        self.status_label.config(text="正在刷新...")
        
        thread = threading.Thread(
            target=self._fetch_quotes_thread,
            args=(quote_fetcher,),
            daemon=True
        )
        thread.start()
    
    def _fetch_quotes_thread(self, quote_fetcher):
        stocks = self.data_manager.get_stock_list()
        results = []
        
        for stock in stocks:
            symbol = stock.get('symbol', '')
            name = stock.get('name', '')
            market = stock.get('market', '美股')
            
            if quote_fetcher:
                quote = quote_fetcher(symbol, market)
            else:
                quote = None
            
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
        
        self.after(0, lambda: self._update_quotes_ui(results))
    
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
