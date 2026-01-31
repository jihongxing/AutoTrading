"""
快速验证脚本 - 最终版本
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
    从 Binance 下载最近的 K 线数据
    """
    print(f"\n下载 {symbol} {interval} 最近 {limit} 条数据...")
    
    url = "https://api.binance.com/api/v3/klines"
    
    all_data = []
    end_time = int(datetime.now().timestamp() * 1000)
    
    while len(all_data) < limit:
        params = {
            "symbol": symbol,
            "interval": interval,
            "endTime": end_time,
            "limit": 1000
        }
        
        try:
            response = requests.get(url, params=params, timeout=30)
            
            if response.status_code != 200:
                print(f"  API 错误: HTTP {response.status_code}")
                break
            
            data = response.json()
            
            if not data or len(data) == 0:
                break
            
            all_data.extend(data)
            end_time = int(data[0][0]) - 1
            
            if len(all_data) % 5000 == 0:
                print(f"  已下载 {len(all_data)} 条...")
            
            time.sleep(0.1)
            
        except Exception as e:
            print(f"  请求错误: {e}")
            break
    
    if not all_data:
        print("❌ 下载失败")
        return None
    
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
    
    # 低波动区间
    low_vol_threshold = df["vol"].quantile(0.4)
    df["low_vol"] = df["vol"] < low_vol_threshold
    
    # 区间 - 使用前一个周期的区间
    df["range_high"] = df["high"].rolling(window_range).max().shift(1)
    df["range_low"] = df["low"].rolling(window_range).min().shift(1)
    
    # 区间破坏
    df["breakout_up"] = df["close"] > df["range_high"]
    df["breakout_dn"] = df["close"] < df["range_low"]
    
    # 联合事件
    df["event"] = df["low_vol"] & (df["breakout_up"] | df["breakout_dn"])
    df = df.dropna()
    
    event_idx = df.index[df["event"]].tolist()
    
    print(f"低波动样本: {df['low_vol'].sum()}")
    print(f"突破事件: {(df['breakout_up'] | df['breakout_dn']).sum()}")
    print(f"联合事件: {len(event_idx)}")
    
    if len(event_idx) < 20:
        print("⚠️ 联合事件不足，使用纯突破")
        df["event"] = df["breakout_up"] | df["breakout_dn"]
        event_idx = df.index[df["event"]].tolist()
        print(f"纯突破事件: {len(event_idx)}")
        
        if len(event_idx) < 20:
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
    print(f"\n----- 统计结果 -----")
    print(f"样本数: {len(event_ret)}")
    print(f"方向偏移 P(up): {dir_bias:.4f}")
    print(f"方向 p-value: {p_dir:.6f} {'✅' if p_dir < 0.01 else '❌'}")
    print(f"波动率 p-value: {p_vol:.6f} {'✅' if p_vol < 0.05 else '❌'}")
    print(f"Cohen's d: {cohens_d:.4f} {'✅' if abs(cohens_d) > 0.2 else '❌'}")
    print(f"KL Divergence: {kl:.6f} {'✅' if kl > 0.01 else '❌'}")
    
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
    
    return {
        "interval": interval_name,
        "verdict": verdict,
        "n": len(event_ret),
        "p_dir": p_dir,
        "p_vol": p_vol,
        "kl": kl,
        "cohens_d": cohens_d,
        "dir_bias": dir_bias
    }


def main():
    print("=" * 60)
    print("BTC 波动率释放 / 区间破坏 统计验证")
    print("=" * 60)
    
    results = []
    
    # 5m 周期
    df_5m = download_recent_klines(interval="5m", limit=30000)
    if df_5m is not None:
        r = run_validation(df_5m, "5m", window_range=48, future_window=12)
        if r:
            results.append(r)
    
    # 15m 周期
    df_15m = download_recent_klines(interval="15m", limit=10000)
    if df_15m is not None:
        r = run_validation(df_15m, "15m", window_range=16, future_window=4)
        if r:
            results.append(r)
    
    # 综合结论
    print("\n" + "=" * 60)
    print("综合审稿结论")
    print("=" * 60)
    
    if not results:
        print("❌ 无有效结果")
        return
    
    print("\n| 周期 | 样本 | P(up) | p_dir | p_vol | d | KL | 判决 |")
    print("|------|------|-------|-------|-------|---|-----|------|")
    for r in results:
        print(f"| {r['interval']} | {r['n']} | {r['dir_bias']:.3f} | {r['p_dir']:.4f} | {r['p_vol']:.4f} | {r['cohens_d']:.2f} | {r['kl']:.2f} | {r['verdict']} |")
    
    verdicts = [r["verdict"] for r in results]
    
    print("\n" + "=" * 60)
    print("最终判决")
    print("=" * 60)
    
    if all(v == "PASS" for v in verdicts):
        print("""
✅ 综合判决: PASS

假设「波动率释放 + 区间破坏」在 BTC 市场存在统计偏移。

下一步：
1. 冻结 MVP Kernel
2. 进入策略工程
3. 引入仓位和风控
        """)
    elif any(v == "PASS" for v in verdicts):
        print("""
⚠️ 综合判决: CONDITIONAL PASS

假设仅在部分时间尺度有效。

建议：
1. 仅在有效周期上工程化
2. 其他周期降级为研究框架
        """)
    elif any(v == "WEAK" for v in verdicts):
        print("""
⚠️ 综合判决: WEAK

存在弱偏移，但不足以支撑工程化。

建议：
1. 降级为研究框架
2. 考虑替代假设：
   - 强制行为假设（清算密度）
   - 流动性耗尽假设（订单簿坍塌）
   - 定价锚失效假设（资金费率偏离）
        """)
    else:
        print("""
❌ 综合判决: FAIL

无法拒绝随机游走假设。
这不是失败，这是研究完成。

下一步：
1. 停止当前假设的工程化
2. 考虑替代假设路径
3. 或承认：BTC 在该时间尺度是近似有效市场
        """)


if __name__ == "__main__":
    main()
