import tkinter as tk
from tkinter import ttk


class StockListWidget(ttk.Frame):
    """
    股票列表组件
    
    可复用的股票列表显示组件，支持：
    - 分页显示
    - 搜索筛选
    - 双击/回车选择
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
        
        self._create_widgets()
        self._init_data()
    
    def _create_widgets(self):
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(btn_frame, text="搜索:").pack(side=tk.LEFT, padx=(10, 2))
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(btn_frame, textvariable=self.search_var, width=15)
        self.search_entry.pack(side=tk.LEFT, padx=2)
        self.search_entry.bind('<Return>', self._on_search)
        
        ttk.Button(btn_frame, text="搜索", command=self._on_search).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="重置", command=self._reset_search).pack(side=tk.LEFT, padx=2)
        
        list_frame = ttk.Frame(self)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        columns = ('symbol', 'name', 'market')
        self.tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=20)
        
        self.tree.heading('symbol', text='代码')
        self.tree.heading('name', text='名称')
        self.tree.heading('market', text='市场')
        
        self.tree.column('symbol', width=120, anchor='center')
        self.tree.column('name', width=150, anchor='center')
        self.tree.column('market', width=100, anchor='center')
        
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
    
    def _init_data(self):
        stocks = self.data_manager.get_stock_list()
        self.total_stocks = len(stocks)
        self.all_stocks_data = []
        
        for stock in stocks:
            self.all_stocks_data.append({
                'symbol': stock.get('symbol', ''),
                'name': stock.get('name', ''),
                'market': stock.get('market', '美股')
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
                data['symbol'], data['name'], data['market']
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
                filtered.append({
                    'symbol': stock.get('symbol'),
                    'name': stock.get('name'),
                    'market': stock.get('market', '美股')
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
