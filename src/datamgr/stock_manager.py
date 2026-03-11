import os
from .kline_manager import KLineManager
from .realtime_manager import RealtimeManager
from .sector_manager import SectorManager
from .config_manager import ConfigManager
from .stock_list_manager import StockListManager


class StockDataManager:
    """
    股票数据管理器 - 统一入口
    
    作为所有数据管理器的统一入口，不直接访问 store 层。
    通过组合各个专门的 manager 来提供完整的数据管理功能。
    
    包含的管理器:
    - stock_list: 股票列表管理（基础信息：代码、名称）
    - kline: K线数据管理
    - realtime: 即时数据管理
    - sector: 板块数据管理
    - config: 配置数据管理
    
    目录结构:
    data/
    ├── cn_stock_list.csv    # A股股票列表
    ├── realtime/            # 即时数据目录
    │   ├── CN_600519.csv
    │   └── ...
    ├── kline_data/          # K线数据目录
    │   ├── CN_600519/
    │   │   ├── daily.csv
    │   │   ├── 1hour.csv
    │   │   └── ...
    │   └── ...
    └── sector/              # 板块数据目录
        ├── industry.json
        ├── concept.json
        └── ...
    config/
    └── stocks_config.json
    """
    
    PERIODS = ['1min', '5min', '15min', '1hour', 'daily']
    
    def __init__(self, base_dir=None, config_path=None):
        if base_dir is None:
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            base_dir = os.path.join(project_root, 'data')
        
        if config_path:
            config_dir = os.path.dirname(config_path)
        else:
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            config_dir = os.path.join(project_root, 'config')
        
        self.base_dir = base_dir
        
        self.stock_list = StockListManager(base_dir)
        self.kline = KLineManager(os.path.join(base_dir, 'kline_data'))
        self.realtime = RealtimeManager(os.path.join(base_dir, 'realtime'))
        self.sector = SectorManager(base_dir)
        self.config = ConfigManager(config_dir)
    
    def get_stock_list(self, market='A股'):
        """
        获取股票列表（从股票列表文件获取基础信息）
        
        Args:
            market: 市场 (A股/美股/港股)，默认A股
        
        Returns:
            list: 股票列表，每项包含 code, name, market
        """
        stocks = self.stock_list.get_stock_list(market)
        result = []
        for stock in stocks:
            result.append({
                'symbol': stock.get('code'),
                'name': stock.get('name'),
                'market': market
            })
        return result
    
    def get_all_stocks(self):
        """
        获取所有市场的股票列表
        
        Returns:
            list: 股票列表，每项包含 code, name, market
        """
        all_stocks = []
        for market in self.stock_list.MARKETS:
            if self.stock_list.exists(market):
                stocks = self.get_stock_list(market)
                all_stocks.extend(stocks)
        return all_stocks
    
    def search_stock(self, keyword, market='A股'):
        """
        搜索股票
        
        Args:
            keyword: 搜索关键词（代码或名称）
            market: 市场
        
        Returns:
            list: 匹配的股票列表
        """
        stocks = self.stock_list.search(keyword, market)
        result = []
        for stock in stocks:
            result.append({
                'symbol': stock.get('code'),
                'name': stock.get('name'),
                'market': market
            })
        return result
    
    def get_stock_name(self, code, market='A股'):
        """
        根据代码获取股票名称
        """
        return self.stock_list.get_stock_name(code, market)
    
    def get_stock_info(self, symbol, market):
        """
        获取股票数据概览
        """
        info = {
            'symbol': symbol,
            'market': market,
            'kline': {},
            'realtime': {
                'count': 0,
                'latest': None
            }
        }
        
        name = self.stock_list.get_stock_name(symbol, market)
        if name:
            info['name'] = name
        
        for period in self.PERIODS:
            df = self.kline.get_data(symbol, market, period)
            if df is not None and not df.empty:
                info['kline'][period] = {
                    'count': len(df),
                    'latest': df['date'].max() if 'date' in df.columns else None
                }
        
        realtime_df = self.realtime.get_data(symbol, market)
        if realtime_df is not None and not realtime_df.empty:
            info['realtime']['count'] = len(realtime_df)
            info['realtime']['latest'] = realtime_df['datetime'].max()
        
        return info
    
    def clear_cache(self):
        """
        清空所有内存缓存
        """
        self.stock_list.clear_cache()
        self.kline.clear_cache()
        self.realtime.clear_cache()
        self.sector.clear_cache()
        self.config.clear_cache()
    
    def add_stock(self, symbol, name, market='A股'):
        """
        添加股票到配置
        """
        return self.config.add_stock(symbol, name, market)
    
    def remove_stock(self, symbol, market='A股'):
        """
        从配置中移除股票
        """
        return self.config.remove_stock(symbol, market)
    
    def get_refresh_interval(self):
        """
        获取刷新间隔
        """
        return self.config.get_refresh_interval()
