import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, Any, Optional
from strategy.interfaces import StrategyRegistry
from strategy.strategies import (
    MACrossStrategy, MACDStrategy, RSIStrategy, 
    HighBreakoutStrategy, CompositeStrategy
)


class BacktestConfigDialog(tk.Toplevel):
    """
    回测配置对话框
    
    用于配置回测参数，包括：
    - 策略选择
    - 策略参数调整
    - 回测周期
    - 初始资金
    - 手续费率
    """
    
    PERIODS = {
        '1min': '1分钟',
        '5min': '5分钟',
        '15min': '15分钟',
        '1hour': '1小时',
        'daily': '日线'
    }
    
    def __init__(self, parent, symbol: str, market: str, on_confirm=None, current_period: str = 'daily'):
        super().__init__(parent)
        self.title("回测配置")
        self.geometry("500x600")
        self.resizable(False, False)
        
        self.symbol = symbol
        self.market = market
        self.current_period = current_period
        self.on_confirm = on_confirm
        
        self._config = {}
        self._param_vars = {}
        
        self._create_widgets()
        self._center_window()
        
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)
        self.transient(parent)
        self.grab_set()
    
    def _center_window(self):
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")
    
    def _create_widgets(self):
        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        title_label = ttk.Label(main_frame, text="策略回测配置", 
                               font=('Microsoft YaHei', 16, 'bold'))
        title_label.pack(pady=(0, 20))
        
        stock_info = ttk.Label(main_frame, 
                              text=f"股票: {self.symbol} ({self.market})",
                              font=('Microsoft YaHei', 11), foreground='#0066cc')
        stock_info.pack(pady=(0, 20))
        
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        strategy_frame = ttk.Frame(notebook, padding=10)
        notebook.add(strategy_frame, text="策略设置")
        
        basic_frame = ttk.Frame(notebook, padding=10)
        notebook.add(basic_frame, text="基本参数")
        
        self._create_strategy_tab(strategy_frame)
        self._create_basic_tab(basic_frame)
        
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        
        ttk.Button(button_frame, text="开始回测", command=self._on_confirm,
                  width=15).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="取消", command=self._on_cancel,
                  width=10).pack(side=tk.RIGHT, padx=5)
    
    def _create_strategy_tab(self, parent):
        ttk.Label(parent, text="选择策略:", font=('Microsoft YaHei', 10, 'bold')).pack(anchor='w', pady=(0, 10))
        
        backtest_strategies = StrategyRegistry.get_backtest_strategies()
        strategy_names = [cfg['name'] for cfg in backtest_strategies.values()]
        self.strategy_var = tk.StringVar(value=strategy_names[0] if strategy_names else '')
        strategy_combo = ttk.Combobox(parent, textvariable=self.strategy_var,
                                     values=strategy_names,
                                     state='readonly', width=30)
        strategy_combo.pack(fill=tk.X, pady=(0, 20))
        strategy_combo.bind('<<ComboboxSelected>>', self._on_strategy_change)
        
        ttk.Separator(parent, orient='horizontal').pack(fill=tk.X, pady=(0, 15))
        
        ttk.Label(parent, text="策略参数:", font=('Microsoft YaHei', 10, 'bold')).pack(anchor='w', pady=(0, 10))
        
        self.params_frame = ttk.Frame(parent)
        self.params_frame.pack(fill=tk.BOTH, expand=True)
        
        self._create_param_inputs(strategy_names[0] if strategy_names else '')
    
    def _create_basic_tab(self, parent):
        ttk.Label(parent, text="回测周期:", font=('Microsoft YaHei', 10, 'bold')).pack(anchor='w', pady=(0, 10))
        
        period_frame = ttk.Frame(parent)
        period_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.period_var = tk.StringVar(value=self.current_period)
        for period_key, period_name in self.PERIODS.items():
            rb = ttk.Radiobutton(
                period_frame, text=period_name, value=period_key,
                variable=self.period_var
            )
            rb.pack(side=tk.LEFT, padx=8)
        
        ttk.Separator(parent, orient='horizontal').pack(fill=tk.X, pady=15)
        
        ttk.Label(parent, text="回测基本参数", font=('Microsoft YaHei', 10, 'bold')).pack(anchor='w', pady=(0, 20))
        
        params = [
            ('initial_capital', '初始资金', 100000.0, 1000.0, 10000000.0),
            ('commission_rate', '手续费率', 0.0003, 0.0, 0.01),
            ('slippage', '滑点', 0.001, 0.0, 0.05)
        ]
        
        for key, label, default, min_val, max_val in params:
            frame = ttk.Frame(parent)
            frame.pack(fill=tk.X, pady=8)
            
            ttk.Label(frame, text=label, width=15).pack(side=tk.LEFT)
            
            var = tk.DoubleVar(value=default)
            entry = ttk.Entry(frame, textvariable=var, width=20)
            entry.pack(side=tk.LEFT, padx=5)
            
            if key == 'commission_rate':
                ttk.Label(frame, text="(0.03%)").pack(side=tk.LEFT)
            elif key == 'slippage':
                ttk.Label(frame, text="(0.1%)").pack(side=tk.LEFT)
            else:
                ttk.Label(frame, text="(元)").pack(side=tk.LEFT)
            
            self._param_vars[key] = var
        
        ttk.Separator(parent, orient='horizontal').pack(fill=tk.X, pady=20)
        
        ttk.Label(parent, text="回测引擎:", font=('Microsoft YaHei', 10, 'bold')).pack(anchor='w', pady=(0, 10))
        
        self.backtest_engine_var = tk.StringVar(value='simple')
        ttk.Radiobutton(parent, text="简单回测引擎 (逐笔交易)", 
                       value='simple', variable=self.backtest_engine_var).pack(anchor='w', pady=5)
        ttk.Radiobutton(parent, text="向量化回测引擎 (快速)", 
                       value='vectorized', variable=self.backtest_engine_var).pack(anchor='w', pady=5)
    
    def _create_param_inputs(self, strategy_name):
        for widget in self.params_frame.winfo_children():
            widget.destroy()
        
        strategy_config = StrategyRegistry.get_strategy_by_name(strategy_name)
        if not strategy_config:
            return
        
        params = strategy_config.get('params', {})
        
        for param_name, param_info in params.items():
            frame = ttk.Frame(self.params_frame)
            frame.pack(fill=tk.X, pady=8)
            
            ttk.Label(frame, text=param_info['label'], width=15).pack(side=tk.LEFT)
            
            var = tk.DoubleVar(value=param_info['default'])
            entry = ttk.Entry(frame, textvariable=var, width=20)
            entry.pack(side=tk.LEFT, padx=5)
            
            min_val = param_info.get('min', 0)
            max_val = param_info.get('max', 100)
            ttk.Label(frame, text=f"[{min_val}, {max_val}]").pack(side=tk.LEFT)
            
            self._param_vars[param_name] = var
    
    def _on_strategy_change(self, event):
        strategy_name = self.strategy_var.get()
        self._create_param_inputs(strategy_name)
    
    def _on_confirm(self):
        try:
            self._config = self._get_config()
            
            if self.on_confirm:
                self.on_confirm(self._config)
            
            self.destroy()
            
        except ValueError as e:
            messagebox.showerror("参数错误", str(e))
        except Exception as e:
            messagebox.showerror("错误", f"配置失败: {str(e)}")
    
    def _on_cancel(self):
        self._config = {}
        self.destroy()
    
    def _get_config(self) -> Dict[str, Any]:
        config = {
            'symbol': self.symbol,
            'market': self.market,
            'period': self.period_var.get(),
            'strategy_name': self.strategy_var.get(),
            'backtest_engine': self.backtest_engine_var.get(),
            'initial_capital': self._param_vars['initial_capital'].get(),
            'commission_rate': self._param_vars['commission_rate'].get(),
            'slippage': self._param_vars['slippage'].get(),
            'strategy_params': {}
        }
        
        strategy_name = config['strategy_name']
        strategy_config = StrategyRegistry.get_strategy_by_name(strategy_name)
        
        if strategy_config:
            params = strategy_config.get('params', {})
            
            for param_name, param_info in params.items():
                value = self._param_vars[param_name].get()
                min_val = param_info.get('min', 0)
                max_val = param_info.get('max', 100)
                
                if value < min_val or value > max_val:
                    raise ValueError(f"{param_info['label']} 必须在 [{min_val}, {max_val}] 范围内")
                
                if param_info['type'] == 'int':
                    value = int(value)
                
                config['strategy_params'][param_name] = value
        
        return config
    
    def get_config(self) -> Optional[Dict[str, Any]]:
        return self._config
