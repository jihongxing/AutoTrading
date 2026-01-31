#!/usr/bin/env python
"""
历史数据下载脚本

用法:
    python scripts/download_data.py --days 30 --symbol BTCUSDT
    python scripts/download_data.py --days 7 --intervals 1m,5m,1h
"""

import argparse
import asyncio
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.downloader import download_historical_data


async def main():
    parser = argparse.ArgumentParser(description="下载 Binance 历史数据")
    parser.add_argument(
        "--symbol",
        default="BTCUSDT",
        help="交易对 (默认: BTCUSDT)",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="下载天数 (默认: 30)",
    )
    parser.add_argument(
        "--intervals",
        default="1m,5m,15m,1h,4h,1d",
        help="K 线周期，逗号分隔 (默认: 1m,5m,15m,1h,4h,1d)",
    )
    parser.add_argument(
        "--questdb-host",
        default="localhost",
        help="QuestDB 主机 (默认: localhost)",
    )
    parser.add_argument(
        "--questdb-port",
        type=int,
        default=9000,
        help="QuestDB 端口 (默认: 9000)",
    )
    
    args = parser.parse_args()
    
    intervals = [i.strip() for i in args.intervals.split(",")]
    
    print(f"开始下载 {args.symbol} 历史数据...")
    print(f"  天数: {args.days}")
    print(f"  周期: {intervals}")
    print(f"  QuestDB: {args.questdb_host}:{args.questdb_port}")
    print()
    
    try:
        results = await download_historical_data(
            symbol=args.symbol,
            days=args.days,
            intervals=intervals,
            questdb_host=args.questdb_host,
            questdb_port=args.questdb_port,
        )
        
        print("\n下载完成:")
        for key, count in results.items():
            print(f"  {key}: {count} 条")
        
        total = sum(results.values())
        print(f"\n总计: {total} 条数据")
        
    except Exception as e:
        print(f"\n下载失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
