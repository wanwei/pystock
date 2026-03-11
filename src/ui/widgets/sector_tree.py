import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional, Dict, List, Any


class SectorTreeWidget(ttk.Frame):
    """
    股票分类树形组件
    
    以树形结构展示股票分类：
    - 根节点：分类类型（行业板块、概念板块）
    - 子节点：具体板块
    
    支持功能：
    - 展开/折叠
    - 搜索过滤
    - 选择回调
    - 显示板块信息
    """
    
    def __init__(
        self, 
        parent, 
        sector_manager,
        on_select: Optional[Callable[[Dict[str, Any]], None]] = None,
        on_double_click: Optional[Callable[[Dict[str, Any]], None]] = None,
        show_search: bool = True,
        show_statistics: bool = True,
        **kwargs
    ):
        super().__init__(parent, **kwargs)
        
        self.sector_manager = sector_manager
        self.on_select = on_select
        self.on_double_click = on_double_click
        self.show_search = show_search
        self.show_statistics = show_statistics
        
        self._sector_data: Dict[str, List[Dict]] = {}
        self._tree_items: Dict[str, str] = {}
        
        self._create_widgets()
        self._load_data()
    
    def _create_widgets(self):
        if self.show_search:
            search_frame = ttk.Frame(self)
            search_frame.pack(fill=tk.X, pady=(0, 5))
            
            ttk.Label(search_frame, text="搜索:").pack(side=tk.LEFT, padx=(5, 2))
            self.search_var = tk.StringVar()
            self.search_var.trace_add('write', self._on_search_change)
            self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=20)
            self.search_entry.pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)
            
            ttk.Button(search_frame, text="展开全部", command=self._expand_all).pack(side=tk.RIGHT, padx=2)
            ttk.Button(search_frame, text="折叠全部", command=self._collapse_all).pack(side=tk.RIGHT, padx=2)
        
        tree_frame = ttk.Frame(self)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        columns = ('name', 'code', 'count')
        self.tree = ttk.Treeview(tree_frame, columns=columns, show='tree headings', height=15)
        
        self.tree.heading('#0', text='分类')
        self.tree.heading('name', text='名称')
        self.tree.heading('code', text='代码')
        self.tree.heading('count', text='成分股数')
        
        self.tree.column('#0', width=150, minwidth=100)
        self.tree.column('name', width=150, minwidth=80, stretch=True)
        self.tree.column('code', width=100, minwidth=80, anchor='center')
        self.tree.column('count', width=80, minwidth=60, anchor='center')
        
        scrollbar_y = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar_x = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)
        
        self.tree.grid(row=0, column=0, sticky='nsew')
        scrollbar_y.grid(row=0, column=1, sticky='ns')
        scrollbar_x.grid(row=1, column=0, sticky='ew')
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        
        self.tree.bind('<<TreeviewSelect>>', self._on_tree_select)
        self.tree.bind('<Double-1>', self._on_tree_double_click)
        self.tree.bind('<Return>', self._on_tree_double_click)
        
        if self.show_statistics:
            self.stats_frame = ttk.Frame(self)
            self.stats_frame.pack(fill=tk.X, pady=(5, 0))
            self.stats_label = ttk.Label(self.stats_frame, text="", font=('Microsoft YaHei', 9))
            self.stats_label.pack(side=tk.LEFT, padx=5)
    
    def _load_data(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        self._tree_items.clear()
        
        sector_types = self.sector_manager.SECTOR_TYPES
        
        for sector_type, type_name in sector_types.items():
            sectors = self.sector_manager.load_sectors(sector_type)
            self._sector_data[sector_type] = sectors
            
            type_item = self.tree.insert('', tk.END, text=type_name, values=(
                type_name, '', ''
            ), open=False)
            self._tree_items[f"type_{sector_type}"] = type_item
            
            for sector in sectors:
                sector_code = sector.get('code', '')
                sector_name = sector.get('name', '')
                
                stocks_info = self.sector_manager.get_sector_stocks_info(sector_type, sector_code)
                stock_count = stocks_info.get('count', 0) if stocks_info else 0
                
                item_id = self.tree.insert(type_item, tk.END, text='', values=(
                    sector_name, sector_code, stock_count
                ), tags=(sector_type,))
                self._tree_items[f"{sector_type}_{sector_code}"] = item_id
        
        self._update_statistics()
    
    def _update_statistics(self):
        if not self.show_statistics:
            return
        
        total_sectors = 0
        for sector_type in self._sector_data:
            total_sectors += len(self._sector_data.get(sector_type, []))
        
        self.stats_label.config(text=f"共 {len(self.sector_manager.SECTOR_TYPES)} 类分类，{total_sectors} 个板块")
    
    def _on_search_change(self, *args):
        keyword = self.search_var.get().strip().lower()
        
        if not keyword:
            self._restore_all_items()
            return
        
        self._filter_by_keyword(keyword)
    
    def _filter_by_keyword(self, keyword: str):
        for item in self.tree.get_children():
            self.tree.delete(item)
        self._tree_items.clear()
        
        sector_types = self.sector_manager.SECTOR_TYPES
        
        for sector_type, type_name in sector_types.items():
            sectors = self._sector_data.get(sector_type, [])
            matched_sectors = []
            
            for sector in sectors:
                sector_code = sector.get('code', '').lower()
                sector_name = sector.get('name', '').lower()
                
                if keyword in sector_code or keyword in sector_name:
                    matched_sectors.append(sector)
            
            if matched_sectors:
                type_item = self.tree.insert('', tk.END, text=type_name, values=(
                    type_name, '', ''
                ), open=True)
                self._tree_items[f"type_{sector_type}"] = type_item
                
                for sector in matched_sectors:
                    sector_code = sector.get('code', '')
                    sector_name = sector.get('name', '')
                    
                    stocks_info = self.sector_manager.get_sector_stocks_info(sector_type, sector_code)
                    stock_count = stocks_info.get('count', 0) if stocks_info else 0
                    
                    item_id = self.tree.insert(type_item, tk.END, text='', values=(
                        sector_name, sector_code, stock_count
                    ), tags=(sector_type,))
                    self._tree_items[f"{sector_type}_{sector_code}"] = item_id
    
    def _restore_all_items(self):
        self._load_data()
    
    def _expand_all(self):
        for item in self.tree.get_children():
            self._expand_item_recursive(item)
    
    def _expand_item_recursive(self, item):
        self.tree.item(item, open=True)
        for child in self.tree.get_children(item):
            self._expand_item_recursive(child)
    
    def _collapse_all(self):
        for item in self.tree.get_children():
            self.tree.item(item, open=False)
    
    def _on_tree_select(self, event):
        if not self.on_select:
            return
        
        selected = self.tree.selection()
        if not selected:
            return
        
        item_id = selected[0]
        item_data = self._get_item_data(item_id)
        
        if item_data:
            self.on_select(item_data)
    
    def _on_tree_double_click(self, event):
        if not self.on_double_click:
            return
        
        selected = self.tree.selection()
        if not selected:
            return
        
        item_id = selected[0]
        item_data = self._get_item_data(item_id)
        
        if item_data and item_data.get('is_sector'):
            self.on_double_click(item_data)
    
    def _get_item_data(self, item_id: str) -> Optional[Dict[str, Any]]:
        values = self.tree.item(item_id, 'values')
        tags = self.tree.item(item_id, 'tags')
        
        if not values:
            return None
        
        name = values[0] if len(values) > 0 else ''
        code = values[1] if len(values) > 1 else ''
        count = values[2] if len(values) > 2 else ''
        
        is_sector = len(tags) > 0 and tags[0] in self.sector_manager.SECTOR_TYPES
        sector_type = tags[0] if is_sector else None
        
        for st in self.sector_manager.SECTOR_TYPES:
            if item_id == self._tree_items.get(f"type_{st}"):
                return {
                    'is_type': True,
                    'sector_type': st,
                    'name': self.sector_manager.SECTOR_TYPES[st],
                    'code': '',
                    'count': len(self._sector_data.get(st, []))
                }
        
        return {
            'is_sector': is_sector,
            'sector_type': sector_type,
            'name': name,
            'code': code,
            'count': count
        }
    
    def get_selected_sector(self) -> Optional[Dict[str, Any]]:
        selected = self.tree.selection()
        if not selected:
            return None
        
        return self._get_item_data(selected[0])
    
    def refresh(self):
        self._sector_data.clear()
        self._load_data()
    
    def select_sector(self, sector_type: str, sector_code: str):
        item_id = self._tree_items.get(f"{sector_type}_{sector_code}")
        if item_id:
            type_item = self._tree_items.get(f"type_{sector_type}")
            if type_item:
                self.tree.item(type_item, open=True)
            
            self.tree.selection_set(item_id)
            self.tree.see(item_id)
            self.tree.focus(item_id)
    
    def get_sector_stocks(self, sector_type: str, sector_code: str) -> List[Dict]:
        return self.sector_manager.load_sector_stocks(sector_type, sector_code)
