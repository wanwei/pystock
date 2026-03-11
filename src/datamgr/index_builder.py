import pandas as pd
from .kline_manager import KLineManager


class IndexBuilder:
    """
    指数构建器
    
    功能:
    1. 将多只股票K线合并成指数
    2. 支持不同周期
    3. 支持自定义基准值
    
    算法说明:
    - 找到所有股票的共同交易日
    - 计算每只股票每天的开盘/最高/最低/收盘相对于前一日收盘价的涨跌幅
    - 对所有股票的涨跌幅取算术平均
    - 从基准值开始累计计算指数
    """
    
    DEFAULT_MARKET = 'A股'
    DEFAULT_BASE_VALUE = 100.0
    
    def __init__(self, kline_manager=None):
        if kline_manager is None:
            self.kline_manager = KLineManager()
        else:
            self.kline_manager = kline_manager
    
    def build_index(self, codes, period, base_value=None, market=None):
        """
        构建指数
        
        Args:
            codes: 股票代码列表，如 ['600519', '000858']
            period: 周期，如 'daily', '1hour', '5min' 等
            base_value: 指数基准值，默认100
            market: 市场，默认A股
        
        Returns:
            DataFrame: 指数K线数据，包含 date, open, high, low, close, volume, amount, change_pct 列
        """
        if not codes:
            raise ValueError("股票代码列表不能为空")
        
        if base_value is None:
            base_value = self.DEFAULT_BASE_VALUE
        
        if market is None:
            market = self.DEFAULT_MARKET
        
        kline_data = {}
        for code in codes:
            df = self.kline_manager.get_data(code, market, period)
            if df is not None and not df.empty:
                kline_data[code] = df
        
        if not kline_data:
            raise ValueError("没有找到任何有效的K线数据")
        
        common_dates = self._get_common_dates(kline_data)
        
        if len(common_dates) < 2:
            raise ValueError("共同交易日不足，无法计算涨跌幅")
        
        index_df = self._calculate_index(kline_data, common_dates, base_value)
        
        return index_df
    
    def _get_common_dates(self, kline_data):
        """
        获取所有股票的共同交易日
        
        Args:
            kline_data: {code: DataFrame} 字典
        
        Returns:
            list: 排序后的共同日期列表
        """
        date_sets = []
        for code, df in kline_data.items():
            if 'date' in df.columns:
                dates = set(df['date'].tolist())
                date_sets.append(dates)
        
        if not date_sets:
            return []
        
        common_dates = date_sets[0]
        for date_set in date_sets[1:]:
            common_dates = common_dates.intersection(date_set)
        
        return sorted(list(common_dates))
    
    def _calculate_index(self, kline_data, common_dates, base_value):
        """
        计算指数K线
        
        Args:
            kline_data: {code: DataFrame} 字典
            common_dates: 共同日期列表
            base_value: 基准值
        
        Returns:
            DataFrame: 指数K线数据
        """
        code_dfs = {}
        for code, df in kline_data.items():
            df_indexed = df.set_index('date')
            code_dfs[code] = df_indexed
        
        index_records = []
        prev_close = base_value
        
        for i, date in enumerate(common_dates):
            avg_open_pct = 0.0
            avg_high_pct = 0.0
            avg_low_pct = 0.0
            avg_close_pct = 0.0
            total_volume = 0
            total_amount = 0
            valid_count = 0
            
            for code, df in code_dfs.items():
                if date not in df.index:
                    continue
                
                row = df.loc[date]
                
                curr_open = float(row['open'])
                curr_high = float(row['high'])
                curr_low = float(row['low'])
                curr_close = float(row['close'])
                
                if i == 0:
                    first_open = curr_open
                    first_high = curr_high
                    first_low = curr_low
                    first_close = curr_close
                    
                    open_pct = 0.0
                    high_pct = 0.0
                    low_pct = 0.0
                    close_pct = 0.0
                else:
                    prev_date = common_dates[i - 1]
                    if prev_date not in df.index:
                        continue
                    
                    prev_close_price = float(df.loc[prev_date, 'close'])
                    
                    if prev_close_price == 0:
                        continue
                    
                    open_pct = (curr_open - prev_close_price) / prev_close_price
                    high_pct = (curr_high - prev_close_price) / prev_close_price
                    low_pct = (curr_low - prev_close_price) / prev_close_price
                    close_pct = (curr_close - prev_close_price) / prev_close_price
                
                avg_open_pct += open_pct
                avg_high_pct += high_pct
                avg_low_pct += low_pct
                avg_close_pct += close_pct
                
                if 'volume' in row.index and pd.notna(row['volume']):
                    total_volume += float(row['volume'])
                if 'amount' in row.index and pd.notna(row['amount']):
                    total_amount += float(row['amount'])
                
                valid_count += 1
            
            if valid_count == 0:
                continue
            
            avg_open_pct /= valid_count
            avg_high_pct /= valid_count
            avg_low_pct /= valid_count
            avg_close_pct /= valid_count
            
            if i == 0:
                index_open = base_value
                index_high = base_value
                index_low = base_value
                index_close = base_value
                change_pct = 0.0
            else:
                index_open = prev_close * (1 + avg_open_pct)
                index_high = prev_close * (1 + avg_high_pct)
                index_low = prev_close * (1 + avg_low_pct)
                index_close = prev_close * (1 + avg_close_pct)
                change_pct = avg_close_pct * 100
            
            index_records.append({
                'date': date,
                'open': round(index_open, 2),
                'high': round(index_high, 2),
                'low': round(index_low, 2),
                'close': round(index_close, 2),
                'volume': int(total_volume),
                'amount': round(total_amount, 2),
                'change_pct': round(change_pct, 2)
            })
            
            prev_close = index_close
        
        return pd.DataFrame(index_records)
    
    def build_index_with_weights(self, codes, period, weights=None, base_value=None, market=None):
        """
        构建加权指数
        
        Args:
            codes: 股票代码列表
            period: 周期
            weights: 权重字典，如 {'600519': 0.3, '000858': 0.7}，默认等权
            base_value: 基准值
            market: 市场
        
        Returns:
            DataFrame: 指数K线数据
        """
        if not codes:
            raise ValueError("股票代码列表不能为空")
        
        if base_value is None:
            base_value = self.DEFAULT_BASE_VALUE
        
        if market is None:
            market = self.DEFAULT_MARKET
        
        if weights is None:
            weights = {code: 1.0 / len(codes) for code in codes}
        else:
            total_weight = sum(weights.values())
            weights = {code: w / total_weight for code, w in weights.items()}
        
        kline_data = {}
        for code in codes:
            if code not in weights:
                continue
            df = self.kline_manager.get_data(code, market, period)
            if df is not None and not df.empty:
                kline_data[code] = df
        
        if not kline_data:
            raise ValueError("没有找到任何有效的K线数据")
        
        common_dates = self._get_common_dates(kline_data)
        
        if len(common_dates) < 2:
            raise ValueError("共同交易日不足，无法计算涨跌幅")
        
        index_df = self._calculate_weighted_index(kline_data, common_dates, weights, base_value)
        
        return index_df
    
    def _calculate_weighted_index(self, kline_data, common_dates, weights, base_value):
        """
        计算加权指数K线
        """
        code_dfs = {}
        for code, df in kline_data.items():
            df_indexed = df.set_index('date')
            code_dfs[code] = df_indexed
        
        index_records = []
        prev_close = base_value
        
        for i, date in enumerate(common_dates):
            weighted_open_pct = 0.0
            weighted_high_pct = 0.0
            weighted_low_pct = 0.0
            weighted_close_pct = 0.0
            total_volume = 0
            total_amount = 0
            
            for code, df in code_dfs.items():
                if date not in df.index:
                    continue
                
                row = df.loc[date]
                weight = weights.get(code, 0)
                
                curr_open = float(row['open'])
                curr_high = float(row['high'])
                curr_low = float(row['low'])
                curr_close = float(row['close'])
                
                if i == 0:
                    open_pct = 0.0
                    high_pct = 0.0
                    low_pct = 0.0
                    close_pct = 0.0
                else:
                    prev_date = common_dates[i - 1]
                    if prev_date not in df.index:
                        continue
                    
                    prev_close_price = float(df.loc[prev_date, 'close'])
                    
                    if prev_close_price == 0:
                        continue
                    
                    open_pct = (curr_open - prev_close_price) / prev_close_price
                    high_pct = (curr_high - prev_close_price) / prev_close_price
                    low_pct = (curr_low - prev_close_price) / prev_close_price
                    close_pct = (curr_close - prev_close_price) / prev_close_price
                
                weighted_open_pct += open_pct * weight
                weighted_high_pct += high_pct * weight
                weighted_low_pct += low_pct * weight
                weighted_close_pct += close_pct * weight
                
                if 'volume' in row.index and pd.notna(row['volume']):
                    total_volume += float(row['volume'])
                if 'amount' in row.index and pd.notna(row['amount']):
                    total_amount += float(row['amount'])
            
            if i == 0:
                index_open = base_value
                index_high = base_value
                index_low = base_value
                index_close = base_value
                change_pct = 0.0
            else:
                index_open = prev_close * (1 + weighted_open_pct)
                index_high = prev_close * (1 + weighted_high_pct)
                index_low = prev_close * (1 + weighted_low_pct)
                index_close = prev_close * (1 + weighted_close_pct)
                change_pct = weighted_close_pct * 100
            
            index_records.append({
                'date': date,
                'open': round(index_open, 2),
                'high': round(index_high, 2),
                'low': round(index_low, 2),
                'close': round(index_close, 2),
                'volume': int(total_volume),
                'amount': round(total_amount, 2),
                'change_pct': round(change_pct, 2)
            })
            
            prev_close = index_close
        
        return pd.DataFrame(index_records)
