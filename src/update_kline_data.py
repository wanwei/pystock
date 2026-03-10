import sys
import os
import pandas as pd
from kline_manager import KLineManager

STOCK_LIST_PATH = 'data/cn_stock_list.csv'


def load_all_cn_stocks():
    if not os.path.exists(STOCK_LIST_PATH):
        print(f"错误: 股票列表文件不存在: {STOCK_LIST_PATH}")
        print("请先运行 stock_list_downloader.py 下载股票列表")
        return []
    
    try:
        df = pd.read_csv(STOCK_LIST_PATH, dtype={'code': str})
        stock_list = []
        for _, row in df.iterrows():
            code = str(row['code']).zfill(6)
            stock_list.append({
                'symbol': code,
                'name': str(row['name']),
                'market': 'A股'
            })
        print(f"已从 {STOCK_LIST_PATH} 加载 {len(stock_list)} 只A股股票")
        return stock_list
    except Exception as e:
        print(f"加载股票列表失败: {e}")
        return []


def main():
    print("="*60)
    print("A股K线数据自动更新工具")
    print("="*60)
    print()
    
    manager = KLineManager(data_dir='data/kline_data')
    
    print("正在加载A股股票列表...")
    stock_list = load_all_cn_stocks()
    
    if not stock_list:
        print("错误: 没有找到任何股票")
        return 1
    
    manager.stock_list = stock_list
    
    print(f"共 {len(stock_list)} 只股票需要处理")
    print()
    
    periods = ['1min', '5min', '15min', '1hour', 'daily']
    
    print(f"将下载/更新以下周期数据: {', '.join(periods)}")
    print()
    
    print("开始同步K线数据...")
    print("-"*60)
    
    results = manager.sync_all_stocks(periods=periods)
    
    print()
    print("="*60)
    print("更新完成！")
    print(f"成功: {len(results.get('success', []))} 只")
    print(f"失败: {len(results.get('failed', []))} 只")
    if results.get('failed'):
        print(f"失败股票: {', '.join(results['failed'][:20])}{'...' if len(results['failed']) > 20 else ''}")
    print("="*60)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
