import os
import json
import time
import pandas as pd
from datetime import datetime

AKSHARE_AVAILABLE = True
try:
    import akshare as ak
except ImportError:
    AKSHARE_AVAILABLE = False


class StockListDownloader:
    """
    股票列表下载器
    
    功能:
    1. 获取A股所有股票列表
    2. 获取美股所有股票列表
    3. 获取港股所有股票列表
    4. 获取指数成分股
    5. 批量下载所有股票K线数据
    6. 保存股票列表到配置文件
    
    数据源: AkShare
    """
    
    def __init__(self, config_path=None):
        self.config_path = config_path or 'stocks_config.json'
        self.akshare_available = AKSHARE_AVAILABLE
        
        if not self.akshare_available:
            print("警告: akshare 未安装，请先安装: pip install akshare")
    
    def get_cn_stock_list(self):
        """
        获取A股所有股票列表
        
        Returns:
            pandas.DataFrame: 股票列表 (code, name)
        """
        if not self.akshare_available:
            print("AkShare 不可用")
            return None
        
        try:
            print("正在获取A股股票列表...")
            df = ak.stock_info_a_code_name()
            
            if df is None or df.empty:
                print("获取失败: 无数据返回")
                return None
            
            print(f"成功获取 {len(df)} 只A股股票")
            
            return df
            
        except Exception as e:
            print(f"获取A股列表失败: {e}")
            return None
    
    def get_cn_stock_list_em(self):
        """
        获取A股实时行情列表（包含更多字段）
        
        Returns:
            pandas.DataFrame: 股票列表（含行情数据）
        """
        if not self.akshare_available:
            print("AkShare 不可用")
            return None
        
        try:
            print("正在获取A股实时行情列表...")
            df = ak.stock_zh_a_spot_em()
            
            if df is None or df.empty:
                print("获取失败: 无数据返回")
                return None
            
            print(f"成功获取 {len(df)} 只A股股票实时行情")
            
            return df
            
        except Exception as e:
            print(f"获取A股实时行情失败: {e}")
            return None
    
    def get_us_stock_list(self):
        """
        获取美股所有股票列表
        
        Returns:
            pandas.DataFrame: 美股列表
        """
        if not self.akshare_available:
            print("AkShare 不可用")
            return None
        
        try:
            print("正在获取美股股票列表...")
            df = ak.stock_us_spot()
            
            if df is None or df.empty:
                print("获取失败: 无数据返回")
                return None
            
            print(f"成功获取 {len(df)} 只美股股票")
            
            return df
            
        except Exception as e:
            print(f"获取美股列表失败: {e}")
            return None
    
    def get_hk_stock_list(self):
        """
        获取港股主板股票列表
        
        Returns:
            pandas.DataFrame: 港股列表
        """
        if not self.akshare_available:
            print("AkShare 不可用")
            return None
        
        try:
            print("正在获取港股股票列表...")
            df = ak.stock_hk_main_board_spot_em()
            
            if df is None or df.empty:
                print("获取失败: 无数据返回")
                return None
            
            print(f"成功获取 {len(df)} 只港股股票")
            
            return df
            
        except Exception as e:
            print(f"获取港股列表失败: {e}")
            return None
    
    def get_stock_by_index(self, index_type):
        """
        获取指数成分股
        
        Args:
            index_type: 指数类型 ('沪深300', '上证50', '中证500', '创业板50')
        
        Returns:
            pandas.DataFrame: 成分股列表
        """
        if not self.akshare_available:
            print("AkShare 不可用")
            return None
        
        index_code_map = {
            '沪深300': '000300',
            '上证50': '000016',
            '中证500': '000905',
            '创业板50': '399673'
        }
        
        index_code = index_code_map.get(index_type)
        if not index_code:
            print(f"不支持的指数类型: {index_type}")
            print(f"支持的指数: {list(index_code_map.keys())}")
            return None
        
        try:
            print(f"正在获取{index_type}成分股...")
            df = ak.stock_zh_index_component(index_code)
            
            if df is None or df.empty:
                print("获取失败: 无数据返回")
                return None
            
            print(f"成功获取 {len(df)} 只成分股")
            
            return df
            
        except Exception as e:
            print(f"获取{index_type}成分股失败: {e}")
            return None
    
    def download_stock_kline(self, stock_code, start_date="20200101", end_date="20251231", 
                             period="daily", adjust="qfq", save_dir="a_stock_daily_data"):
        """
        下载单只股票的K线数据
        
        Args:
            stock_code: 股票代码
            start_date: 开始日期 (格式: 20200101)
            end_date: 结束日期 (格式: 20251231)
            period: 周期
            adjust: 复权类型 ("qfq" 前复权, "hfq" 后复权, "" 不复权)
            save_dir: 保存目录
        
        Returns:
            pandas.DataFrame: K线数据
        """
        if not self.akshare_available:
            print("AkShare 不可用")
            return None
        
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
        
        try:
            df = ak.stock_zh_a_hist(
                symbol=stock_code,
                period=period,
                start_date=start_date,
                end_date=end_date,
                adjust=adjust
            )
            
            if df is None or df.empty:
                print(f"❌ {stock_code} 无数据返回")
                return None
            
            filepath = os.path.join(save_dir, f"{stock_code}.csv")
            df.to_csv(filepath, index=False, encoding="utf-8-sig")
            print(f"✅ 成功下载 {stock_code} 数据，共 {len(df)} 条")
            
            return df
            
        except Exception as e:
            print(f"❌ 下载 {stock_code} 失败: {str(e)}")
            return None
    
    def download_all_stocks_kline(self, stock_codes=None, start_date="20200101", end_date="20251231",
                                   period="daily", adjust="qfq", save_dir="a_stock_daily_data",
                                   merge_output=True, limit=None, sleep_interval=10):
        """
        批量下载所有股票的K线数据
        
        Args:
            stock_codes: 股票代码列表，如果为None则下载全部A股
            start_date: 开始日期
            end_date: 结束日期
            period: 周期
            adjust: 复权类型
            save_dir: 保存目录
            merge_output: 是否合并为一个文件
            limit: 下载数量限制，None表示不限制
            sleep_interval: 每下载多少只股票暂停一次
        
        Returns:
            dict: 下载结果统计
        """
        if not self.akshare_available:
            print("AkShare 不可用")
            return None
        
        if stock_codes is None:
            stock_list_df = self.get_cn_stock_list()
            if stock_list_df is None:
                return None
            stock_codes = stock_list_df["code"].tolist()
        
        if limit:
            stock_codes = stock_codes[:limit]
        
        print(f"📊 共需下载 {len(stock_codes)} 只股票数据")
        print(f"📁 保存目录: {save_dir}")
        print(f"📅 日期范围: {start_date} ~ {end_date}")
        print()
        
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
        
        success_count = 0
        failed_count = 0
        failed_codes = []
        
        for i, code in enumerate(stock_codes, 1):
            print(f"[{i}/{len(stock_codes)}] ", end="")
            
            result = self.download_stock_kline(
                stock_code=code,
                start_date=start_date,
                end_date=end_date,
                period=period,
                adjust=adjust,
                save_dir=save_dir
            )
            
            if result is not None:
                success_count += 1
            else:
                failed_count += 1
                failed_codes.append(code)
            
            if sleep_interval > 0 and i % sleep_interval == 0:
                print("⏳ 暂停1秒...")
                time.sleep(1)
        
        print()
        print("="*60)
        print("下载完成!")
        print(f"✅ 成功: {success_count} 只")
        print(f"❌ 失败: {failed_count} 只")
        if failed_codes:
            print(f"失败股票: {', '.join(failed_codes[:10])}{'...' if len(failed_codes) > 10 else ''}")
        
        if merge_output and success_count > 0:
            print()
            print("正在合并数据...")
            all_data = []
            for code in stock_codes:
                csv_file = os.path.join(save_dir, f"{code}.csv")
                if os.path.exists(csv_file):
                    df = pd.read_csv(csv_file)
                    df["stock_code"] = code
                    all_data.append(df)
            
            if all_data:
                total_df = pd.concat(all_data, ignore_index=True)
                merge_file = os.path.join(save_dir, "all_a_stock_daily.csv")
                total_df.to_csv(merge_file, index=False, encoding="utf-8-sig")
                print(f"📝 所有数据已合并为 {merge_file}，共 {len(total_df)} 条")
        
        print("="*60)
        
        return {
            'success': success_count,
            'failed': failed_count,
            'failed_codes': failed_codes
        }
    
    def save_to_config(self, stock_list, market='A股', append=True):
        """
        保存股票列表到配置文件
        
        Args:
            stock_list: 股票列表 (DataFrame 或 list)
            market: 市场类型
            append: 是否追加到现有配置
        """
        config = {'stocks': [], 'refresh_interval': 5}
        
        if append and os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            except:
                pass
        
        existing_symbols = {s['symbol'] for s in config.get('stocks', [])}
        new_stocks = []
        
        if isinstance(stock_list, pd.DataFrame):
            code_col = 'code' if 'code' in stock_list.columns else 'symbol'
            name_col = 'name' if 'name' in stock_list.columns else None
            
            for _, row in stock_list.iterrows():
                symbol = str(row[code_col])
                name = str(row[name_col]) if name_col and name_col in row.index else ''
                
                if symbol not in existing_symbols:
                    new_stocks.append({
                        'symbol': symbol,
                        'name': name,
                        'market': market
                    })
                    existing_symbols.add(symbol)
        elif isinstance(stock_list, list):
            for stock in stock_list:
                symbol = stock.get('symbol', stock) if isinstance(stock, dict) else str(stock)
                name = stock.get('name', '') if isinstance(stock, dict) else ''
                
                if symbol not in existing_symbols:
                    new_stocks.append({
                        'symbol': symbol,
                        'name': name,
                        'market': market
                    })
                    existing_symbols.add(symbol)
        
        config['stocks'].extend(new_stocks)
        
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=4)
            print(f"已保存 {len(new_stocks)} 只新股票到配置文件: {self.config_path}")
        except Exception as e:
            print(f"保存配置文件失败: {e}")
    
    def save_to_csv(self, df, filepath):
        """
        保存股票列表到CSV文件
        
        Args:
            df: DataFrame
            filepath: 文件路径
        """
        if df is None or df.empty:
            print("无数据可保存")
            return
        
        try:
            df.to_csv(filepath, index=False, encoding='utf-8-sig')
            print(f"已保存到: {filepath}")
        except Exception as e:
            print(f"保存失败: {e}")
    
    def filter_stocks(self, df, **filters):
        """
        筛选股票
        
        Args:
            df: DataFrame
            filters: 筛选条件
                - code_prefix: 代码前缀 (如 '60' 表示沪市主板)
                - name_contains: 名称包含
                - exclude_st: 排除ST股票
                - exclude_delisting: 排除退市股票
        
        Returns:
            pandas.DataFrame: 筛选后的股票列表
        """
        if df is None or df.empty:
            return df
        
        result = df.copy()
        code_col = 'code' if 'code' in result.columns else 'symbol'
        name_col = 'name' if 'name' in result.columns else None
        
        if filters.get('code_prefix'):
            prefix = filters['code_prefix']
            result = result[result[code_col].str.startswith(prefix)]
        
        if name_col and filters.get('name_contains'):
            keyword = filters['name_contains']
            result = result[result[name_col].str.contains(keyword, na=False)]
        
        if name_col and filters.get('exclude_st'):
            result = result[~result[name_col].str.contains('ST', na=False)]
        
        if name_col and filters.get('exclude_delisting'):
            result = result[~result[name_col].str.contains('退', na=False)]
        
        return result
    
    def show_summary(self):
        """显示各市场股票数量统计"""
        if not self.akshare_available:
            print("AkShare 不可用")
            return
        
        print("\n" + "="*50)
        print("股票市场统计")
        print("="*50)
        
        cn_df = self.get_cn_stock_list()
        if cn_df is not None:
            sh_count = len(cn_df[cn_df['code'].str.startswith('6')])
            sz_count = len(cn_df[cn_df['code'].str.startswith('0')])
            cy_count = len(cn_df[cn_df['code'].str.startswith('3')])
            kc_count = len(cn_df[cn_df['code'].str.startswith('688')])
            bj_count = len(cn_df[cn_df['code'].str.startswith(('4', '8'))])
            
            print(f"\nA股市场: {len(cn_df)} 只")
            print(f"  - 沪市主板 (60): {sh_count} 只")
            print(f"  - 深市主板 (00): {sz_count} 只")
            print(f"  - 创业板 (30): {cy_count} 只")
            print(f"  - 科创板 (688): {kc_count} 只")
            print(f"  - 北交所 (4/8): {bj_count} 只")
        
        us_df = self.get_us_stock_list()
        if us_df is not None:
            print(f"\n美股市场: {len(us_df)} 只")
        
        hk_df = self.get_hk_stock_list()
        if hk_df is not None:
            print(f"\n港股市场: {len(hk_df)} 只")
        
        print("\n" + "="*50)


if __name__ == "__main__":
    downloader = StockListDownloader()
    
    print("="*60)
    print("A股股票列表下载器")
    print("="*60)
    
    if not downloader.akshare_available:
        print("请先安装 akshare: pip install akshare")
        exit(1)
    
    df = downloader.get_cn_stock_list()
    if df is not None:
        print(f"\n前10只股票:")
        print(df.head(10).to_string(index=False))
        
        output_file = 'data/cn_stock_list.csv'
        if not os.path.exists('data'):
            os.makedirs('data')
        downloader.save_to_csv(df, output_file)
        print(f"\n共获取 {len(df)} 只A股股票")
