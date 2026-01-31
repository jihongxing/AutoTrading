"""
波动率释放 / 区间破坏 统计验证脚本

文档类型：策略假设验证（Hypothesis Validation）
唯一目标：判断是否存在统计偏移（Statistical Edge）

⚠️ 重要说明：
- 不接交易所 API（避免噪声和权限问题）
- 假设你已经有 BTC K 线 CSV 数据
- 只做一件事：判断"波动率释放 / 区间破坏"是否 statistically non-random
- 不是策略回测，不算收益

数据格式要求（CSV 文件，例如 btc_5m.csv）：
timestamp,open,high,low,close,volume
2022-01-01 00:00:00,46200,46300,46150,46250,123.4
...
- 时间升序
- 任意周期（5m / 15m / 1h 都行）
"""

import pandas as pd
import numpy as np
from scipy import stats


# =========================
# 1. 参数区（可调）
# =========================
CSV_PATH = "btc_5m.csv"
WINDOW_RANGE = 48          # 区间窗口（例如 48 根 5m = 4h）
FUTURE_WINDOW = 12         # 事件后观察窗口
LOW_VOL_PERCENTILE = 0.2   # 低波动分位数
BREAKOUT_K = 1.2           # 区间突破倍数
N_RANDOM = 1000            # 随机事件次数


# =========================
# 2. 数据读取
# =========================
df = pd.read_csv(CSV_PATH, parse_dates=["timestamp"])
df.set_index("timestamp", inplace=True)
df["ret"] = np.log(df["close"]).diff()
df["vol"] = df["ret"].rolling(WINDOW_RANGE).std()


# =========================
# 3. 事件定义
# =========================
# 低波动区间
low_vol_threshold = df["vol"].quantile(LOW_VOL_PERCENTILE)
df["low_vol"] = df["vol"] < low_vol_threshold

# 区间高低
df["range_high"] = df["high"].rolling(WINDOW_RANGE).max()
df["range_low"] = df["low"].rolling(WINDOW_RANGE).min()
df["range_width"] = df["range_high"] - df["range_low"]

# 区间破坏
df["breakout_up"] = df["close"] > df["range_high"] + BREAKOUT_K * df["range_width"].rolling(WINDOW_RANGE).std()
df["breakout_dn"] = df["close"] < df["range_low"] - BREAKOUT_K * df["range_width"].rolling(WINDOW_RANGE).std()

# 联合事件
df["event"] = df["low_vol"] & (df["breakout_up"] | df["breakout_dn"])
event_idx = df.index[df["event"]]

print(f"Total events detected: {len(event_idx)}")


# =========================
# 4. 事件后行为统计
# =========================
def future_stats(indexes):
    future_ret = []
    future_vol = []
    for t in indexes:
        try:
            fwd = df.loc[t:].iloc[1:FUTURE_WINDOW+1]
            future_ret.append(fwd["ret"].sum())
            future_vol.append(fwd["ret"].std())
        except:
            continue
    return np.array(future_ret), np.array(future_vol)


event_ret, event_vol = future_stats(event_idx)


# =========================
# 5. 随机对照组
# =========================
random_rets = []
random_vols = []
valid_idx = df.index[WINDOW_RANGE:-FUTURE_WINDOW]

for _ in range(N_RANDOM):
    sample = np.random.choice(valid_idx, size=len(event_idx), replace=False)
    r_ret, r_vol = future_stats(sample)
    random_rets.append(np.mean(r_ret))
    random_vols.append(np.mean(r_vol))

random_rets = np.array(random_rets)
random_vols = np.array(random_vols)


# =========================
# 6. 显著性检验
# =========================
# 方向偏移
directional_bias = np.mean(event_ret > 0)
p_dir = stats.binom_test(np.sum(event_ret > 0), len(event_ret), 0.5)

# 波动率差异
vol_diff = np.mean(event_vol) - np.mean(random_vols)
t_stat, p_vol = stats.ttest_1samp(event_vol, np.mean(random_vols))

# 信息增益（简化：KL divergence）
hist_event, _ = np.histogram(event_ret, bins=20, density=True)
hist_rand, _ = np.histogram(random_rets, bins=20, density=True)
hist_event += 1e-8
hist_rand += 1e-8
kl_div = stats.entropy(hist_event, hist_rand)


# =========================
# 7. 输出结论
# =========================
print("\n===== VALIDATION RESULT =====")
print(f"Directional Bias P(up): {directional_bias:.3f}")
print(f"Directional p-value   : {p_dir:.5f}")
print(f"Volatility diff       : {vol_diff:.6f}")
print(f"Volatility p-value    : {p_vol:.5f}")
print(f"KL Divergence (IG)    : {kl_div:.6f}")

print("\n===== REVIEWER VERDICT =====")
if p_dir < 0.01 and p_vol < 0.01 and kl_div > 0.01:
    print("✅ PASS: Non-random structure detected")
    print("   → 可以进入策略工程")
else:
    print("❌ FAIL: Cannot reject random walk hypothesis")
    print("   → 立即承认：这是一个'空壳框架'")


# =========================
# 8. 审稿式解读指南
# =========================
"""
你只看三行：
- Directional p-value
- Volatility p-value
- KL Divergence

✅ 通过（值得继续）
- p_dir < 0.01
- p_vol < 0.01
- KL > 0.01 且不随样本扩展衰减
→ 可以进入策略工程

❌ 不通过（立刻停）
- 任一 p-value 接近 0.1
- KL → 0
- 换周期即崩
→ 立即承认：这是一个"空壳框架"

工程级忠告：
- 不要急着改参数
- 改参数 ≠ 新假设
- 改参数 ≈ p-hacking
- 如果这个脚本跑出来是 FAIL，你已经赢了
  因为你节省了至少 6–12 个月工程时间
"""
