import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import pandas as pd
import os
import json

from datamgr import StockDataManager, KLineManager
from datamgr.stock_filter import StockFilter
from ui.widgets import StockListWidget, KLineChartWidget
from ui.widgets.pattern_scanner_dialog import PatternScannerDialog
from .backtest_config_dialog import BacktestConfigDialog
from .backtest_result_window import BacktestResultWindow
from strategy.backtest import SimpleBacktest, VectorizedBacktest
from strategy.interfaces import StrategyRegistry
from strategy.strategies import (
    MACrossStrategy, MACDStrategy, RSIStrategy, 
    HighBreakoutStrategy, CompositeStrategy
)


STRATEGY_CLASSES = {
    '均线交叉策略': MACrossStrategy,
    'MACD策略': MACDStrategy,
    'RSI策略': RSIStrategy,
    '高点突破策略': HighBreakoutStrategy,
    '组合策略': CompositeStrategy
}


class HistoryAnalysisApp:
    """
    历史分析模块主窗口
    
    功能:
    - 股票列表浏览
    - K线图查看
    - 策略回测
    - 形态扫描
    """
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("股票历史分析系统")
        self.root.geometry("1200x800")
        self.root.minsize(800, 600)
        self.root.state('zoomed')
        
        self.data_manager = StockDataManager()
        self.kline_manager = KLineManager()
        
        self.current_symbol = None
        self.current_name = None
        self.current_market = None
        self.current_stock_index = -1
        
        self._create_menu()
        self._create_main_frame()
    
    def _create_menu(self):
        menubar = tk.Menu(self.root)
        
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="退出", command=self.root.quit)
        menubar.add_cascade(label="文件", menu=file_menu)
        
        data_menu = tk.Menu(menubar, tearoff=0)
        data_menu.add_command(label="更新K线数据", command=self._update_kline_data)
        data_menu.add_command(label="数据状态", command=self._show_data_status)
        menubar.add_cascade(label="数据", menu=data_menu)
        
        strategy_menu = tk.Menu(menubar, tearoff=0)
        strategy_menu.add_command(label="策略回测", command=self._open_backtest)
        strategy_menu.add_command(label="形态扫描", command=self._open_scanner)
        menubar.add_cascade(label="策略", menu=strategy_menu)
        
        self.root.config(menu=menubar)
    
    def _create_main_frame(self):
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        title_label = ttk.Label(self.main_frame, text="股票列表", font=('Microsoft YaHei', 16, 'bold'))
        title_label.pack(pady=(0, 10))
        
        style = ttk.Style()
        style.configure('Custom.TNotebook.Tab', font=('Microsoft YaHei', 12))
        
        self.notebook = ttk.Notebook(self.main_frame, style='Custom.TNotebook')
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        self.all_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.all_tab, text="  全部  ")
        
        self.favorite_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.favorite_tab, text="  自选  ")
        
        self._create_all_tab_content()
        self._create_favorite_tab_content()
    
    def _create_all_tab_content(self):
        self.stock_list = StockListWidget(
            self.all_tab,
            self.data_manager,
            on_double_click=self._on_stock_double_click
        )
        self.stock_list.pack(fill=tk.BOTH, expand=True)
    
    def _create_favorite_tab_content(self):
        # 使用 data/config 作为“自选”配置目录，保持与“配置路径”展示一致
        favorite_config_path = os.path.join(StockDataManager().base_dir, 'config', 'stocks_config.json')
        self.favorite_data_manager = StockDataManager(config_path=favorite_config_path)
        
        config_frame = ttk.Frame(self.favorite_tab)
        config_frame.pack(fill=tk.X, pady=5)
        
        self.config_path_var = tk.StringVar()
        config_dir = os.path.dirname(favorite_config_path)
        self.config_path_var.set(config_dir)
        
        ttk.Label(config_frame, text="配置路径:").pack(side=tk.LEFT, padx=5)
        self.config_path_entry = ttk.Entry(config_frame, textvariable=self.config_path_var, width=50)
        self.config_path_entry.pack(side=tk.LEFT, padx=5)
        ttk.Button(config_frame, text="装载JSON", command=self._load_json_to_favorite).pack(side=tk.LEFT, padx=5)
        
        self.favorite_stock_list = StockListWidget(
            self.favorite_tab,
            self.favorite_data_manager,
            on_double_click=self._on_stock_double_click,
            stocks_source='config'
        )
        self.favorite_stock_list.pack(fill=tk.BOTH, expand=True)
    
    def _load_json_to_favorite(self):
        config_dir = self.config_path_var.get()
        if not os.path.exists(config_dir):
            os.makedirs(config_dir, exist_ok=True)
        
        file_path = filedialog.askopenfilename(
            parent=self.root,
            initialdir=config_dir,
            title="选择JSON文件",
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")]
        )
        
        if file_path:
            def load_thread():
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    json_data = json.loads(content)
                    stocks = json_data.get('stocks', [])
                    
                    if not isinstance(stocks, list) or len(stocks) == 0:
                        self.root.after(0, lambda: messagebox.showwarning("提示", "JSON中没有股票数据", parent=self.root))
                        return
                    
                    def switch_config():
                        # 切换“自选”到用户选择的配置文件
                        self.favorite_data_manager = StockDataManager(config_path=file_path)
                        self.favorite_stock_list.data_manager = self.favorite_data_manager
                        self.favorite_stock_list.refresh()
                        # 更新展示的配置路径
                        self.config_path_var.set(os.path.dirname(file_path))
                        messagebox.showinfo("成功", f"已切换到配置文件: {os.path.basename(file_path)}（{len(stocks)} 只股票）", parent=self.root)
                    
                    self.root.after(0, switch_config)
                    
                except json.JSONDecodeError as e:
                    self.root.after(0, lambda: messagebox.showerror("JSON格式错误", f"JSON解析失败: {e}", parent=self.root))
                except Exception as e:
                    self.root.after(0, lambda: messagebox.showerror("错误", f"读取文件失败: {e}", parent=self.root))
            
            thread = threading.Thread(target=load_thread, daemon=True)
            thread.start()
    
    def _on_stock_double_click(self, stock):
        self.current_symbol = stock['symbol']
        self.current_name = stock['name']
        self.current_market = stock['market']
        
        stocks = self.data_manager.get_stock_list()
        for i, s in enumerate(stocks):
            if s.get('symbol') == self.current_symbol and s.get('market') == self.current_market:
                self.current_stock_index = i
                break
        
        self._show_kline_view()
    
    def _show_kline_view(self):
        for widget in self.main_frame.winfo_children():
            widget.destroy()
        
        self.root.title(f"股票历史分析系统 - {self.current_name} ({self.current_symbol})")
        
        header_frame = ttk.Frame(self.main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.header_label = ttk.Label(header_frame, 
                  text=f"{self.current_name} ({self.current_symbol}) - {self.current_market}",
                  font=('Microsoft YaHei', 16, 'bold'))
        self.header_label.pack(side=tk.LEFT)
        
        btn_frame = ttk.Frame(self.main_frame)
        btn_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(btn_frame, text="返回列表", command=self._return_to_list).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="刷新数据", command=self._refresh_kline).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="回测", command=self._open_backtest).pack(side=tk.LEFT, padx=5)
        
        self.kline_chart = KLineChartWidget(
            self.main_frame,
            on_period_change=self._on_period_change,
            on_stock_change=self._on_stock_change
        )
        self.kline_chart.pack(fill=tk.BOTH, expand=True)
        self.kline_chart.bind_keys(self.root)
        
        self._load_kline_data()
    
    def _return_to_list(self):
        for widget in self.main_frame.winfo_children():
            widget.destroy()
        
        title_label = ttk.Label(self.main_frame, text="股票列表", font=('Microsoft YaHei', 16, 'bold'))
        title_label.pack(pady=(0, 10))
        
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        self.all_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.all_tab, text="全部")
        
        self.favorite_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.favorite_tab, text="收藏")
        
        self._create_all_tab_content()
        self._create_favorite_tab_content()
    
    def _on_stock_change(self, direction):
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
        
        self.root.title(f"股票历史分析系统 - {self.current_name} ({self.current_symbol})")
        
        if hasattr(self, 'header_label'):
            self.header_label.config(text=f"{self.current_name} ({self.current_symbol}) - {self.current_market}")
        
        self._load_kline_data(self.kline_chart.current_period)
    
    def _on_period_change(self, period):
        self._load_kline_data(period)
    
    def _load_kline_data(self, period='daily'):
        self.kline_chart.status_label.config(text="正在加载...")
        
        thread = threading.Thread(
            target=self._fetch_kline_thread,
            args=(period,),
            daemon=True
        )
        thread.start()
    
    def _fetch_kline_thread(self, period):
        kline_data = self._get_stock_kline(self.current_symbol, self.current_market, period)
        self.root.after(0, lambda: self.kline_chart.set_data(kline_data, period))
    
    def _refresh_kline(self):
        self._load_kline_data(self.kline_chart.current_period)
    
    def _get_stock_kline(self, symbol, market, period='daily'):
        try:
            df = self.kline_manager.get_data(symbol, market, period)
            
            if df is None or df.empty:
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
    
    def _update_kline_data(self):
        messagebox.showinfo("提示", "请在命令行运行 update_kline_data.py 更新数据")
    
    def _show_data_status(self):
        stocks = self.kline_manager.list_stocks()
        if stocks:
            print(f"共有 {len(stocks)} 只股票有K线数据")
            for stock in stocks[:10]:
                print(f"  {stock}")
            if len(stocks) > 10:
                print(f"  ... 还有 {len(stocks) - 10} 只")
        else:
            print("暂无K线数据")
    
    def _open_backtest(self):
        if not self.current_symbol:
            messagebox.showwarning("提示", "请先选择一只股票")
            return
        
        current_period = 'daily'
        if hasattr(self, 'kline_chart') and self.kline_chart:
            current_period = self.kline_chart.current_period
        
        dialog = BacktestConfigDialog(
            self.root,
            self.current_symbol,
            self.current_market,
            on_confirm=self._run_backtest,
            current_period=current_period
        )
    
    def _run_backtest(self, config):
        if not config:
            return
        
        progress_window = tk.Toplevel(self.root)
        progress_window.title("回测中")
        progress_window.geometry("300x100")
        progress_window.resizable(False, False)
        progress_window.transient(self.root)
        progress_window.grab_set()
        
        ttk.Label(progress_window, text="正在执行回测，请稍候...", 
                 font=('Microsoft YaHei', 10)).pack(pady=20)
        
        progress = ttk.Progressbar(progress_window, mode='indeterminate')
        progress.pack(fill=tk.X, padx=20, pady=10)
        progress.start()
        
        def run_backtest_thread():
            try:
                result = self._execute_backtest(config)
                
                self.root.after(0, lambda: progress_window.destroy())
                self.root.after(0, lambda: self._show_backtest_result(result, config))
                
            except Exception as e:
                error_msg = str(e)
                self.root.after(0, lambda: progress_window.destroy())
                self.root.after(0, lambda msg=error_msg: messagebox.showerror("回测错误", msg))
        
        thread = threading.Thread(target=run_backtest_thread, daemon=True)
        thread.start()
    
    def _execute_backtest(self, config):
        df = self.kline_manager.get_data(
            config['symbol'], 
            config['market'], 
            config.get('period', 'daily')
        )
        
        if df is None or df.empty:
            raise ValueError("无法获取K线数据")
        
        strategy_name = config['strategy_name']
        strategy_params = config['strategy_params']
        
        strategy_config = StrategyRegistry.get_strategy_by_name(strategy_name)
        if not strategy_config:
            raise ValueError(f"未知策略: {strategy_name}")
        
        strategy_class = strategy_config['class']
        
        if strategy_name == '组合策略':
            sub_strategies = [
                MACrossStrategy(),
                MACDStrategy(),
                RSIStrategy()
            ]
            strategy = CompositeStrategy(
                strategies=sub_strategies,
                min_votes=strategy_params.get('min_votes', 2)
            )
        else:
            strategy = strategy_class(**strategy_params)
        
        initial_capital = config['initial_capital']
        commission_rate = config['commission_rate']
        slippage = config['slippage']
        
        if config['backtest_engine'] == 'vectorized':
            backtest = VectorizedBacktest(
                strategy=strategy,
                initial_capital=initial_capital,
                commission_rate=commission_rate
            )
        else:
            backtest = SimpleBacktest(
                strategy=strategy,
                initial_capital=initial_capital,
                commission_rate=commission_rate,
                slippage=slippage
            )
        
        result = backtest.run(df)
        
        return {
            'statistics': result,
            'equity_curve': backtest.get_equity_curve(),
            'trade_history': backtest.get_trade_history(),
            'signals': strategy.generate_signals(df) if hasattr(strategy, 'generate_signals') else []
        }
    
    def _show_backtest_result(self, result, config):
        BacktestResultWindow(
            self.root,
            result['statistics'],
            result['equity_curve'],
            result['trade_history'],
            result['signals'],
            on_show_signals=self._show_signals_on_kline
        )
    
    def _show_signals_on_kline(self, signals):
        if hasattr(self, 'kline_chart') and self.kline_chart:
            self.kline_chart.set_signals(signals)
    
    def _open_scanner(self):
        stock_filter = StockFilter(self.data_manager, self.data_manager.sector)
        dialog = PatternScannerDialog(
            self.root, 
            stock_filter=stock_filter,
            kline_manager=self.kline_manager,
            on_load_stocks=self._load_scanned_stocks
        )
        dialog.transient(self.root)
        dialog.grab_set()
    
    def _load_scanned_stocks(self, stocks):
        if stocks:
            for stock in stocks:
                self.data_manager.add_stock(
                    stock.get('symbol'),
                    stock.get('name', stock.get('symbol')),
                    stock.get('market', 'A股')
                )
            if hasattr(self, 'stock_list') and self.stock_list:
                self.stock_list.refresh()
            messagebox.showinfo("成功", f"已加载 {len(stocks)} 只股票到配置")
    
    def run(self):
        self.root.mainloop()


def main():
    app = HistoryAnalysisApp()
    app.run()


if __name__ == "__main__":
    main()
