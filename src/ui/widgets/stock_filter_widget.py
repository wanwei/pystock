import tkinter as tk
from tkinter import ttk
from typing import List, Dict, Optional, Callable
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from datamgr.stock_filter import StockFilter, FilterCondition


class StockFilterWidget(ttk.Frame):
    """
    股票筛选组件
    
    可复用的股票筛选组件，支持：
    - 按代码/名称搜索
    - 按市场筛选（A股/美股/港股）
    - 按板块筛选（行业/概念）
    - 排除ST股票
    - 价格范围筛选
    - 分页显示结果
    """

    def __init__(
        self, 
        parent, 
        stock_filter: StockFilter,
        on_select: Optional[Callable] = None,
        on_double_click: Optional[Callable] = None,
        **kwargs
    ):
        super().__init__(parent, **kwargs)
        
        self.stock_filter = stock_filter
        self.on_select = on_select
        self.on_double_click = on_double_click
        
        self.current_page = 1
        self.page_size = 100
        self.total_stocks = 0
        self.filtered_stocks: List[Dict] = []
        
        self._sector_data = {'industry': [], 'concept': []}
        
        self._create_widgets()
        self._load_sector_data()
        self._init_data()
    
    def _create_widgets(self):
        filter_frame = ttk.LabelFrame(self, text="筛选条件", padding=10)
        filter_frame.pack(fill=tk.X, padx=5, pady=5)
        
        row1 = ttk.Frame(filter_frame)
        row1.pack(fill=tk.X, pady=2)
        
        ttk.Label(row1, text="搜索:").pack(side=tk.LEFT, padx=(0, 2))
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(row1, textvariable=self.search_var, width=20)
        self.search_entry.pack(side=tk.LEFT, padx=(0, 10))
        self.search_entry.bind('<Return>', lambda e: self._apply_filter())
        
        ttk.Label(row1, text="市场:").pack(side=tk.LEFT, padx=(0, 2))
        self.market_var = tk.StringVar(value='')
        self.market_combo = ttk.Combobox(
            row1, 
            textvariable=self.market_var,
            values=['全部', 'A股', '美股', '港股'],
            width=10,
            state='readonly'
        )
        self.market_combo.pack(side=tk.LEFT, padx=(0, 10))
        self.market_combo.set('全部')
        
        self.exclude_st_var = tk.BooleanVar(value=True)
        self.exclude_st_cb = ttk.Checkbutton(
            row1, 
            text="排除ST", 
            variable=self.exclude_st_var
        )
        self.exclude_st_cb.pack(side=tk.LEFT, padx=(0, 10))
        
        row2 = ttk.Frame(filter_frame)
        row2.pack(fill=tk.X, pady=2)
        
        ttk.Label(row2, text="行业板块:").pack(side=tk.LEFT, padx=(0, 2))
        self.industry_var = tk.StringVar(value='')
        self.industry_combo = ttk.Combobox(
            row2, 
            textvariable=self.industry_var,
            values=['全部'],
            width=15,
            state='readonly'
        )
        self.industry_combo.pack(side=tk.LEFT, padx=(0, 10))
        self.industry_combo.set('全部')
        
        ttk.Label(row2, text="概念板块:").pack(side=tk.LEFT, padx=(0, 2))
        self.concept_var = tk.StringVar(value='')
        self.concept_combo = ttk.Combobox(
            row2, 
            textvariable=self.concept_var,
            values=['全部'],
            width=15,
            state='readonly'
        )
        self.concept_combo.pack(side=tk.LEFT, padx=(0, 10))
        self.concept_combo.set('全部')
        
        row3 = ttk.Frame(filter_frame)
        row3.pack(fill=tk.X, pady=2)
        
        ttk.Label(row3, text="价格范围:").pack(side=tk.LEFT, padx=(0, 2))
        ttk.Label(row3, text="最低").pack(side=tk.LEFT, padx=(2, 2))
        self.min_price_var = tk.StringVar()
        self.min_price_entry = ttk.Entry(row3, textvariable=self.min_price_var, width=8)
        self.min_price_entry.pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Label(row3, text="最高").pack(side=tk.LEFT, padx=(5, 2))
        self.max_price_var = tk.StringVar()
        self.max_price_entry = ttk.Entry(row3, textvariable=self.max_price_var, width=8)
        self.max_price_entry.pack(side=tk.LEFT, padx=(0, 10))
        
        btn_frame = ttk.Frame(filter_frame)
        btn_frame.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Button(btn_frame, text="筛选", command=self._apply_filter, width=10).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="重置", command=self._reset_filter, width=10).pack(side=tk.LEFT, padx=5)
        
        self.result_count_label = ttk.Label(btn_frame, text="", font=('Microsoft YaHei', 10))
        self.result_count_label.pack(side=tk.RIGHT, padx=10)
        
        list_frame = ttk.LabelFrame(self, text="筛选结果", padding=5)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        columns = ('symbol', 'name', 'market', 'price', 'change_pct')
        self.tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=15)
        
        self.tree.heading('symbol', text='代码')
        self.tree.heading('name', text='名称')
        self.tree.heading('market', text='市场')
        self.tree.heading('price', text='价格')
        self.tree.heading('change_pct', text='涨跌幅')
        
        self.tree.column('symbol', width=100, anchor='center')
        self.tree.column('name', width=120, anchor='center')
        self.tree.column('market', width=80, anchor='center')
        self.tree.column('price', width=80, anchor='center')
        self.tree.column('change_pct', width=80, anchor='center')
        
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.tree.bind('<<TreeviewSelect>>', self._on_tree_select)
        self.tree.bind('<Double-1>', self._on_tree_double_click)
        self.tree.bind('<Return>', self._on_tree_double_click)
        
        page_frame = ttk.Frame(self)
        page_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.page_label = ttk.Label(page_frame, text="", font=('Microsoft YaHei', 10))
        self.page_label.pack(side=tk.LEFT, padx=10)
        
        self.prev_btn = ttk.Button(page_frame, text="上一页", command=self.prev_page, width=8)
        self.prev_btn.pack(side=tk.LEFT, padx=5)
        
        self.next_btn = ttk.Button(page_frame, text="下一页", command=self.next_page, width=8)
        self.next_btn.pack(side=tk.LEFT, padx=5)
    
    def _load_sector_data(self):
        industry_sectors = self.stock_filter.get_available_sectors('industry')
        concept_sectors = self.stock_filter.get_available_sectors('concept')
        
        self._sector_data['industry'] = industry_sectors
        self._sector_data['concept'] = concept_sectors
        
        industry_names = ['全部'] + [s.get('name', '') for s in industry_sectors]
        concept_names = ['全部'] + [s.get('name', '') for s in concept_sectors]
        
        self.industry_combo['values'] = industry_names
        self.concept_combo['values'] = concept_names
    
    def _init_data(self):
        condition = FilterCondition()
        self.filtered_stocks = self.stock_filter.filter(condition)
        self.total_stocks = len(self.filtered_stocks)
        self.current_page = 1
        self._update_page_display()
        self._update_page_buttons()
        self._update_result_count()
    
    def _apply_filter(self):
        condition = FilterCondition()
        
        search = self.search_var.get().strip()
        if search:
            condition.search = search
        
        market = self.market_var.get()
        if market and market != '全部':
            condition.markets = [market]
        
        sectors = []
        industry = self.industry_var.get()
        if industry and industry != '全部':
            for s in self._sector_data['industry']:
                if s.get('name') == industry:
                    sectors.append({'type': 'industry', 'code': s.get('code'), 'name': industry})
                    break
        
        concept = self.concept_var.get()
        if concept and concept != '全部':
            for s in self._sector_data['concept']:
                if s.get('name') == concept:
                    sectors.append({'type': 'concept', 'code': s.get('code'), 'name': concept})
                    break
        
        condition.sectors = sectors
        condition.exclude_st = self.exclude_st_var.get()
        
        min_price_str = self.min_price_var.get().strip()
        max_price_str = self.max_price_var.get().strip()
        
        if min_price_str:
            try:
                condition.min_price = float(min_price_str)
            except ValueError:
                pass
        
        if max_price_str:
            try:
                condition.max_price = float(max_price_str)
            except ValueError:
                pass
        
        self.filtered_stocks = self.stock_filter.filter(condition)
        self.total_stocks = len(self.filtered_stocks)
        self.current_page = 1
        self._update_page_display()
        self._update_page_buttons()
        self._update_result_count()
    
    def _reset_filter(self):
        self.search_var.set('')
        self.market_var.set('全部')
        self.industry_var.set('全部')
        self.concept_var.set('全部')
        self.exclude_st_var.set(True)
        self.min_price_var.set('')
        self.max_price_var.set('')
        
        self._init_data()
    
    def _update_result_count(self):
        self.result_count_label.config(text=f"共 {self.total_stocks} 只股票")
    
    def _update_page_display(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        start_idx = (self.current_page - 1) * self.page_size
        end_idx = min(start_idx + self.page_size, self.total_stocks)
        
        for i in range(start_idx, end_idx):
            stock = self.filtered_stocks[i]
            symbol = stock.get('symbol', '')
            name = stock.get('name', '')
            market = stock.get('market', '')
            price = stock.get('price', '')
            change_pct = stock.get('change_pct', '')
            
            if price:
                try:
                    price = f"{float(price):.2f}"
                except (ValueError, TypeError):
                    price = str(price)
            
            if change_pct:
                try:
                    change_pct = f"{float(change_pct):.2f}%"
                except (ValueError, TypeError):
                    change_pct = str(change_pct)
            
            self.tree.insert('', tk.END, values=(symbol, name, market, price, change_pct))
        
        total_pages = max(1, (self.total_stocks + self.page_size - 1) // self.page_size)
        self.page_label.config(text=f"第 {self.current_page}/{total_pages} 页")
    
    def _update_page_buttons(self):
        total_pages = max(1, (self.total_stocks + self.page_size - 1) // self.page_size)
        self.prev_btn.config(state='normal' if self.current_page > 1 else 'disabled')
        self.next_btn.config(state='normal' if self.current_page < total_pages else 'disabled')
    
    def prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self._update_page_display()
            self._update_page_buttons()
    
    def next_page(self):
        total_pages = max(1, (self.total_stocks + self.page_size - 1) // self.page_size)
        if self.current_page < total_pages:
            self.current_page += 1
            self._update_page_display()
            self._update_page_buttons()
    
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
    
    def get_selected_stock(self) -> Optional[Dict]:
        selected = self.tree.selection()
        if not selected:
            return None
        item = self.tree.item(selected[0])
        values = item['values']
        return {
            'symbol': values[0],
            'name': values[1],
            'market': values[2],
            'price': values[3],
            'change_pct': values[4]
        }
    
    def get_filter_condition(self) -> FilterCondition:
        condition = FilterCondition()
        
        search = self.search_var.get().strip()
        if search:
            condition.search = search
        
        market = self.market_var.get()
        if market and market != '全部':
            condition.markets = [market]
        
        sectors = []
        industry = self.industry_var.get()
        if industry and industry != '全部':
            for s in self._sector_data['industry']:
                if s.get('name') == industry:
                    sectors.append({'type': 'industry', 'code': s.get('code'), 'name': industry})
                    break
        
        concept = self.concept_var.get()
        if concept and concept != '全部':
            for s in self._sector_data['concept']:
                if s.get('name') == concept:
                    sectors.append({'type': 'concept', 'code': s.get('code'), 'name': concept})
                    break
        
        condition.sectors = sectors
        condition.exclude_st = self.exclude_st_var.get()
        
        min_price_str = self.min_price_var.get().strip()
        max_price_str = self.max_price_var.get().strip()
        
        if min_price_str:
            try:
                condition.min_price = float(min_price_str)
            except ValueError:
                pass
        
        if max_price_str:
            try:
                condition.max_price = float(max_price_str)
            except ValueError:
                pass
        
        return condition
    
    def refresh(self):
        self.stock_filter.refresh_cache()
        self._load_sector_data()
        self._apply_filter()


if __name__ == "__main__":
    from datamgr.stock_manager import StockDataManager
    from datamgr.sector_manager import SectorManager
    
    root = tk.Tk()
    root.title("股票筛选器测试")
    root.geometry("900x700")
    
    stock_mgr = StockDataManager()
    sector_mgr = SectorManager()
    stock_filter = StockFilter(stock_mgr, sector_mgr)
    
    widget = StockFilterWidget(root, stock_filter)
    widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    root.mainloop()
