import tkinter as tk
from tkinter import ttk
from typing import Dict, Any, List, Optional
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import matplotlib
matplotlib.use('TkAgg')
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial']
plt.rcParams['axes.unicode_minus'] = False


class BacktestResultWindow(tk.Toplevel):
    """
    回测结果展示窗口
    
    展示内容包括：
    - 收益曲线图
    - 统计指标
    - 交易记录列表
    """
    
    def __init__(self, parent, backtest_result: Dict[str, Any], 
                 equity_curve=None, trade_history=None, signals=None,
                 on_show_signals=None):
        super().__init__(parent)
        self.title("回测结果")
        self.geometry("1200x800")
        self.minsize(1000, 700)
        
        self._result = backtest_result
        self._equity_curve = equity_curve
        self._trade_history = trade_history or []
        self._signals = signals or []
        self._on_show_signals = on_show_signals
        
        self._create_widgets()
        self._center_window()
    
    def _center_window(self):
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")
    
    def _create_widgets(self):
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        title_label = ttk.Label(header_frame, text="回测结果分析", 
                               font=('Microsoft YaHei', 16, 'bold'))
        title_label.pack(side=tk.LEFT)
        
        if self._signals and self._on_show_signals:
            ttk.Button(header_frame, text="在K线图上显示信号", 
                      command=self._show_signals_on_chart).pack(side=tk.RIGHT, padx=5)
        
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True)
        
        overview_frame = ttk.Frame(notebook, padding=10)
        notebook.add(overview_frame, text="概览")
        
        chart_frame = ttk.Frame(notebook, padding=10)
        notebook.add(chart_frame, text="收益曲线")
        
        trades_frame = ttk.Frame(notebook, padding=10)
        notebook.add(trades_frame, text="交易记录")
        
        self._create_overview_tab(overview_frame)
        self._create_chart_tab(chart_frame)
        self._create_trades_tab(trades_frame)
    
    def _show_signals_on_chart(self):
        if self._on_show_signals:
            self._on_show_signals(self._signals)
            self.destroy()
    
    def _create_overview_tab(self, parent):
        stats_frame = ttk.LabelFrame(parent, text="核心指标", padding=15)
        stats_frame.pack(fill=tk.X, pady=(0, 20))
        
        core_metrics = [
            ('total_return', '总收益率', self._format_percent),
            ('annual_return', '年化收益率', self._format_percent),
            ('max_drawdown', '最大回撤', self._format_percent),
            ('sharpe_ratio', '夏普比率', self._format_float),
            ('win_rate', '胜率', self._format_percent),
            ('profit_factor', '盈亏比', self._format_float),
            ('total_trades', '总交易次数', str),
            ('total_profit', '总盈亏', self._format_money)
        ]
        
        for i, (key, label, formatter) in enumerate(core_metrics):
            row = i // 4
            col = i % 4
            
            frame = ttk.Frame(stats_frame)
            frame.grid(row=row, column=col, padx=20, pady=10, sticky='w')
            
            value = self._result.get(key, 0)
            formatted_value = formatter(value)
            
            ttk.Label(frame, text=label, font=('Microsoft YaHei', 10)).pack(anchor='w')
            
            color = self._get_value_color(key, value)
            value_label = ttk.Label(frame, text=formatted_value, 
                                   font=('Microsoft YaHei', 14, 'bold'), foreground=color)
            value_label.pack(anchor='w')
        
        detail_frame = ttk.LabelFrame(parent, text="详细统计", padding=15)
        detail_frame.pack(fill=tk.BOTH, expand=True)
        
        detail_metrics = [
            ('win_count', '盈利次数', str),
            ('loss_count', '亏损次数', str),
            ('avg_profit', '平均盈亏', self._format_money),
            ('avg_win', '平均盈利', self._format_money),
            ('avg_loss', '平均亏损', self._format_money)
        ]
        
        for i, (key, label, formatter) in enumerate(detail_metrics):
            row = i // 3
            col = i % 3
            
            frame = ttk.Frame(detail_frame)
            frame.grid(row=row, column=col, padx=20, pady=10, sticky='w')
            
            value = self._result.get(key, 0)
            formatted_value = formatter(value)
            
            ttk.Label(frame, text=label, font=('Microsoft YaHei', 10)).pack(anchor='w')
            ttk.Label(frame, text=formatted_value, font=('Microsoft YaHei', 12)).pack(anchor='w')
    
    def _create_chart_tab(self, parent):
        if self._equity_curve is None or len(self._equity_curve) == 0:
            ttk.Label(parent, text="无收益曲线数据", 
                     font=('Microsoft YaHei', 12)).pack(expand=True)
            return
        
        fig = Figure(figsize=(12, 6), dpi=100)
        ax = fig.add_subplot(111)
        
        if hasattr(self._equity_curve, 'columns'):
            if 'datetime' in self._equity_curve.columns:
                x_data = self._equity_curve['datetime']
            else:
                x_data = range(len(self._equity_curve))
            
            if 'equity' in self._equity_curve.columns:
                y_data = self._equity_curve['equity']
            else:
                y_data = self._equity_curve.iloc[:, 0]
        else:
            x_data = range(len(self._equity_curve))
            y_data = self._equity_curve
        
        ax.plot(x_data, y_data, 'b-', linewidth=1.5, label='账户权益')
        
        ax.fill_between(x_data, y_data, alpha=0.3)
        
        ax.set_xlabel('日期', fontsize=10)
        ax.set_ylabel('账户权益', fontsize=10)
        ax.set_title('回测收益曲线', fontsize=12, fontweight='bold')
        ax.legend(loc='upper left')
        ax.grid(True, alpha=0.3)
        
        fig.autofmt_xdate()
        fig.tight_layout()
        
        canvas = FigureCanvasTkAgg(fig, parent)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    
    def _create_trades_tab(self, parent):
        if not self._trade_history:
            ttk.Label(parent, text="无交易记录", 
                     font=('Microsoft YaHei', 12)).pack(expand=True)
            return
        
        columns = ('entry_time', 'exit_time', 'entry_price', 'exit_price', 
                  'profit', 'profit_pct', 'hold_periods')
        
        tree = ttk.Treeview(parent, columns=columns, show='headings', height=20)
        
        headings = {
            'entry_time': '入场时间',
            'exit_time': '出场时间',
            'entry_price': '入场价格',
            'exit_price': '出场价格',
            'profit': '盈亏金额',
            'profit_pct': '盈亏比例',
            'hold_periods': '持仓周期'
        }
        
        widths = {
            'entry_time': 120,
            'exit_time': 120,
            'entry_price': 100,
            'exit_price': 100,
            'profit': 100,
            'profit_pct': 100,
            'hold_periods': 80
        }
        
        for col in columns:
            tree.heading(col, text=headings[col])
            tree.column(col, width=widths[col], anchor='center')
        
        for trade in self._trade_history:
            entry_time = trade.entry_time if hasattr(trade, 'entry_time') else trade.get('entry_time', '')
            exit_time = trade.exit_time if hasattr(trade, 'exit_time') else trade.get('exit_time', '')
            entry_price = trade.entry_price if hasattr(trade, 'entry_price') else trade.get('entry_price', 0)
            exit_price = trade.exit_price if hasattr(trade, 'exit_price') else trade.get('exit_price', 0)
            profit = trade.profit if hasattr(trade, 'profit') else trade.get('profit', 0)
            profit_pct = trade.profit_pct if hasattr(trade, 'profit_pct') else trade.get('profit_pct', 0)
            hold_periods = trade.hold_periods if hasattr(trade, 'hold_periods') else trade.get('hold_periods', 0)
            
            if isinstance(entry_time, datetime):
                entry_time = entry_time.strftime('%Y-%m-%d')
            if isinstance(exit_time, datetime):
                exit_time = exit_time.strftime('%Y-%m-%d')
            
            profit_str = f"{profit:+.2f}"
            profit_pct_str = f"{profit_pct*100:+.2f}%"
            
            tags = ('profit',) if profit > 0 else ('loss',)
            
            tree.insert('', 'end', values=(
                entry_time, exit_time, 
                f"{entry_price:.2f}", f"{exit_price:.2f}",
                profit_str, profit_pct_str, hold_periods
            ), tags=tags)
        
        tree.tag_configure('profit', foreground='red')
        tree.tag_configure('loss', foreground='green')
        
        scrollbar = ttk.Scrollbar(parent, orient='vertical', command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def _format_percent(self, value) -> str:
        if isinstance(value, (int, float)):
            return f"{value * 100:.2f}%"
        return str(value)
    
    def _format_float(self, value) -> str:
        if isinstance(value, (int, float)):
            return f"{value:.4f}"
        return str(value)
    
    def _format_money(self, value) -> str:
        if isinstance(value, (int, float)):
            return f"¥{value:,.2f}"
        return str(value)
    
    def _get_value_color(self, key: str, value) -> str:
        if key in ['total_return', 'annual_return', 'profit_factor', 'win_rate']:
            if isinstance(value, (int, float)):
                if value > 0:
                    return '#cc0000'
                elif value < 0:
                    return '#00aa00'
        elif key == 'max_drawdown':
            if isinstance(value, (int, float)) and value > 0.2:
                return '#cc0000'
        elif key == 'sharpe_ratio':
            if isinstance(value, (int, float)):
                if value > 1:
                    return '#00aa00'
                elif value < 0:
                    return '#cc0000'
        
        return '#333333'
