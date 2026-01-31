"""
自动下载 Binance BTC K线数据并运行统计验证

一键完成：
1. 从 Binance API 下载 5m / 15m 历史数据
2. 运行波动率释放 + 区间破坏验证
3. 输出审稿级结论
"""

import os
import pandas as pd
import numpy as np
from scipy import stats
from datetime import datetime, timedelta
import requests
import time
import warnings
warnings.filterwarnings('ignore')


# =========================
# 1. 数据下载
# =========================
def download_klines(symbol="BTC-USDT", interval="5m", 
                    start_date="2022-01-01", end_date="2025-01-01"):
    """
    从 OKX API 下载历史 K 线数据（无地区限制）
    """
    print(f"\n下载 {symbol} {interval} 数据...")
    print(f"时间范围: {start_date} ~ {end_date}")
    
    # OKX interval 映射
    interval_map = {"5m": "5m", "15m": "15m", "1h": "1H", "4h": "4H", "1d": "1D"}
    okx_interval = interval_map.get(interval, interval)
    
    url = "https://www.okx.com/api/v5/market/candles"
    end_ts = int(datetime.strptime(end_date, "%Y-%m-%d").timestamp() * 1000)
    start_ts = int(datetime.strptime(start_date, "%Y-%m-%d").timestamp() * 1000)
    
    all_data = []
    request_count = 0
    current_ts = end_ts  # OKX 从后往前拉
    
    while current_ts > start_ts:
        params = {
            "instId": symbol,
            "bar": okx_interval,
            "before": str(current_ts),
            "limit": "300"
        }
        
        try:
            response = requests.get(url, params=params, timeout=30)
            result = response.json()
            
            if result.get("code") != "0" or not result.get("data"):
                print(f"API 返回: {result.get('msg', 'No data')}")
                break
            
            data = result["data"]
            all_data.extend(data)
            
            # OKX 返回的是倒序，最后一条是最早的
            current_ts = int(data[-1][0]) - 1
            request_count += 1
            
            if request_count % 20 == 0:
                current_date = datetime.fromtimestamp(current_ts/1000).strftime("%Y-%m-%d")
                print(f"  已下载至 {current_date}, 共 {len(all_data)} 条")
            
            time.sleep(0.1)
            
        except Exception as e:
            print(f"下载出错: {e}")
            time.sleep(1)
            continue
    
    if not all_data:
        print("❌ 下载失败，无数据")
        return None
    
    # OKX 格式: [ts, o, h, l, c, vol, volCcy, volCcyQuote, confirm]
    df = pd.DataFrame(all_data, columns=[
        "open_time", "open", "high", "low", "close", "volume",
        "vol_ccy", "vol_ccy_quote", "confirm"
    ])
    
    df["timestamp"] = pd.to_datetime(df["open_time"].astype(float), unit="ms")
    df = df[["timestamp", "open", "high", "low", "close", "volume"]]
    
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    df = df.drop_duplicates(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)
    
    print(f"✅ 下载完成: {len(df)} 条数据")
    print(f"   时间范围: {df['timestamp'].min()} ~ {df['timestamp'].max()}")
    
    return df


# =========================
# 2. 验证核心逻辑
# =========================
def run_validation(df, interval_name, window_range=48, future_window=12, 
                   low_vol_percentile=0.2, breakout_k=1.2, n_random=500):
    """
    运行波动率释放 + 区间破坏验证
    """
    print(f"\n{'='*60}")
    print(f"验证周期: {interval_name}")
    print(f"参数: window={window_range}, future={future_window}")
    print(f"{'='*60}")
    
    df = df.copy()
    df["ret"] = np.log(df["close"]).diff()
    df["vol"] = df["ret"].rolling(window_range).std()
    
    # 低波动区间
    low_vol_threshold = df["vol"].quantile(low_vol_percentile)
    df["low_vol"] = df["vol"] < low_vol_threshold
    
    # 区间高低
    df["range_high"] = df["high"].rolling(window_range).max()
    df["range_low"] = df["low"].rolling(window_range).min()
    df["range_width"] = df["range_high"] - df["range_low"]
    
    # 区间破坏
    range_std = df["range_width"].rolling(window_range).std()
    df["breakout_up"] = df["close"] > df["range_high"] + breakout_k * range_std
    df["breakout_dn"] = df["close"] < df["range_low"] - breakout_k * range_std
    
    # 联合事件
    df["event"] = df["low_vol"] & (df["breakout_up"] | df["breakout_dn"])
    df = df.dropna()
    
    event_idx = df.index[df["event"]].tolist()
    print(f"检测到事件数: {len(event_idx)}")
    
    if len(event_idx) < 30:
        print("⚠️ 事件数量不足")
        return None
    
    # 事件后统计
    def future_stats(indexes):
        future_ret = []
        future_vol = []
        for i in indexes:
            try:
                pos = df.index.get_loc(i)
                if pos + future_window >= len(df):
                    continue
                fwd = df.iloc[pos+1:pos+future_window+1]
                future_ret.append(fwd["ret"].sum())
                future_vol.append(fwd["ret"].std())
            except:
                continue
        return np.array(future_ret), np.array(future_vol)
    
    event_ret, event_vol = future_stats(event_idx)
    
    if len(event_ret) < 30:
        print("⚠️ 有效样本不足")
        return None
    
    # 随机对照组
    valid_idx = df.index[window_range:-future_window].tolist()
    random_rets = []
    random_vols = []
    
    print("生成随机对照组...")
    for _ in range(n_random):
        sample_size = min(len(event_idx), len(valid_idx))
        sample = np.random.choice(valid_idx, size=sample_size, replace=False)
        r_ret, r_vol = future_stats(sample)
        if len(r_ret) > 0:
            random_rets.append(np.mean(r_ret))
            random_vols.append(np.mean(r_vol))
    
    random_rets = np.array(random_rets)
    random_vols = np.array(random_vols)
    
    # =========================
    # 显著性检验
    # =========================
    
    # 方向偏移
    n_up = np.sum(event_ret > 0)
    n_total = len(event_ret)
    directional_bias = n_up / n_total
    
    try:
        from scipy.stats import binomtest
        p_dir = binomtest(n_up, n_total, 0.5).pvalue
    except:
        p_dir = stats.binom_test(n_up, n_total, 0.5)
    
    # 波动率差异
    baseline_vol = np.mean(random_vols) if len(random_vols) > 0 else df["ret"].std()
    vol_diff = np.mean(event_vol) - baseline_vol
    t_stat, p_vol = stats.ttest_1samp(event_vol, baseline_vol)
    
    # 信息增益
    if len(random_rets) > 0:
        all_rets = np.concatenate([event_ret, random_rets])
        bins = np.linspace(np.percentile(all_rets, 1), np.percentile(all_rets, 99), 21)
        hist_event, _ = np.histogram(event_ret, bins=bins, density=True)
        hist_rand, _ = np.histogram(random_rets, bins=bins, density=True)
        hist_event += 1e-10
        hist_rand += 1e-10
        kl_div = stats.entropy(hist_event, hist_rand)
    else:
        kl_div = 0
    
    # Cohen's d
    cohens_d = (np.mean(event_vol) - baseline_vol) / np.std(event_vol) if np.std(event_vol) > 0 else 0
    
    # =========================
    # 输出
    # =========================
    print(f"\n----- 统计结果 -----")
    print(f"样本数量          : {len(event_ret)}")
    print(f"方向偏移 P(up)    : {directional_bias:.4f}")
    print(f"方向 p-value      : {p_dir:.6f}")
    print(f"波动率差异        : {vol_diff:.8f}")
    print(f"波动率 p-value    : {p_vol:.6f}")
    print(f"Cohen's d         : {cohens_d:.4f}")
    print(f"KL Divergence     : {kl_div:.6f}")
    
    # 判决
    pass_dir = p_dir < 0.01
    pass_vol = p_vol < 0.05
    pass_kl = kl_div > 0.01
    pass_effect = abs(cohens_d) > 0.2
    
    print(f"\n----- 审稿判决 -----")
    print(f"方向偏移显著 (p<0.01)     : {'✅' if pass_dir else '❌'}")
    print(f"波动率差异显著 (p<0.05)   : {'✅' if pass_vol else '❌'}")
    print(f"信息增益 (KL>0.01)        : {'✅' if pass_kl else '❌'}")
    print(f"效应量 (|d|>0.2)          : {'✅' if pass_effect else '❌'}")
    
    if pass_dir and (pass_vol or pass_kl):
        verdict = "PASS"
        print(f"\n✅ {interval_name} 判决: PASS - 检测到非随机结构")
    elif sum([pass_dir, pass_vol, pass_kl, pass_effect]) >= 2:
        verdict = "WEAK"
        print(f"\n⚠️ {interval_name} 判决: WEAK - 存在弱偏移")
    else:
        verdict = "FAIL"
        print(f"\n❌ {interval_name} 判决: FAIL - 无法拒绝随机游走")
    
    return {
        "interval": interval_name,
        "n_events": len(event_ret),
        "directional_bias": directional_bias,
        "p_dir": p_dir,
        "p_vol": p_vol,
        "cohens_d": cohens_d,
        "kl_div": kl_div,
        "verdict": verdict
    }


# =========================
# 3. 主程序
# =========================
def main():
    print("=" * 60)
    print("BTC 波动率释放 / 区间破坏 统计验证")
    print("=" * 60)
    
    results = []
    
    # 下载并验证 5m 数据
    print("\n" + "=" * 60)
    print("阶段 1: 5 分钟周期验证")
    print("=" * 60)
    
    df_5m = download_klines(interval="5m", start_date="2024-06-01", end_date="2025-01-30")
    if df_5m is not None and len(df_5m) > 1000:
        result_5m = run_validation(df_5m, "5m", window_range=48, future_window=12)
        if result_5m:
            results.append(result_5m)
    
    # 下载并验证 15m 数据
    print("\n" + "=" * 60)
    print("阶段 2: 15 分钟周期验证")
    print("=" * 60)
    
    df_15m = download_klines(interval="15m", start_date="2024-06-01", end_date="2025-01-30")
    if df_15m is not None and len(df_15m) > 1000:
        result_15m = run_validation(df_15m, "15m", window_range=16, future_window=4)
        if result_15m:
            results.append(result_15m)
    
    # =========================
    # 综合结论
    # =========================
    print("\n" + "=" * 60)
    print("综合审稿结论")
    print("=" * 60)
    
    if not results:
        print("❌ 无有效验证结果")
        return
    
    print("\n| 周期 | 事件数 | P(up) | p_dir | p_vol | d | KL | 判决 |")
    print("|------|--------|-------|-------|-------|---|-----|------|")
    for r in results:
        print(f"| {r['interval']} | {r['n_events']} | {r['directional_bias']:.3f} | {r['p_dir']:.4f} | {r['p_vol']:.4f} | {r['cohens_d']:.2f} | {r['kl_div']:.3f} | {r['verdict']} |")
    
    verdicts = [r["verdict"] for r in results]
    
    print("\n" + "=" * 60)
    print("最终审稿判决")
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
2. 考虑替代假设
        """)
    else:
        print("""
❌ 综合判决: FAIL

无法拒绝随机游走假设。
这不是失败，这是研究完成。

下一步：
1. 停止当前假设的工程化
2. 考虑替代假设：
   - 强制行为假设（清算密度）
   - 流动性耗尽假设（订单簿坍塌）
   - 定价锚失效假设（资金费率偏离）
        """)


if __name__ == "__main__":
    main()
