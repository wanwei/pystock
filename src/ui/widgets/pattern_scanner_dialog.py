import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import os
import sys
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from strategy.scanner import StockScanner
from strategy.interfaces import StrategyRegistry
from strategy.strategies import (
    HighBreakoutStrategy, 
    MACrossStrategy, 
    MACDStrategy, 
    RSIStrategy
)
from datamgr.stock_filter import StockFilter, FilterCondition
from ui.widgets.kline_chart import KLineChartWidget


class PatternScannerDialog(tk.Toplevel):
    """
    形态扫描对话框
    
    功能:
    - 股票范围选择（使用StockFilter）
    - 策略选择和参数配置
    - 扫描执行和进度显示
    - 结果展示和处理
    """
    
    def __init__(self, parent, stock_filter: StockFilter, kline_manager=None,
                 on_load_stocks: Optional[Callable] = None):
        super().__init__(parent)
        
        self.title("形态扫描")
        self.geometry("1100x750")
        self.minsize(900, 600)
        
        self.stock_filter = stock_filter
        self.kline_manager = kline_manager
        self.on_load_stocks = on_load_stocks
        self.scanner = StockScanner(kline_manager=kline_manager)
        
        self.scan_results: List[Dict] = []
        self.is_scanning = False
        self.scan_thread = None
        
        self._param_widgets: Dict[str, tk.Widget] = {}
        self._sector_data = {'industry': [], 'concept': []}
        self.all_stocks: List[Dict] = []
        self.filtered_stocks: List[Dict] = []
        
        self.current_page = 1
        self.page_size = 100
        
        self._create_widgets()
        self._load_sector_data()
        self._load_stock_list()
        self._center_window()
        
        self.protocol("WM_DELETE_WINDOW", self._on_close)
    
    def _center_window(self):
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')
    
    def _create_widgets(self):
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        left_frame = ttk.LabelFrame(main_frame, text="股票范围", padding=5)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=(0, 5))
        
        self._create_stock_filter_panel(left_frame)
        
        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        self._create_strategy_panel(right_frame)
        
        self._create_filter_panel(right_frame)
        
        self._create_results_panel(right_frame)
        
        self._create_bottom_panel()
    
    def _create_stock_filter_panel(self, parent):
        filter_frame = ttk.Frame(parent)
        filter_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(filter_frame, text="搜索:").pack(side=tk.LEFT, padx=(0, 2))
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(filter_frame, textvariable=self.search_var, width=15)
        self.search_entry.pack(side=tk.LEFT, padx=(0, 5))
        self.search_entry.bind('<Return>', lambda e: self._apply_stock_filter())
        
        row2 = ttk.Frame(parent)
        row2.pack(fill=tk.X, pady=2)
        
        ttk.Label(row2, text="市场:").pack(side=tk.LEFT, padx=(0, 2))
        self.market_var = tk.StringVar(value='全部')
        self.market_combo = ttk.Combobox(
            row2, 
            textvariable=self.market_var,
            values=['全部', 'A股', '美股', '港股'],
            width=10,
            state='readonly'
        )
        self.market_combo.pack(side=tk.LEFT, padx=(0, 5))
        
        self.exclude_st_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(row2, text="排除ST", variable=self.exclude_st_var).pack(side=tk.LEFT)
        
        row3 = ttk.Frame(parent)
        row3.pack(fill=tk.X, pady=2)
        
        ttk.Label(row3, text="行业:").pack(side=tk.LEFT, padx=(0, 2))
        self.industry_var = tk.StringVar(value='全部')
        self.industry_combo = ttk.Combobox(
            row3, 
            textvariable=self.industry_var,
            values=['全部'],
            width=12,
            state='readonly'
        )
        self.industry_combo.pack(side=tk.LEFT, padx=(0, 5))
        
        row4 = ttk.Frame(parent)
        row4.pack(fill=tk.X, pady=2)
        
        ttk.Label(row4, text="概念:").pack(side=tk.LEFT, padx=(0, 2))
        self.concept_var = tk.StringVar(value='全部')
        self.concept_combo = ttk.Combobox(
            row4, 
            textvariable=self.concept_var,
            values=['全部'],
            width=12,
            state='readonly'
        )
        self.concept_combo.pack(side=tk.LEFT, padx=(0, 5))
        
        row5 = ttk.Frame(parent)
        row5.pack(fill=tk.X, pady=2)
        
        ttk.Label(row5, text="价格:").pack(side=tk.LEFT, padx=(0, 2))
        self.min_price_var = tk.StringVar()
        ttk.Entry(row5, textvariable=self.min_price_var, width=6).pack(side=tk.LEFT, padx=(0, 2))
        ttk.Label(row5, text="-").pack(side=tk.LEFT)
        self.max_price_var = tk.StringVar()
        ttk.Entry(row5, textvariable=self.max_price_var, width=6).pack(side=tk.LEFT, padx=(0, 5))
        
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(btn_frame, text="应用筛选", command=self._apply_stock_filter, width=10).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="重置", command=self._reset_stock_filter, width=8).pack(side=tk.LEFT, padx=2)
        
        self.stock_count_label = ttk.Label(parent, text="已选择: 0 只股票", font=('Microsoft YaHei', 10))
        self.stock_count_label.pack(pady=5)
        
        list_frame = ttk.LabelFrame(parent, text="股票列表", padding=3)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        columns = ('symbol', 'name', 'market')
        self.stock_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=15)
        
        self.stock_tree.heading('symbol', text='代码')
        self.stock_tree.heading('name', text='名称')
        self.stock_tree.heading('market', text='市场')
        
        self.stock_tree.column('symbol', width=80, anchor='center')
        self.stock_tree.column('name', width=80, anchor='center')
        self.stock_tree.column('market', width=50, anchor='center')
        
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.stock_tree.yview)
        self.stock_tree.configure(yscrollcommand=scrollbar.set)
        
        self.stock_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        page_frame = ttk.Frame(parent)
        page_frame.pack(fill=tk.X, pady=2)
        
        self.page_label = ttk.Label(page_frame, text="", font=('Microsoft YaHei', 9))
        self.page_label.pack(side=tk.LEFT, padx=5)
        
        self.prev_btn = ttk.Button(page_frame, text="上一页", command=self._prev_page, width=8)
        self.prev_btn.pack(side=tk.LEFT, padx=2)
        
        self.next_btn = ttk.Button(page_frame, text="下一页", command=self._next_page, width=8)
        self.next_btn.pack(side=tk.LEFT, padx=2)
    
    def _load_sector_data(self):
        industry_sectors = self.stock_filter.get_available_sectors('industry')
        concept_sectors = self.stock_filter.get_available_sectors('concept')
        
        self._sector_data['industry'] = industry_sectors
        self._sector_data['concept'] = concept_sectors
        
        industry_names = ['全部'] + [s.get('name', '') for s in industry_sectors]
        concept_names = ['全部'] + [s.get('name', '') for s in concept_sectors]
        
        self.industry_combo['values'] = industry_names
        self.concept_combo['values'] = concept_names
    
    def _load_stock_list(self):
        for item in self.stock_tree.get_children():
            self.stock_tree.delete(item)
        
        condition = FilterCondition()
        self.all_stocks = self.stock_filter.filter(condition)
        self.filtered_stocks = self.all_stocks.copy()
        self.current_page = 1
        
        self._update_stock_display()
        self._update_stock_count()
    
    def _update_stock_display(self):
        for item in self.stock_tree.get_children():
            self.stock_tree.delete(item)
        
        start_idx = (self.current_page - 1) * self.page_size
        end_idx = min(start_idx + self.page_size, len(self.filtered_stocks))
        
        for i in range(start_idx, end_idx):
            stock = self.filtered_stocks[i]
            self.stock_tree.insert('', tk.END, values=(
                stock.get('symbol', ''),
                stock.get('name', ''),
                stock.get('market', '')
            ))
        
        self._update_page_label()
        self._update_page_buttons()
    
    def _update_page_label(self):
        total_pages = max(1, (len(self.filtered_stocks) + self.page_size - 1) // self.page_size)
        self.page_label.config(text=f"第 {self.current_page}/{total_pages} 页")
    
    def _update_page_buttons(self):
        total_pages = max(1, (len(self.filtered_stocks) + self.page_size - 1) // self.page_size)
        self.prev_btn.config(state='normal' if self.current_page > 1 else 'disabled')
        self.next_btn.config(state='normal' if self.current_page < total_pages else 'disabled')
    
    def _prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self._update_stock_display()
    
    def _next_page(self):
        total_pages = max(1, (len(self.filtered_stocks) + self.page_size - 1) // self.page_size)
        if self.current_page < total_pages:
            self.current_page += 1
            self._update_stock_display()
    
    def _apply_stock_filter(self):
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
        self.current_page = 1
        self._update_stock_display()
        self._update_stock_count()
    
    def _reset_stock_filter(self):
        self.search_var.set('')
        self.market_var.set('全部')
        self.industry_var.set('全部')
        self.concept_var.set('全部')
        self.exclude_st_var.set(True)
        self.min_price_var.set('')
        self.max_price_var.set('')
        self._load_stock_list()
    
    def _update_stock_count(self):
        total = len(self.filtered_stocks)
        all_total = len(self.all_stocks)
        self.stock_count_label.config(text=f"筛选: {total} 只 (共 {all_total} 只)")
    
    def _create_strategy_panel(self, parent):
        strategy_frame = ttk.LabelFrame(parent, text="策略配置", padding=5)
        strategy_frame.pack(fill=tk.X, pady=5)
        
        select_frame = ttk.Frame(strategy_frame)
        select_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(select_frame, text="选择策略:").pack(side=tk.LEFT, padx=(0, 5))
        
        scanner_strategies = StrategyRegistry.get_scanner_strategies()
        strategy_names = [cfg['name'] for cfg in scanner_strategies.values()]
        self.strategy_var = tk.StringVar(value=strategy_names[0] if strategy_names else '')
        self.strategy_combo = ttk.Combobox(
            select_frame,
            textvariable=self.strategy_var,
            values=strategy_names,
            width=15,
            state='readonly'
        )
        self.strategy_combo.pack(side=tk.LEFT, padx=(0, 10))
        self.strategy_combo.bind('<<ComboboxSelected>>', self._on_strategy_change)
        
        self.strategy_desc_label = ttk.Label(select_frame, text="", foreground='gray')
        self.strategy_desc_label.pack(side=tk.LEFT, padx=5)
        
        self.params_frame = ttk.Frame(strategy_frame)
        self.params_frame.pack(fill=tk.X, pady=5)
        
        self._update_strategy_params()
    
    def _create_filter_panel(self, parent):
        filter_frame = ttk.LabelFrame(parent, text="扫描过滤条件", padding=5)
        filter_frame.pack(fill=tk.X, pady=5)
        
        row1 = ttk.Frame(filter_frame)
        row1.pack(fill=tk.X, pady=2)
        
        ttk.Label(row1, text="最小成交量:").pack(side=tk.LEFT, padx=(0, 2))
        self.min_volume_var = tk.StringVar()
        ttk.Entry(row1, textvariable=self.min_volume_var, width=12).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Label(row1, text="最小成交额:").pack(side=tk.LEFT, padx=(0, 2))
        self.min_turnover_var = tk.StringVar()
        ttk.Entry(row1, textvariable=self.min_turnover_var, width=12).pack(side=tk.LEFT, padx=(0, 10))
        
        row2 = ttk.Frame(filter_frame)
        row2.pack(fill=tk.X, pady=2)
        
        ttk.Label(row2, text="最小数据天数:").pack(side=tk.LEFT, padx=(0, 2))
        self.min_data_days_var = tk.StringVar(value='60')
        ttk.Entry(row2, textvariable=self.min_data_days_var, width=8).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Label(row2, text="最大结果数:").pack(side=tk.LEFT, padx=(0, 2))
        self.max_results_var = tk.StringVar(value='100')
        ttk.Entry(row2, textvariable=self.max_results_var, width=8).pack(side=tk.LEFT, padx=(0, 10))
    
    def _create_results_panel(self, parent):
        results_frame = ttk.LabelFrame(parent, text="扫描结果", padding=5)
        results_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        columns = ('symbol', 'market', 'date', 'price', 'strength', 'reason')
        self.results_tree = ttk.Treeview(results_frame, columns=columns, show='headings', height=10)
        
        self.results_tree.heading('symbol', text='代码')
        self.results_tree.heading('market', text='市场')
        self.results_tree.heading('date', text='日期')
        self.results_tree.heading('price', text='价格')
        self.results_tree.heading('strength', text='强度')
        self.results_tree.heading('reason', text='原因')
        
        self.results_tree.column('symbol', width=80, anchor='center')
        self.results_tree.column('market', width=60, anchor='center')
        self.results_tree.column('date', width=100, anchor='center')
        self.results_tree.column('price', width=80, anchor='center')
        self.results_tree.column('strength', width=60, anchor='center')
        self.results_tree.column('reason', width=300, anchor='w')
        
        scrollbar = ttk.Scrollbar(results_frame, orient=tk.VERTICAL, command=self.results_tree.yview)
        self.results_tree.configure(yscrollcommand=scrollbar.set)
        
        self.results_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.results_tree.bind('<Double-1>', self._on_result_double_click)
    
    def _create_bottom_panel(self):
        bottom_frame = ttk.Frame(self, padding=5)
        bottom_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(bottom_frame, variable=self.progress_var, maximum=100, length=300)
        self.progress_bar.pack(side=tk.LEFT, padx=5)
        
        self.status_label = ttk.Label(bottom_frame, text="就绪", width=40)
        self.status_label.pack(side=tk.LEFT, padx=10)
        
        self.results_count_label = ttk.Label(bottom_frame, text="结果: 0 只")
        self.results_count_label.pack(side=tk.LEFT, padx=10)
        
        btn_frame = ttk.Frame(bottom_frame)
        btn_frame.pack(side=tk.RIGHT, padx=5)
        
        self.scan_btn = ttk.Button(btn_frame, text="开始扫描", command=self._start_scan, width=12)
        self.scan_btn.pack(side=tk.LEFT, padx=3)
        
        self.stop_btn = ttk.Button(btn_frame, text="停止", command=self._stop_scan, width=8, state='disabled')
        self.stop_btn.pack(side=tk.LEFT, padx=3)
        
        ttk.Button(btn_frame, text="导出结果", command=self._export_results, width=10).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_frame, text="加载到列表", command=self._load_to_stock_list, width=10).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_frame, text="关闭", command=self._on_close, width=8).pack(side=tk.LEFT, padx=3)
    
    def _on_strategy_change(self, event=None):
        self._update_strategy_params()
    
    def _update_strategy_params(self):
        for widget in self.params_frame.winfo_children():
            widget.destroy()
        
        self._param_widgets.clear()
        
        strategy_name = self.strategy_var.get()
        strategy_config = StrategyRegistry.get_strategy_by_name(strategy_name)
        
        if not strategy_config:
            return
        
        self.strategy_desc_label.config(text=strategy_config['description'])
        params = strategy_config['params']
        
        row_frame = None
        col = 0
        for param_name, param_config in params.items():
            if col % 3 == 0:
                row_frame = ttk.Frame(self.params_frame)
                row_frame.pack(fill=tk.X, pady=2)
            
            frame = ttk.Frame(row_frame)
            frame.pack(side=tk.LEFT, padx=10)
            
            ttk.Label(frame, text=param_config['label'] + ":").pack(side=tk.LEFT, padx=(0, 2))
            
            if param_config['type'] == 'int':
                var = tk.StringVar(value=str(param_config['default']))
                widget = ttk.Spinbox(
                    frame, 
                    from_=param_config['min'], 
                    to=param_config['max'],
                    textvariable=var,
                    width=8
                )
            else:
                var = tk.StringVar(value=str(param_config['default']))
                widget = ttk.Entry(frame, textvariable=var, width=10)
            
            widget.pack(side=tk.LEFT)
            self._param_widgets[param_name] = (widget, var, param_config)
            
            col += 1
    
    def _get_strategy_instance(self):
        strategy_name = self.strategy_var.get()
        strategy_config = StrategyRegistry.get_strategy_by_name(strategy_name)
        
        if not strategy_config:
            return None
        
        strategy_class = strategy_config['class']
        params = {}
        
        for param_name, (widget, var, config) in self._param_widgets.items():
            value = var.get()
            try:
                if config['type'] == 'int':
                    params[param_name] = int(value)
                else:
                    params[param_name] = float(value)
            except ValueError:
                params[param_name] = config['default']
        
        return strategy_class(**params)
    
    def _get_scan_filters(self) -> Dict[str, Any]:
        filters = {}
        
        try:
            min_volume = int(self.min_volume_var.get()) if self.min_volume_var.get().strip() else None
            if min_volume:
                filters['min_volume'] = min_volume
        except ValueError:
            pass
        
        try:
            min_turnover = float(self.min_turnover_var.get()) if self.min_turnover_var.get().strip() else None
            if min_turnover:
                filters['min_turnover'] = min_turnover
        except ValueError:
            pass
        
        return filters if filters else None
    
    def _start_scan(self):
        if self.is_scanning:
            return
        
        if not self.filtered_stocks:
            messagebox.showwarning("提示", "请先选择要扫描的股票范围")
            return
        
        self.is_scanning = True
        self.scan_btn.config(state='disabled')
        self.stop_btn.config(state='normal')
        
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)
        self.scan_results.clear()
        
        self.progress_var.set(0)
        self.status_label.config(text="正在扫描...")
        self.results_count_label.config(text="结果: 0 只")
        
        self.scan_thread = threading.Thread(target=self._scan_thread, daemon=True)
        self.scan_thread.start()
    
    def _scan_thread(self):
        try:
            strategy = self._get_strategy_instance()
            if not strategy:
                self.after(0, lambda: self.status_label.config(text="请选择策略"))
                return
            
            filters = self._get_scan_filters()
            
            try:
                min_data_days = int(self.min_data_days_var.get()) if self.min_data_days_var.get().strip() else 60
            except ValueError:
                min_data_days = 60
            
            try:
                max_results = int(self.max_results_var.get()) if self.max_results_var.get().strip() else None
            except ValueError:
                max_results = None
            
            def progress_callback(current, total, symbol, results_count):
                progress = current / total * 100
                self.after(0, lambda: self._update_progress(progress, symbol))
            
            self.scan_results = self.scanner.scan_stocks(
                stocks=self.filtered_stocks,
                strategy=strategy,
                min_data_days=min_data_days,
                max_results=max_results,
                show_progress=False,
                filters=filters,
                progress_callback=progress_callback
            )
            
            for result in self.scan_results:
                self.after(0, lambda r=result: self._add_result(r))
            
            self.after(0, self._scan_complete)
            
        except Exception as e:
            self.after(0, lambda: self.status_label.config(text=f"扫描出错: {str(e)}"))
            self.after(0, self._scan_complete)
    
    def _update_progress(self, progress: float, current_symbol: str):
        self.progress_var.set(progress)
        self.status_label.config(text=f"正在扫描: {current_symbol}")
    
    def _add_result(self, result: Dict):
        self.results_tree.insert('', tk.END, values=(
            result['symbol'],
            result['market'],
            result['date'].strftime('%Y-%m-%d') if hasattr(result['date'], 'strftime') else str(result['date']),
            f"{result['price']:.2f}" if isinstance(result['price'], (int, float)) else result['price'],
            result['strength'],
            result['reason']
        ))
        
        count = len(self.results_tree.get_children())
        self.results_count_label.config(text=f"结果: {count} 只")
    
    def _scan_complete(self):
        self.is_scanning = False
        self.scan_btn.config(state='normal')
        self.stop_btn.config(state='disabled')
        
        count = len(self.scan_results)
        self.status_label.config(text=f"扫描完成，找到 {count} 只股票")
        self.progress_var.set(100)
    
    def _stop_scan(self):
        self.is_scanning = False
        self.status_label.config(text="扫描已停止")
    
    def _export_results(self):
        if not self.scan_results:
            messagebox.showinfo("提示", "没有扫描结果可导出")
            return
        
        filename = f"scan_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")],
            initialfile=filename
        )
        
        if not filepath:
            return
        
        import json
        
        export_data = []
        for r in self.scan_results:
            export_data.append({
                'symbol': r['symbol'],
                'name': r.get('name', ''),
                'market': r['market'],
                'date': r['date'].strftime('%Y-%m-%d') if hasattr(r['date'], 'strftime') else str(r['date']),
                'price': r['price'],
                'strength': r['strength'],
                'reason': r['reason'],
                'confidence': r['confidence'],
            })
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump({'stocks': export_data}, f, ensure_ascii=False, indent=2)
        
        messagebox.showinfo("成功", f"结果已导出到:\n{filepath}")
    
    def _load_to_stock_list(self):
        if not self.scan_results:
            messagebox.showinfo("提示", "没有扫描结果可加载")
            return
        
        if self.on_load_stocks:
            stocks = []
            for r in self.scan_results:
                stocks.append({
                    'symbol': r['symbol'],
                    'name': r.get('name', r['symbol']),
                    'market': r['market']
                })
            self.on_load_stocks(stocks)
            messagebox.showinfo("成功", f"已加载 {len(stocks)} 只股票到配置")
        else:
            messagebox.showinfo("提示", "未配置加载回调函数")
    
    def _on_result_double_click(self, event):
        selected = self.results_tree.selection()
        if not selected:
            return
        
        item = self.results_tree.item(selected[0])
        values = item['values']
        
        if len(values) >= 2:
            symbol = str(values[0])
            market = values[1]
            if market == 'A股':
                symbol = symbol.zfill(6)
            self._show_kline_dialog(symbol, market)
    
    def _show_kline_dialog(self, symbol: str, market: str):
        if not self.kline_manager:
            messagebox.showwarning("提示", "K线管理器未配置")
            return
        
        kline_window = tk.Toplevel(self)
        kline_window.title(f"{symbol} K线图")
        kline_window.geometry("1000x600")
        kline_window.minsize(800, 500)
        
        kline_chart = KLineChartWidget(kline_window)
        kline_chart.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        def load_kline_data(period='daily'):
            df = self.kline_manager.get_data(symbol, market, period)
            if df is not None and not df.empty:
                kline_data = df.to_dict('records')
                kline_chart.set_data(kline_data, period)
            else:
                kline_chart.set_data(None)
        
        def on_period_change(new_period):
            load_kline_data(new_period)
        
        kline_chart.on_period_change = on_period_change
        
        kline_chart.bind_keys(kline_window)
        kline_window.protocol("WM_DELETE_WINDOW", lambda: self._close_kline_window(kline_window, kline_chart))
        
        load_kline_data('daily')
        
        kline_window.update_idletasks()
        width = kline_window.winfo_width()
        height = kline_window.winfo_height()
        x = (kline_window.winfo_screenwidth() // 2) - (width // 2)
        y = (kline_window.winfo_screenheight() // 2) - (height // 2)
        kline_window.geometry(f'{width}x{height}+{x}+{y}')
    
    def _close_kline_window(self, window, kline_chart):
        kline_chart.unbind_keys(window)
        window.destroy()
    
    def _on_close(self):
        if self.is_scanning:
            self.is_scanning = False
        self.destroy()


if __name__ == "__main__":
    from datamgr.stock_manager import StockDataManager
    from datamgr.sector_manager import SectorManager
    
    root = tk.Tk()
    root.withdraw()
    
    stock_mgr = StockDataManager()
    sector_mgr = SectorManager()
    stock_filter = StockFilter(stock_mgr, sector_mgr)
    
    dialog = PatternScannerDialog(root, stock_filter)
    dialog.mainloop()
