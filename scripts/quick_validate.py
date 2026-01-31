"""
快速验证脚本 - 使用已下载的数据直接运行统计验证
"""

import pandas as pd
import numpy as np
from scipy import stats
import requests
import time
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')


def download_recent_klines(symbol="BTCUSDT", interval="5m", limit=50000):
    """
    从 Binance 下载最近的 K 线数据（快速版）
    """
    print(f"\n快速下载 {symbol} {interval} 最近 {limit} 条数据...")
    
    url = "https://api.binance.com/api/v3/klines"
    
    all_data = []
    end_time = int(datetime.now().timestamp() * 1000)
    
    # 计算每个周期的毫秒数
    interval_ms = {
        "1m": 60 * 1000,
        "5m": 5 * 60 * 1000,
        "15m": 15 * 60 * 1000,
        "1h": 60 * 60 * 1000
    }
    
    ms_per_candle = interval_ms.get(interval, 5 * 60 * 1000)
    
    while len(all_data) < limit:
        params = {
            "symbol": symbol,
            "interval": interval,
            "endTime": end_time,
            "limit": 1000  # Binance 最大 1000
        }
        
        try:
            response = requests.get(url, params=params, timeout=30)
            
            if response.status_code != 200:
                print(f"  API 错误: HTTP {response.status_code}")
                break
            
            data = response.json()
            
            if not data or len(data) == 0:
                print(f"  无更多数据")
                break
            
            all_data.extend(data)
            
            # 更新 end_time 为最早的时间戳
            end_time = int(data[0][0]) - 1
            
            if len(all_data) % 5000 == 0:
                print(f"  已下载 {len(all_data)} 条...")
            
            time.sleep(0.1)
            
        except Exception as e:
            print(f"  请求错误: {e}")
            break
    
    if not all_data:
        print("❌ 下载失败，无数据")
        return None
    
    # Binance 格式: [open_time, open, high, low, close, volume, close_time, ...]
    df = pd.DataFrame(all_data, columns=[
        "open_time", "open", "high", "low", "close", "volume",
        "close_time", "quote_volume", "trades", "taker_buy_base",
        "taker_buy_quote", "ignore"
    ])
    
    df["timestamp"] = pd.to_datetime(df["open_time"].astype(float), unit="ms")
    df = df[["timestamp", "open", "high", "low", "close", "volume"]]
    
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    df = df.drop_duplicates(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)
    
    print(f"✅ 下载完成: {len(df)} 条")
    print(f"   范围: {df['timestamp'].min()} ~ {df['timestamp'].max()}")
    
    return df


def run_validation(df, interval_name, window_range=48, future_window=12):
    """
    运行波动率释放 + 区间破坏验证
    """
    print(f"\n{'='*60}")
    print(f"验证: {interval_name} | 数据量: {len(df)}")
    print(f"{'='*60}")
    
    df = df.copy()
    df["ret"] = np.log(df["close"]).diff()
    df["vol"] = df["ret"].rolling(window_range).std()
    
    # 低波动区间 (40分位)
    low_vol_threshold = df["vol"].quantile(0.4)
    df["low_vol"] = df["vol"] < low_vol_threshold
    
    print(f"低波动阈值: {low_vol_threshold:.8f}")
    print(f"低波动样本数: {df['low_vol'].sum()}")
    
    # 区间 - 使用前一个周期的区间
    df["range_high"] = df["high"].rolling(window_range).max().shift(1)
    df["range_low"] = df["low"].rolling(window_range).min().shift(1)
    df["range_width"] = df["range_high"] - df["range_low"]
    
    # 区间破坏 - 当前价格突破前一周期的区间
    df["breakout_up"] = df["close"] > df["range_high"]
    df["breakout_dn"] = df["close"] < df["range_low"]
    
    print(f"向上突破数: {df['breakout_up'].sum()}")
    print(f"向下突破数: {df['breakout_dn'].sum()}")
    
    # 联合事件
    df["event"] = df["low_vol"] & (df["breakout_up"] | df["breakout_dn"])
    df = df.dropna()
    
    event_idx = df.index[df["event"]].tolist()
    print(f"检测到联合事件: {len(event_idx)}")
    
    if len(event_idx) < 20:
        print("⚠️ 联合事件不足，尝试仅使用突破事件")
        # 如果联合事件不足，尝试仅使用突破
        df["event"] = df["breakout_up"] | df["breakout_dn"]
        event_idx = df.index[df["event"]].tolist()
        print(f"仅突破事件数: {len(event_idx)}")
        
        if len(event_idx) < 20:
            print("⚠️ 事件仍然不足")
            return None
    
    # 事件后统计
    def get_future(indexes):
        rets, vols = [], []
        for i in indexes:
            try:
                pos = df.index.get_loc(i)
                if pos + future_window >= len(df):
                    continue
                fwd = df.iloc[pos+1:pos+future_window+1]
                rets.append(fwd["ret"].sum())
                vols.append(fwd["ret"].std())
            except:
                continue
        return np.array(rets), np.array(vols)
    
    event_ret, event_vol = get_future(event_idx)
    
    if len(event_ret) < 20:
        print("⚠️ 有效样本不足")
        return None
    
    # 随机对照
    valid_idx = df.index[window_range:-future_window].tolist()
    rand_rets, rand_vols = [], []
    
    for _ in range(300):
        sample = np.random.choice(valid_idx, size=min(len(event_idx), len(valid_idx)), replace=False)
        r, v = get_future(sample)
        if len(r) > 0:
            rand_rets.append(np.mean(r))
            rand_vols.append(np.mean(v))
    
    rand_rets = np.array(rand_rets)
    rand_vols = np.array(rand_vols)
    
    # 统计检验
    n_up = np.sum(event_ret > 0)
    n_total = len(event_ret)
    dir_bias = n_up / n_total
    
    try:
        from scipy.stats import binomtest
        p_dir = binomtest(n_up, n_total, 0.5).pvalue
    except:
        p_dir = stats.binom_test(n_up, n_total, 0.5)
    
    baseline = np.mean(rand_vols) if len(rand_vols) > 0 else df["ret"].std()
    vol_diff = np.mean(event_vol) - baseline
    _, p_vol = stats.ttest_1samp(event_vol, baseline)
    
    # KL
    if len(rand_rets) > 0:
        all_r = np.concatenate([event_ret, rand_rets])
        bins = np.linspace(np.percentile(all_r, 1), np.percentile(all_r, 99), 21)
        h1, _ = np.histogram(event_ret, bins=bins, density=True)
        h2, _ = np.histogram(rand_rets, bins=bins, density=True)
        kl = stats.entropy(h1 + 1e-10, h2 + 1e-10)
    else:
        kl = 0
    
    cohens_d = vol_diff / np.std(event_vol) if np.std(event_vol) > 0 else 0
    
    # 输出
    print(f"\n----- 结果 -----")
    print(f"样本数: {len(event_ret)}")
    print(f"P(up): {dir_bias:.4f}")
    print(f"p_dir: {p_dir:.6f} {'✅' if p_dir < 0.01 else '❌'}")
    print(f"p_vol: {p_vol:.6f} {'✅' if p_vol < 0.05 else '❌'}")
    print(f"Cohen d: {cohens_d:.4f} {'✅' if abs(cohens_d) > 0.2 else '❌'}")
    print(f"KL: {kl:.6f} {'✅' if kl > 0.01 else '❌'}")
    
    # 判决
    pass_dir = p_dir < 0.01
    pass_vol = p_vol < 0.05
    pass_kl = kl > 0.01
    
    if pass_dir and (pass_vol or pass_kl):
        verdict = "PASS"
    elif sum([pass_dir, pass_vol, pass_kl]) >= 2:
        verdict = "WEAK"
    else:
        verdict = "FAIL"
    
    print(f"\n===== {interval_name} 判决: {verdict} =====")
    
    return {"interval": interval_name, "verdict": verdict, "p_dir": p_dir, "p_vol": p_vol, "kl": kl, "n": len(event_ret)}


def main():
    print("=" * 60)
    print("BTC 波动率释放 / 区间破坏 快速验证")
    print("=" * 60)
    
    results = []
    
    # 5m - 减少数据量加快速度
    df_5m = download_recent_klines(interval="5m", limit=30000)
    if df_5m is not None:
        r = run_validation(df_5m, "5m", window_range=48, future_window=12)
        if r: results.append(r)
    
    # 15m - 减少数据量
    df_15m = download_recent_klines(interval="15m", limit=10000)
    if df_15m is not None:
        r = run_validation(df_15m, "15m", window_range=16, future_window=4)
        if r: results.append(r)
    
    # 综合
    print("\n" + "=" * 60)
    print("综合审稿结论")
    print("=" * 60)
    
    if not results:
        print("❌ 无结果")
        return
    
    print("\n| 周期 | 样本 | p_dir | p_vol | KL | 判决 |")
    print("|------|------|-------|-------|-----|------|")
    for r in results:
        print(f"| {r['interval']} | {r['n']} | {r['p_dir']:.4f} | {r['p_vol']:.4f} | {r['kl']:.4f} | {r['verdict']} |")
    
    verdicts = [r["verdict"] for r in results]
    
    print("\n" + "=" * 60)
    if all(v == "PASS" for v in verdicts):
        print("✅ 综合: PASS - 可进入策略工程")
    elif any(v == "PASS" for v in verdicts):
        print("⚠️ 综合: CONDITIONAL - 部分周期有效")
    elif any(v == "WEAK" for v in verdicts):
        print("⚠️ 综合: WEAK - 弱偏移，不建议工程化")
    else:
        print("❌ 综合: FAIL - 无法拒绝随机游走")
        print("   → 考虑替代假设或放弃")


if __name__ == "__main__":
    main()
