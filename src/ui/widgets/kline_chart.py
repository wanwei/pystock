import tkinter as tk
from tkinter import ttk
from datetime import datetime


class KLineChartWidget(ttk.Frame):
    """
    K线图组件
    
    可复用的K线图显示组件，支持：
    - 多周期切换
    - 缩放显示
    - 十字光标
    - 键盘导航
    """
    
    PERIODS = {
        '1min': '1分钟',
        '5min': '5分钟',
        '15min': '15分钟',
        '1hour': '1小时',
        'daily': '日线'
    }
    
    def __init__(self, parent, on_period_change=None, on_stock_change=None, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.on_period_change = on_period_change
        self.on_stock_change = on_stock_change
        
        self.current_kline_data = None
        self.current_period = 'daily'
        self.display_count = 120
        self.display_start = 0
        self.crosshair_items = []
        self.signal_items = []
        self.signals = []
        
        self._create_widgets()
    
    def _create_widgets(self):
        toolbar = ttk.Frame(self)
        toolbar.pack(fill=tk.X, pady=5)
        
        ttk.Label(toolbar, text="周期:", font=('Microsoft YaHei', 10)).pack(side=tk.LEFT, padx=5)
        
        self.period_var = tk.StringVar(value=self.current_period)
        for period_key, period_name in self.PERIODS.items():
            rb = ttk.Radiobutton(
                toolbar, text=period_name, value=period_key,
                variable=self.period_var, command=self._on_period_change
            )
            rb.pack(side=tk.LEFT, padx=3)
        
        ttk.Label(toolbar, text="  |  ↑↓键缩放  鼠标移动显示十字线", 
                  font=('Microsoft YaHei', 9), foreground='gray').pack(side=tk.LEFT, padx=10)
        
        self.canvas = tk.Canvas(self, bg='white', highlightthickness=1, highlightbackground='gray')
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        self.canvas.bind('<Configure>', self._on_canvas_resize)
        self.canvas.bind('<Motion>', self._on_mouse_move)
        self.canvas.bind('<Leave>', self._on_mouse_leave)
        
        self.status_label = ttk.Label(self, text="", font=('Microsoft YaHei', 10))
        self.status_label.pack(fill=tk.X, pady=5)
    
    def bind_keys(self, root):
        root.bind('<Up>', self._on_key_up)
        root.bind('<Down>', self._on_key_down)
        root.bind('<Left>', self._on_key_left)
        root.bind('<Right>', self._on_key_right)
        root.bind('<Prior>', self._on_page_up)
        root.bind('<Next>', self._on_page_down)
    
    def unbind_keys(self, root):
        root.unbind('<Up>')
        root.unbind('<Down>')
        root.unbind('<Left>')
        root.unbind('<Right>')
        root.unbind('<Prior>')
        root.unbind('<Next>')
    
    def set_data(self, kline_data, period='daily'):
        self.current_kline_data = kline_data
        self.current_period = period
        self.period_var.set(period)
        
        if kline_data:
            total = len(kline_data)
            self.display_start = max(0, total - self.display_count)
            self._redraw()
        else:
            self._show_error("无法获取K线数据")
    
    def set_signals(self, signals):
        self.signals = signals or []
        self._redraw()
    
    def clear_signals(self):
        self.signals = []
        self._redraw()
    
    def _show_error(self, message):
        self.canvas.delete('all')
        error_label = ttk.Label(self.canvas, text=message, 
                               font=('Microsoft YaHei', 12), foreground='red')
        self.canvas.create_window(400, 250, window=error_label)
        self.status_label.config(text="加载失败")
    
    def _on_period_change(self):
        new_period = self.period_var.get()
        if new_period != self.current_period:
            self.current_period = new_period
            self.display_count = 120
            self.display_start = 0
            if self.on_period_change:
                self.on_period_change(new_period)
    
    def _on_canvas_resize(self, event):
        if self.current_kline_data:
            self.after(100, self._redraw)
    
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
    
    def _redraw(self):
        if not self.current_kline_data or not hasattr(self, 'canvas'):
            return
        
        self.canvas.delete('all')
        self.draw_candlestick(self._get_display_data())
        self._update_status()
    
    def _on_key_up(self, event):
        if self.current_kline_data:
            total = len(self.current_kline_data)
            old_end = min(self.display_start + self.display_count, total)
            self.display_count = max(20, self.display_count - 20)
            self.display_start = max(0, old_end - self.display_count)
            self._redraw()
    
    def _on_key_down(self, event):
        if self.current_kline_data:
            total = len(self.current_kline_data)
            old_end = min(self.display_start + self.display_count, total)
            self.display_count = min(total, self.display_count + 20)
            self.display_start = max(0, old_end - self.display_count)
            self._redraw()
    
    def _on_key_left(self, event):
        if self.current_kline_data:
            if self.display_start > 0:
                self.display_start = max(0, self.display_start - 10)
                self._redraw()
    
    def _on_key_right(self, event):
        if self.current_kline_data:
            total = len(self.current_kline_data)
            if self.display_start + self.display_count < total:
                self.display_start = min(total - self.display_count, self.display_start + 10)
                self._redraw()
    
    def _on_page_up(self, event):
        if self.on_stock_change:
            self.on_stock_change(-1)
    
    def _on_page_down(self, event):
        if self.on_stock_change:
            self.on_stock_change(1)
    
    def _update_status(self):
        if self.current_kline_data:
            total = len(self.current_kline_data)
            end_idx = min(self.display_start + self.display_count, total)
            period_name = self.PERIODS.get(self.current_period, self.current_period)
            self.status_label.config(text=f"{period_name} 显示 {self.display_start+1}-{end_idx}/{total} 根K线")
    
    def _on_mouse_move(self, event):
        if not self.current_kline_data:
            return
        
        self._clear_crosshair()
        
        x, y = event.x, event.y
        
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
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
        
        v_line = self.canvas.create_line(x, margin_top, x, canvas_height - margin_bottom, 
                                         fill='#666666', width=1, dash=(3, 3))
        h_line = self.canvas.create_line(margin_left, y, canvas_width - margin_right, y, 
                                         fill='#666666', width=1, dash=(3, 3))
        self.crosshair_items.extend([v_line, h_line])
        
        prices = []
        for d in display_data:
            prices.extend([d['high'], d['low']])
        min_price = min(prices)
        max_price = max(prices)
        price_range = max_price - min_price if max_price != min_price else 1
        
        price_at_y = max_price - (y - margin_top) / chart_height * price_range
        
        price_text = self.canvas.create_text(canvas_width - margin_right + 5, y, 
                                             text=f"{price_at_y:.2f}", anchor='w', 
                                             font=('Arial', 9), fill='#0066cc')
        self.crosshair_items.append(price_text)
        
        info_text = f"日期:{data['date']} 开:{data['open']:.2f} 高:{data['high']:.2f} 低:{data['low']:.2f} 收:{data['close']:.2f}"
        info_bg = self.canvas.create_rectangle(margin_left, margin_top - 25, 
                                               margin_left + 380, margin_top - 5, 
                                               fill='#ffffcc', outline='#cccc00')
        info_label = self.canvas.create_text(margin_left + 5, margin_top - 15, 
                                             text=info_text, anchor='w', 
                                             font=('Microsoft YaHei', 9), fill='#333333')
        self.crosshair_items.extend([info_bg, info_label])
    
    def _on_mouse_leave(self, event):
        self._clear_crosshair()
    
    def _clear_crosshair(self):
        for item in self.crosshair_items:
            try:
                self.canvas.delete(item)
            except:
                pass
        self.crosshair_items = []
    
    def draw_candlestick(self, kline_data):
        self.canvas.update_idletasks()
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
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
        self.canvas.create_text(canvas_width // 2, 15, text=f"K线图 ({period_name})", 
                               font=('Microsoft YaHei', 12, 'bold'))
        
        for i in range(5):
            y = margin_top + i * chart_height / 4
            price = max_price - (price_range * i / 4)
            self.canvas.create_line(margin_left, y, canvas_width - margin_right, y, 
                                   fill='#e0e0e0', dash=(2, 2))
            self.canvas.create_text(margin_left - 10, y, text=f"{price:.2f}", 
                                   anchor='e', font=('Arial', 9))
        
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
            
            self.canvas.create_line(x, y_high, x, y_low, fill=color, width=1)
            
            body_top = min(y_open, y_close)
            body_height = max(abs(y_close - y_open), 1)
            
            self.canvas.create_rectangle(
                x - candle_width/2, body_top,
                x + candle_width/2, body_top + body_height,
                fill=fill_color, outline=color
            )
            
            if i % max(1, len(kline_data) // 6) == 0:
                date_str = data['date']
                if len(str(date_str)) > 5:
                    date_str = str(date_str)[5:]
                self.canvas.create_text(x, canvas_height - margin_bottom + 15, 
                                       text=date_str, anchor='n', font=('Arial', 8))
        
        self.canvas.create_text(margin_left - 40, margin_top + chart_height / 2, 
                               text="价格", anchor='center', font=('Microsoft YaHei', 10), angle=90)
        self.canvas.create_text(canvas_width // 2, canvas_height - 15, 
                               text="日期", anchor='center', font=('Microsoft YaHei', 10))
        
        self._draw_signals(kline_data, margin_left, margin_top, chart_width, chart_height, 
                          max_price, price_range, candle_gap)
    
    def _draw_signals(self, kline_data, margin_left, margin_top, chart_width, chart_height,
                      max_price, price_range, candle_gap):
        for item in self.signal_items:
            try:
                self.canvas.delete(item)
            except:
                pass
        self.signal_items = []
        
        if not self.signals or not kline_data:
            return
        
        date_to_index = {}
        for i, data in enumerate(kline_data):
            date_str = str(data.get('date', ''))
            date_to_index[date_str] = i
        
        for signal in self.signals:
            signal_time = signal.datetime if hasattr(signal, 'datetime') else signal.get('datetime')
            signal_type = signal.signal_type if hasattr(signal, 'signal_type') else signal.get('signal_type')
            signal_price = signal.price if hasattr(signal, 'price') else signal.get('price', 0)
            
            if signal_time is None:
                continue
            
            date_str = str(signal_time)
            if ' ' in date_str:
                date_str = date_str.split(' ')[0]
            
            if date_str not in date_to_index:
                continue
            
            i = date_to_index[date_str]
            x = margin_left + i * candle_gap + candle_gap / 2
            
            y_signal = margin_top + (max_price - signal_price) / price_range * chart_height
            
            signal_type_str = signal_type.value if hasattr(signal_type, 'value') else str(signal_type)
            
            if 'open_long' in signal_type_str.lower():
                arrow = self.canvas.create_polygon(
                    x - 8, y_signal + 15,
                    x + 8, y_signal + 15,
                    x, y_signal,
                    fill='#ff0000', outline='#cc0000'
                )
                text = self.canvas.create_text(x, y_signal + 25, text="买", 
                                              font=('Microsoft YaHei', 8, 'bold'), fill='#ff0000')
                self.signal_items.extend([arrow, text])
            
            elif 'close_long' in signal_type_str.lower():
                arrow = self.canvas.create_polygon(
                    x - 8, y_signal - 15,
                    x + 8, y_signal - 15,
                    x, y_signal,
                    fill='#00aa00', outline='#008800'
                )
                text = self.canvas.create_text(x, y_signal - 25, text="卖", 
                                              font=('Microsoft YaHei', 8, 'bold'), fill='#00aa00')
                self.signal_items.extend([arrow, text])
