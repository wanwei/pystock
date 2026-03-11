import tkinter as tk
from tkinter import ttk
import threading


class StockListWidget(ttk.Frame):
    """
    股票列表组件
    
    可复用的股票列表显示组件，支持：
    - 分页显示
    - 搜索筛选
    - 双击/回车选择
    - 从K线数据获取补充信息（最新价、涨跌幅、数据量等）
    """
    
    COLUMNS = ('symbol', 'name', 'market', 'latest_price', 'change_pct', 'data_count', 'latest_date')
    
    def __init__(self, parent, data_manager, on_select=None, on_double_click=None, stocks_source='list', **kwargs):
        super().__init__(parent, **kwargs)
        
        self.data_manager = data_manager
        self.on_select = on_select
        self.on_double_click = on_double_click
        self.stocks_source = stocks_source
        
        self.current_page = 1
        self.page_size = 100
        self.total_stocks = 0
        self.all_stocks_data = []
        
        self._create_widgets()
        self._init_data()
    
    def _create_widgets(self):
        style = ttk.Style()
        style.configure('StockList.Treeview', font=('Microsoft YaHei', 11), rowheight=28)
        style.configure('StockList.TButton', font=('Microsoft YaHei', 11))
        style.configure('StockList.TLabel', font=('Microsoft YaHei', 11))
        
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(btn_frame, text="搜索:", style='StockList.TLabel').pack(side=tk.LEFT, padx=(10, 2))
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(btn_frame, textvariable=self.search_var, width=15, font=('Microsoft YaHei', 11))
        self.search_entry.pack(side=tk.LEFT, padx=2)
        self.search_entry.bind('<Return>', self._on_search)
        
        ttk.Button(btn_frame, text="搜索", command=self._on_search, style='StockList.TButton').pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="重置", command=self._reset_search, style='StockList.TButton').pack(side=tk.LEFT, padx=2)
        
        ttk.Button(btn_frame, text="刷新K线数据", command=self._refresh_kline_info, style='StockList.TButton').pack(side=tk.LEFT, padx=10)
        
        list_frame = ttk.Frame(self)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        self.tree = ttk.Treeview(list_frame, columns=self.COLUMNS, show='headings', height=20, style='StockList.Treeview')
        
        self.tree.heading('symbol', text='代码')
        self.tree.heading('name', text='名称')
        self.tree.heading('market', text='市场')
        self.tree.heading('latest_price', text='最新价')
        self.tree.heading('change_pct', text='涨跌幅(%)')
        self.tree.heading('data_count', text='K线数')
        self.tree.heading('latest_date', text='最新日期')
        
        self.tree.column('symbol', width=110, anchor='center')
        self.tree.column('name', width=130, anchor='center')
        self.tree.column('market', width=90, anchor='center')
        self.tree.column('latest_price', width=100, anchor='center')
        self.tree.column('change_pct', width=100, anchor='center')
        self.tree.column('data_count', width=90, anchor='center')
        self.tree.column('latest_date', width=120, anchor='center')
        
        scrollbar_y = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar_x = ttk.Scrollbar(list_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.tree.bind('<<TreeviewSelect>>', self._on_tree_select)
        self.tree.bind('<Double-1>', self._on_tree_double_click)
        self.tree.bind('<Return>', self._on_tree_double_click)
        
        page_frame = ttk.Frame(self)
        page_frame.pack(fill=tk.X, pady=5)
        
        self.page_label = ttk.Label(page_frame, text="", font=('Microsoft YaHei', 11))
        self.page_label.pack(side=tk.LEFT, padx=10)
        
        self.prev_btn = ttk.Button(page_frame, text="上一页", command=self.prev_page, style='StockList.TButton')
        self.prev_btn.pack(side=tk.LEFT, padx=5)
        
        self.next_btn = ttk.Button(page_frame, text="下一页", command=self.next_page, style='StockList.TButton')
        self.next_btn.pack(side=tk.LEFT, padx=5)
    
    def _get_stocks(self):
        if self.stocks_source == 'config':
            return self.data_manager.config.get_stock_list()
        else:
            return self.data_manager.get_stock_list()
    
    def _init_data(self):
        stocks = self._get_stocks()
        self.total_stocks = len(stocks)
        self.all_stocks_data = []
        
        for stock in stocks:
            self.all_stocks_data.append({
                'symbol': stock.get('symbol', ''),
                'name': stock.get('name', ''),
                'market': stock.get('market', '美股'),
                'latest_price': '-',
                'change_pct': '-',
                'data_count': '-',
                'latest_date': '-'
            })
        
        self.current_page = 1
        self._update_page_display()
        self._update_page_buttons()
    
    def _refresh_kline_info(self):
        self._load_kline_info_async()
    
    def _load_kline_info_async(self):
        def load_thread():
            for i, stock in enumerate(self.all_stocks_data):
                try:
                    symbol = stock.get('symbol', '')
                    market = stock.get('market', 'A股')
                    
                    df = self.data_manager.kline.get_data(symbol, market, 'daily')
                    
                    if df is not None and not df.empty:
                        latest_row = df.iloc[-1]
                        prev_close = df.iloc[-2]['close'] if len(df) > 1 else latest_row['close']
                        
                        latest_price = latest_row['close']
                        change_pct = ((latest_price - prev_close) / prev_close * 100) if prev_close > 0 else 0
                        data_count = len(df)
                        latest_date = str(latest_row['date']).split(' ')[0]
                        
                        self.all_stocks_data[i]['latest_price'] = f"{latest_price:.2f}"
                        self.all_stocks_data[i]['change_pct'] = f"{change_pct:.2f}"
                        self.all_stocks_data[i]['data_count'] = str(data_count)
                        self.all_stocks_data[i]['latest_date'] = latest_date
                        
                        if i % 50 == 0:
                            self.after(0, self._update_page_display)
                except Exception as e:
                    pass
            
            self.after(0, self._update_page_display)
        
        thread = threading.Thread(target=load_thread, daemon=True)
        thread.start()
    
    def _update_page_display(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        start_idx = (self.current_page - 1) * self.page_size
        end_idx = min(start_idx + self.page_size, self.total_stocks)
        
        for i in range(start_idx, end_idx):
            data = self.all_stocks_data[i]
            values = tuple(data.get(col, '-') for col in self.COLUMNS)
            item_id = self.tree.insert('', tk.END, values=values)
            
            change_pct_str = data.get('change_pct', '-')
            if change_pct_str != '-':
                try:
                    change_pct = float(change_pct_str)
                    if change_pct > 0:
                        self.tree.item(item_id, tags=('up',))
                    elif change_pct < 0:
                        self.tree.item(item_id, tags=('down',))
                except:
                    pass
        
        self.tree.tag_configure('up', foreground='red')
        self.tree.tag_configure('down', foreground='green')
        
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
        for stock in self._get_stocks():
            symbol = stock.get('symbol', '').lower()
            name = stock.get('name', '').lower()
            if keyword in symbol or keyword in name:
                filtered.append({
                    'symbol': stock.get('symbol'),
                    'name': stock.get('name'),
                    'market': stock.get('market', '美股'),
                    'latest_price': '-',
                    'change_pct': '-',
                    'data_count': '-',
                    'latest_date': '-'
                })
        
        self.all_stocks_data = filtered
        self.total_stocks = len(filtered)
        self.current_page = 1
        self._update_page_display()
        self._update_page_buttons()
        self._load_kline_info_async()
    
    def _reset_search(self):
        self.search_var.set('')
        self._init_data()
    
    def refresh(self):
        self._init_data()
    
    def _on_tree_select(self, event):
        if self.on_select:
            stock = self.get_selected_stock()
            if stock:
                self.on_select(stock)
    
    def _on_tree_double_click(self, event):
        if self.on_double_click:
            stock = self.get_selected_stock()
            if stock:
                self.on_double_click(stock)
    
    def get_selected_stock(self):
        selected = self.tree.selection()
        if not selected:
            return None
        
        item_id = selected[0]
        children = self.tree.get_children()
        idx = children.index(item_id)
        
        start_idx = (self.current_page - 1) * self.page_size
        actual_idx = start_idx + idx
        
        if actual_idx < len(self.all_stocks_data):
            return self.all_stocks_data[actual_idx]
        
        return None
