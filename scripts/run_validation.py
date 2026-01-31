"""
波动率释放 / 区间破坏 统计验证脚本（完整版）

自动读取 Binance 历史数据目录，合并 CSV，分别对 5m / 15m 跑验证
输出审稿级结论

数据目录结构：
data/spot/monthly/klines/BTCUSDT/5m/*.csv
data/spot/monthly/klines/BTCUSDT/15m/*.csv
"""

import os
import glob
import pandas as pd
import numpy as np
from scipy import stats
import warnings
warnings.filterwarnings('ignore')


# =========================
# 1. 数据读取与合并
# =========================
def load_binance_klines(data_dir):
    """
    读取 Binance 历史数据目录下所有 CSV 并合并
    Binance 格式：open_time,open,high,low,close,volume,close_time,...
    """
    csv_files = sorted(glob.glob(os.path.join(data_dir, "*.csv")))
    
    if not csv_files:
        print(f"❌ 未找到 CSV 文件: {data_dir}")
        return None
    
    print(f"找到 {len(csv_files)} 个 CSV 文件")
    
    dfs = []
    for f in csv_files:
        try:
            # Binance 数据无表头
            df = pd.read_csv(f, header=None, names=[
                "open_time", "open", "high", "low", "close", "volume",
                "close_time", "quote_volume", "trades", "taker_buy_base",
                "taker_buy_quote", "ignore"
            ])
            dfs.append(df)
        except Exception as e:
            print(f"读取失败: {f}, 错误: {e}")
            continue
    
    if not dfs:
        return None
    
    df = pd.concat(dfs, ignore_index=True)
    
    # 转换时间戳
    df["timestamp"] = pd.to_datetime(df["open_time"], unit="ms")
    df = df[["timestamp", "open", "high", "low", "close", "volume"]]
    
    # 转换数值类型
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # 去重并排序
    df = df.drop_duplicates(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)
    
    print(f"合并完成: {len(df)} 条数据")
    print(f"时间范围: {df['timestamp'].min()} ~ {df['timestamp'].max()}")
    
    return df


# =========================
# 2. 验证核心逻辑
# =========================
def run_validation(df, interval_name, window_range=48, future_window=12, 
                   low_vol_percentile=0.2, breakout_k=1.2, n_random=1000):
    """
    运行波动率释放 + 区间破坏验证
    """
    print(f"\n{'='*60}")
    print(f"验证周期: {interval_name}")
    print(f"参数: window={window_range}, future={future_window}, low_vol_pct={low_vol_percentile}")
    print(f"{'='*60}")
    
    # 计算收益率和波动率
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
    
    # 联合事件：低波动 + 区间破坏
    df["event"] = df["low_vol"] & (df["breakout_up"] | df["breakout_dn"])
    
    # 清理 NaN
    df = df.dropna()
    
    event_idx = df.index[df["event"]]
    print(f"检测到事件数: {len(event_idx)}")
    
    if len(event_idx) < 30:
        print("⚠️ 事件数量不足，无法进行有效统计检验")
        return None
    
    # 事件后行为统计
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
        print("⚠️ 有效事件样本不足")
        return None
    
    # 随机对照组
    valid_idx = df.index[window_range:-future_window].tolist()
    random_rets = []
    random_vols = []
    
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
    
    # 1. 方向偏移
    n_up = np.sum(event_ret > 0)
    n_total = len(event_ret)
    directional_bias = n_up / n_total
    
    # 使用 binomtest (scipy >= 1.7) 或 binom_test
    try:
        from scipy.stats import binomtest
        p_dir = binomtest(n_up, n_total, 0.5).pvalue
    except ImportError:
        p_dir = stats.binom_test(n_up, n_total, 0.5)
    
    # 2. 波动率差异
    baseline_vol = np.mean(random_vols) if len(random_vols) > 0 else df["ret"].std()
    vol_diff = np.mean(event_vol) - baseline_vol
    
    if len(event_vol) > 1:
        t_stat, p_vol = stats.ttest_1samp(event_vol, baseline_vol)
    else:
        p_vol = 1.0
    
    # 3. 信息增益 (KL Divergence)
    if len(random_rets) > 0 and len(event_ret) > 0:
        # 使用相同的 bins
        all_rets = np.concatenate([event_ret, random_rets])
        bins = np.linspace(np.percentile(all_rets, 1), np.percentile(all_rets, 99), 21)
        
        hist_event, _ = np.histogram(event_ret, bins=bins, density=True)
        hist_rand, _ = np.histogram(random_rets, bins=bins, density=True)
        
        # 避免除零
        hist_event = hist_event + 1e-10
        hist_rand = hist_rand + 1e-10
        
        kl_div = stats.entropy(hist_event, hist_rand)
    else:
        kl_div = 0
    
    # 4. Cohen's d (效应量)
    if len(event_vol) > 1 and np.std(event_vol) > 0:
        cohens_d = (np.mean(event_vol) - baseline_vol) / np.std(event_vol)
    else:
        cohens_d = 0
    
    # =========================
    # 输出结果
    # =========================
    print(f"\n----- 统计结果 -----")
    print(f"样本数量          : {len(event_ret)}")
    print(f"方向偏移 P(up)    : {directional_bias:.4f}")
    print(f"方向 p-value      : {p_dir:.6f}")
    print(f"波动率差异        : {vol_diff:.8f}")
    print(f"波动率 p-value    : {p_vol:.6f}")
    print(f"Cohen's d         : {cohens_d:.4f}")
    print(f"KL Divergence     : {kl_div:.6f}")
    
    # =========================
    # 审稿级判决
    # =========================
    print(f"\n----- 审稿判决 -----")
    
    # 判决逻辑
    pass_dir = p_dir < 0.01
    pass_vol = p_vol < 0.05
    pass_kl = kl_div > 0.01
    pass_effect = abs(cohens_d) > 0.2
    
    print(f"方向偏移显著 (p<0.01)     : {'✅ PASS' if pass_dir else '❌ FAIL'}")
    print(f"波动率差异显著 (p<0.05)   : {'✅ PASS' if pass_vol else '❌ FAIL'}")
    print(f"信息增益 (KL>0.01)        : {'✅ PASS' if pass_kl else '❌ FAIL'}")
    print(f"效应量 (|d|>0.2)          : {'✅ PASS' if pass_effect else '❌ FAIL'}")
    
    # 综合判决
    pass_count = sum([pass_dir, pass_vol, pass_kl, pass_effect])
    
    print(f"\n===== 最终判决 ({interval_name}) =====")
    
    if pass_dir and (pass_vol or pass_kl):
        print("✅ PASS: 检测到非随机结构")
        print("   → 可以进入策略工程阶段")
        verdict = "PASS"
    elif pass_count >= 2:
        print("⚠️ WEAK: 存在弱偏移，仅在特定条件下有效")
        print("   → 降级为研究框架，不建议自动化执行")
        verdict = "WEAK"
    else:
        print("❌ FAIL: 无法拒绝随机游走假设")
        print("   → 停止工程化，考虑替代假设")
        verdict = "FAIL"
    
    return {
        "interval": interval_name,
        "n_events": len(event_ret),
        "directional_bias": directional_bias,
        "p_dir": p_dir,
        "vol_diff": vol_diff,
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
    print("波动率释放 / 区间破坏 统计验证")
    print("=" * 60)
    
    results = []
    
    # 5m 数据验证
    data_dir_5m = "data/spot/monthly/klines/BTCUSDT/5m"
    if os.path.exists(data_dir_5m):
        df_5m = load_binance_klines(data_dir_5m)
        if df_5m is not None and len(df_5m) > 1000:
            # 5m: window=48 (4小时), future=12 (1小时)
            result_5m = run_validation(df_5m, "5m", window_range=48, future_window=12)
            if result_5m:
                results.append(result_5m)
    else:
        print(f"⚠️ 目录不存在: {data_dir_5m}")
    
    # 15m 数据验证
    data_dir_15m = "data/spot/monthly/klines/BTCUSDT/15m"
    if os.path.exists(data_dir_15m):
        df_15m = load_binance_klines(data_dir_15m)
        if df_15m is not None and len(df_15m) > 1000:
            # 15m: window=16 (4小时), future=4 (1小时)
            result_15m = run_validation(df_15m, "15m", window_range=16, future_window=4)
            if result_15m:
                results.append(result_15m)
    else:
        print(f"⚠️ 目录不存在: {data_dir_15m}")
    
    # =========================
    # 综合结论
    # =========================
    print("\n" + "=" * 60)
    print("综合审稿结论")
    print("=" * 60)
    
    if not results:
        print("❌ 无有效验证结果")
        return
    
    # 汇总表
    print("\n| 周期 | 事件数 | P(up) | p_dir | p_vol | Cohen's d | KL | 判决 |")
    print("|------|--------|-------|-------|-------|-----------|-----|------|")
    for r in results:
        print(f"| {r['interval']} | {r['n_events']} | {r['directional_bias']:.3f} | {r['p_dir']:.4f} | {r['p_vol']:.4f} | {r['cohens_d']:.3f} | {r['kl_div']:.4f} | {r['verdict']} |")
    
    # 最终判决
    verdicts = [r["verdict"] for r in results]
    
    print("\n" + "=" * 60)
    print("最终审稿判决")
    print("=" * 60)
    
    if all(v == "PASS" for v in verdicts):
        print("""
✅ 综合判决: PASS

假设「波动率释放 + 区间破坏」在 BTC 市场存在统计偏移。
可以进入下一阶段：
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
3. 不建议跨周期组合
        """)
    elif any(v == "WEAK" for v in verdicts):
        print("""
⚠️ 综合判决: WEAK

存在弱偏移，但不足以支撑工程化。
建议：
1. 降级为研究框架
2. 不做自动化执行
3. 考虑替代假设
        """)
    else:
        print("""
❌ 综合判决: FAIL

无法拒绝随机游走假设。
这不是失败，这是研究完成。

下一步：
1. 停止当前假设的工程化
2. 考虑替代假设路径：
   - 强制行为假设（清算密度、止损触发）
   - 流动性耗尽假设（订单簿斜率坍塌）
   - 定价锚失效假设（资金费率/基差偏离）
3. 或承认：BTC 在该时间尺度是近似有效市场
        """)


if __name__ == "__main__":
    main()
