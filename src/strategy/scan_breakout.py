import sys
import os
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from strategy import scan_today_breakout, StockScanner, HighBreakoutStrategy


def main():
    parser = argparse.ArgumentParser(description='股票突破扫描器')
    parser.add_argument('--data-dir', type=str, default='data/kline_data',
                        help='K线数据目录 (默认: data/kline_data)')
    parser.add_argument('--lookback-start', type=int, default=5,
                        help='回溯起始天数 (默认: 5)')
    parser.add_argument('--lookback-end', type=int, default=50,
                        help='回溯结束天数 (默认: 50)')
    parser.add_argument('--confirm-days', type=int, default=4,
                        help='确认天数 (默认: 4)')
    parser.add_argument('--min-volume', type=int, default=None,
                        help='最小成交量过滤')
    parser.add_argument('--min-price', type=float, default=None,
                        help='最小价格过滤')
    parser.add_argument('--max-price', type=float, default=None,
                        help='最大价格过滤')
    parser.add_argument('--output', type=str, default=None,
                        help='输出文件路径 (CSV格式)')
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("股票突破扫描器")
    print("=" * 70)
    print(f"扫描参数:")
    print(f"  回溯范围: {args.lookback_start}~{args.lookback_end}日前")
    print(f"  确认天数: {args.confirm_days}天")
    print(f"  数据目录: {args.data_dir}")
    print()
    
    filters = {}
    if args.min_volume:
        filters['min_volume'] = args.min_volume
    if args.min_price:
        filters['min_price'] = args.min_price
    if args.max_price:
        filters['max_price'] = args.max_price
    
    if filters:
        print(f"过滤条件:")
        for k, v in filters.items():
            print(f"  {k}: {v}")
        print()
    
    scanner = StockScanner(args.data_dir)
    strategy = HighBreakoutStrategy(
        lookback_start=args.lookback_start,
        lookback_end=args.lookback_end,
        confirm_days=args.confirm_days
    )
    
    results = scanner.scan_latest(strategy, period='daily', filters=filters if filters else None)
    
    print("=" * 70)
    print(f"扫描完成，找到 {len(results)} 只突破股票")
    print("=" * 70)
    print()
    
    if results:
        print(f"{'代码':<10} {'市场':<8} {'日期':<12} {'价格':<10} {'突破幅度':<10} {'阻力位':<10}")
        print("-" * 70)
        
        for r in results:
            metadata = r.get('metadata', {})
            breakout_pct = metadata.get('breakout_pct', 0)
            resistance = metadata.get('resistance_high', 0)
            
            print(f"{r['symbol']:<10} {r['market']:<8} "
                  f"{r['date'].strftime('%Y-%m-%d'):<12} "
                  f"{r['price']:<10.2f} "
                  f"{breakout_pct:<10.2f}% "
                  f"{resistance:<10.2f}")
        
        print()
        print("详细信息:")
        print("-" * 70)
        
        for r in results:
            print(f"\n股票: {r['symbol']} ({r['market']})")
            print(f"  日期: {r['date'].strftime('%Y-%m-%d')}")
            print(f"  价格: {r['price']:.2f}")
            print(f"  原因: {r['reason']}")
            print(f"  置信度: {r['confidence']:.2%}")
            
            metadata = r.get('metadata', {})
            if metadata:
                print(f"  阻力位: {metadata.get('resistance_high', 'N/A')}")
                print(f"  突破幅度: {metadata.get('breakout_pct', 0):.2f}%")
                print(f"  回溯范围: {metadata.get('lookback_range', 'N/A')}")
                print(f"  确认天数: {metadata.get('confirm_days', 'N/A')}")
        
        if args.output:
            import pandas as pd
            df = pd.DataFrame(results)
            df.to_csv(args.output, index=False, encoding='utf-8-sig')
            print(f"\n结果已保存到: {args.output}")
    else:
        print("今日未发现突破股票")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
