import os
import pandas as pd
from .base_store import BaseStore


class StockListStore(BaseStore):
    """
    股票列表存储类
    
    管理股票基础信息列表，如A股全部股票代码和名称
    
    目录结构:
    data/
    ├── cn_stock_list.csv    # A股股票列表
    ├── us_stock_list.csv    # 美股股票列表 (可选)
    └── hk_stock_list.csv    # 港股股票列表 (可选)
    """
    
    COLUMNS = ['code', 'name']
    
    MARKET_FILES = {
        'A股': 'cn_stock_list.csv',
        '美股': 'us_stock_list.csv',
        '港股': 'hk_stock_list.csv'
    }
    
    def __init__(self, base_dir):
        super().__init__(base_dir)
    
    def get_filepath(self, market='A股'):
        filename = self.MARKET_FILES.get(market, 'cn_stock_list.csv')
        return os.path.join(self.base_dir, filename)
    
    def save(self, market, data, **kwargs):
        """
        保存股票列表
        
        Args:
            market: 市场 (A股/美股/港股)
            data: DataFrame 或 list 数据
        
        Returns:
            bool: 是否成功
        """
        with self._lock:
            try:
                if isinstance(data, list):
                    df = pd.DataFrame(data)
                else:
                    df = data.copy()
                
                filepath = self.get_filepath(market)
                df.to_csv(filepath, index=False, encoding='utf-8')
                return True
                
            except Exception as e:
                print(f"保存股票列表失败 {market}: {e}")
                return False
    
    def load(self, market='A股', **kwargs):
        """
        加载股票列表
        
        Args:
            market: 市场 (A股/美股/港股)
        
        Returns:
            DataFrame: 股票列表
        """
        filepath = self.get_filepath(market)
        
        if not os.path.exists(filepath):
            return pd.DataFrame(columns=self.COLUMNS)
        
        try:
            df = pd.read_csv(filepath, dtype={'code': str})
            return df
            
        except Exception as e:
            print(f"加载股票列表失败 {market}: {e}")
            return pd.DataFrame(columns=self.COLUMNS)
    
    def exists(self, market='A股', **kwargs):
        """
        检查股票列表是否存在
        """
        filepath = self.get_filepath(market)
        return os.path.exists(filepath)
    
    def delete(self, market, **kwargs):
        """
        删除股票列表
        """
        with self._lock:
            try:
                filepath = self.get_filepath(market)
                if os.path.exists(filepath):
                    os.remove(filepath)
                return True
            except Exception as e:
                print(f"删除股票列表失败 {market}: {e}")
                return False
    
    def get_count(self, market='A股'):
        """
        获取股票数量
        """
        df = self.load(market)
        return len(df)
    
    def search(self, keyword, market='A股'):
        """
        搜索股票
        
        Args:
            keyword: 搜索关键词（代码或名称）
            market: 市场
        
        Returns:
            DataFrame: 匹配的股票列表
        """
        df = self.load(market)
        if df.empty:
            return df
        
        keyword = str(keyword).lower()
        mask = (
            df['code'].astype(str).str.lower().str.contains(keyword) |
            df['name'].astype(str).str.lower().str.contains(keyword)
        )
        return df[mask]
    
    def get_stock_name(self, code, market='A股'):
        """
        根据代码获取股票名称
        """
        df = self.load(market)
        if df.empty:
            return None
        
        result = df[df['code'].astype(str) == str(code)]
        if not result.empty:
            return result.iloc[0]['name']
        return None
    
    def get_stock_code(self, name, market='A股'):
        """
        根据名称获取股票代码
        """
        df = self.load(market)
        if df.empty:
            return None
        
        result = df[df['name'] == name]
        if not result.empty:
            return result.iloc[0]['code']
        return None
    
    def list_all_markets(self):
        """
        列出所有有数据的市场
        """
        markets = []
        for market in self.MARKET_FILES:
            if self.exists(market):
                markets.append(market)
        return markets
