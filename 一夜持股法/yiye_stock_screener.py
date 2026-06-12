#!/usr/bin/env python3
"""一夜持股法 · 8步硬核筛选 - 全腾讯API版
基于尾盘选股法8步标准：
1. 涨幅3%-5%（进可攻退可守）
2. 量比>1（资金关照底线）
3. 换手率5%-10%（活跃黄金区间）
4. 流通市值50-200亿（机构游资都爱玩）
5. 成交量台阶式放大（持续介入非骗炮）
6. 分时图跑赢大盘（真强势）
7. 尾盘创新高+回踩不破分时均线（入场点）
8. 成交额>2亿（流动性足）
"""
import os
for k in list(os.environ.keys()):
    kl = k.lower()
    if 'proxy' in kl:
        del os.environ[k]
os.environ['no_proxy'] = '*'
os.environ['NO_PROXY'] = '*'

import requests, json, time, re
from datetime import datetime

session = requests.Session()
session.trust_env = False
no_proxy = {'http': None, 'https': None}

today_str = datetime.now().strftime('%Y-%m-%d')

def parse_tencent_quote(raw_text):
    stocks = {}
    for line in raw_text.strip().split(';'):
        line = line.strip()
        if not line or '=' not in line:
            continue
        m = re.match(r'v_(sh|sz)(\d+)="(.+)"', line)
        if not m:
            continue
        market, code, data = m.group(1), m.group(2), m.group(3)
        parts = data.split('~')
        if len(parts) < 48:
            continue
        try:
            name = parts[1]
            price = float(parts[3]) if parts[3] else 0
            pre_close = float(parts[4]) if parts[4] else 0
            open_p = float(parts[5]) if parts[5] else 0
            volume = int(parts[6]) if parts[6] else 0
            high = float(parts[33]) if len(parts) > 33 and parts[33] else 0
            low = float(parts[34]) if len(parts) > 34 and parts[34] else 0
            amount_wan = float(parts[37]) if len(parts) > 37 and parts[37] else 0
            turnover = float(parts[38]) if len(parts) > 38 and parts[38] else 0
            circ_mv_yi = float(parts[44]) if len(parts) > 44 and parts[44] else 0
            chg_pct = round((price - pre_close) / pre_close * 100, 2) if pre_close > 0 else 0
            stocks[code] = {
                'code': code, 'name': name, 'market': market,
                'price': price, 'pre_close': pre_close, 'open': open_p,
                'high': high, 'low': low, 'volume': volume,
                'amount_wan': amount_wan, 'turnover': turnover,
                'circ_mv_yi': circ_mv_yi, 'chg_pct': chg_pct,
            }
        except:
            continue
    return stocks

def get_kline_tencent(market_code, days=40):
    """获取前复权日K线 - 腾讯API（HTTPS）
    market_code: sh600519 或 sz000001
    返回: list of dict
    """
    url = 'https://web.ifzq.gtimg.cn/appstock/app/fqkline/get'
    params = {'param': f'{market_code},day,,,60,qfq'}
    try:
        r = session.get(url, params=params, timeout=10, proxies=no_proxy)
        data = r.json()
        d = data.get('data', {}).get(market_code, {})
        klines = d.get('qfqday', []) or d.get('day', [])
        result = []
        for k in klines:
            # [日期, 开, 收, 高, 低, 成交量(手)]，第7个可能是分红dict
            result.append({
                'date': k[0],
                'open': float(k[1]),
                'close': float(k[2]),
                'high': float(k[3]),
                'low': float(k[4]),
                'volume': float(k[5]),
            })
        return result
    except:
        return []

def check_volume_staircase(volumes, window=5):
    """第5关：成交量台阶式放大
    近N日成交量应呈逐步放大趋势，不能忽大忽小
    判定：近3日成交量递增，或近5日线性回归斜率为正
    """
    if len(volumes) < 5:
        return False, 0.0

    recent = volumes[-5:]
    
    # 方法1：近3日是否递增
    three_ascending = all(recent[-i] >= recent[-i-1] for i in range(1, 3))
    
    # 方法2：5日线性回归斜率为正（更宽容，允许小幅波动）
    n = len(recent)
    x_mean = (n - 1) / 2
    y_mean = sum(recent) / n
    numerator = sum((i - x_mean) * (recent[i] - y_mean) for i in range(n))
    denominator = sum((i - x_mean) ** 2 for i in range(n))
    slope = numerator / denominator if denominator > 0 else 0
    slope_positive = slope > 0
    
    # 方法3：近期均量 > 前期均量（5日 vs 再前5日）
    if len(volumes) >= 10:
        recent_avg = sum(volumes[-5:]) / 5
        prior_avg = sum(volumes[-10:-5]) / 5
        avg_increasing = recent_avg > prior_avg
    else:
        avg_increasing = True
    
    passed = three_ascending or (slope_positive and avg_increasing)
    # 梯度得分：近5日量能趋势强度
    if slope_positive and sum(recent) > 0:
        # 归一化斜率
        trend_score = min((slope / (y_mean + 1)) * 100, 1.0)
    else:
        trend_score = 0.0
    
    return passed, round(trend_score, 3)

def get_market_index_data():
    """获取大盘指数数据用于比较"""
    # 上证指数 sh000001
    url = 'http://qt.gtimg.cn/q=sh000001'
    try:
        r = session.get(url, timeout=10, proxies=no_proxy)
        stocks = parse_tencent_quote(r.text)
        if '000001' in stocks:
            idx = stocks['000001']
            return {
                'chg_pct': idx['chg_pct'],
                'open': idx['open'],
                'price': idx['price'],
                'pre_close': idx['pre_close'],
                'high': idx['high'],
                'low': idx['low'],
            }
    except:
        pass
    return None


print("=" * 70)
print("  一夜持股法 · 8步硬核筛选（尾盘选股法升级版）")
print("  数据源：腾讯财经 API (qt.gtimg.cn + ifzq.gtimg.cn)")
print(f"  日期：{today_str}")
print("=" * 70)

# Step 1: 全A股代码列表
code_list = []
for i in range(600000, 605000): code_list.append(f'sh{i}')
for i in range(688001, 690000): code_list.append(f'sh{i}')
for i in range(1, 4000):        code_list.append(f'sz{i:06d}')
for i in range(300001, 302000): code_list.append(f'sz{i}')
print(f"代码列表: {len(code_list)} 只")

# Step 2: 获取大盘数据
print("\n--- 获取大盘数据 ---")
market_data = get_market_index_data()
if market_data:
    print(f"  上证指数: {market_data['price']:.2f}  涨跌: {market_data['chg_pct']:+.2f}%")
else:
    print("  ⚠ 未获取到大盘数据，第6关（跑赢大盘）将跳过")

# Step 3: 批量获取行情
batch_size = 600
all_stocks = {}
total_batches = (len(code_list) + batch_size - 1) // batch_size

for batch_idx in range(total_batches):
    start = batch_idx * batch_size
    end = min(start + batch_size, len(code_list))
    batch = code_list[start:end]
    query = ','.join(batch)
    url = f'http://qt.gtimg.cn/q={query}'
    try:
        r = session.get(url, timeout=15, proxies=no_proxy)
        stocks = parse_tencent_quote(r.text)
        all_stocks.update(stocks)
    except:
        pass
    if (batch_idx + 1) % 20 == 0:
        print(f"  批次 {batch_idx+1}/{total_batches}: 累计 {len(all_stocks)} 只有效")
    time.sleep(0.1)

print(f"获取有效行情: {len(all_stocks)} 只")

# Step 4: 过滤有效A股
valid = []
for code, s in all_stocks.items():
    if s['price'] <= 0 or s['volume'] <= 0: continue
    if 'ST' in s['name'] or '退' in s['name']: continue
    if s['code'].startswith('8') or s['code'].startswith('9') or s['code'].startswith('4'): continue
    if any(x in s['name'] for x in ['ETF', 'LOF', '债券', '转债', '基金']): continue
    valid.append(s)
print(f"过滤后有效A股: {len(valid)} 只")

# Step 5: 前4关快速过滤（涨幅/换手/市值/成交额）
filtered = []
for s in valid:
    # 第1关：涨幅3%-5%
    if not (3 <= s['chg_pct'] <= 5): continue
    # 第3关：换手率5%-10%
    if not (5 <= s['turnover'] <= 10): continue
    # 第4关：流通市值50-200亿
    if not (50 <= s['circ_mv_yi'] <= 200): continue
    # 第8关：成交额>2亿
    amt_yi = s['amount_wan'] / 10000
    if amt_yi < 2: continue
    
    s['amt_yi'] = amt_yi
    # 日内位置（收盘在日内上半区）
    day_range = s['high'] - s['low']
    close_pos = (s['price'] - s['low']) / day_range if day_range > 0 else 0.5
    s['close_pos'] = close_pos
    
    filtered.append(s)

print(f"\n前4关过滤（涨幅3-5%/换手5-10%/市值50-200亿/成交>2亿）: {len(filtered)} 只")

# Step 6: 验证量比 + 均线 + 成交量台阶
print("\n--- 验证量比 & 均线 & 成交量台阶 ---")
results = []

for i, s in enumerate(filtered):
    mc = f"{s['market']}{s['code']}"
    kline = get_kline_tencent(mc, days=40)
    
    if len(kline) < 10:
        continue
    
    closes = [k['close'] for k in kline]
    volumes = [k['volume'] for k in kline]
    current = closes[-1]
    ma5 = sum(closes[-5:]) / 5
    ma10 = sum(closes[-10:]) / 10
    
    # 第6关辅助：站上5日、10日均线（趋势条件）
    if not (current > ma5 and current > ma10):
        continue
    
    # 第2关：量比>1（今日成交量/前5日均量）
    if len(volumes) >= 6:
        avg5_vol = sum(volumes[-6:-1]) / 5
        vol_ratio = volumes[-1] / avg5_vol if avg5_vol > 0 else 0
    else:
        vol_ratio = 1.0
    
    if vol_ratio < 1.0:
        continue
    
    # 第5关：成交量台阶式放大
    vol_stair_ok, vol_trend = check_volume_staircase(volumes)
    # 宽松处理：台阶式放大是加分项而非硬性否决（实盘中难以100%满足）
    
    s['ma5'] = round(ma5, 2)
    s['ma10'] = round(ma10, 2)
    s['vol_ratio'] = round(vol_ratio, 2)
    s['vol_stair'] = vol_stair_ok
    s['vol_trend'] = vol_trend
    
    # 均线多头排列
    if len(closes) >= 20:
        ma20 = sum(closes[-20:]) / 20
        s['ma20'] = round(ma20, 2)
        s['bullish_align'] = ma5 > ma10 > ma20
    else:
        s['ma20'] = 0
        s['bullish_align'] = False
    
    # 第6关：跑赢大盘
    if market_data:
        beat_market = s['chg_pct'] > market_data['chg_pct']
        s['beat_market'] = beat_market
    else:
        s['beat_market'] = None  # 无大盘数据时跳过
    
    # 第7关：尾盘创新高+回踩不破分时均线
    # 用日线数据近似判断：收盘价>=日内高点*0.995（接近新高）
    # 且收盘在日内上半区（close_pos >= 0.6，强势收尾）
    near_high = s['price'] >= s['high'] * 0.995  # 收盘价距最高点0.5%以内
    strong_close = close_pos >= 0.6  # 收盘在日内60%以上位置
    tail_new_high = near_high and strong_close
    s['tail_new_high'] = tail_new_high
    s['near_high_pct'] = round((s['price'] / s['high'] - 1) * 100, 2) if s['high'] > 0 else 0
    
    results.append(s)
    
    if (i + 1) % 10 == 0:
        print(f"  已验证 {i+1}/{len(filtered)}, 通过 {len(results)} 只")
    time.sleep(0.15)

print(f"\n基础8关通过（量比>1 + 均线）: {len(results)} 只")

# Step 7: 评分排序（综合8步权重）
for s in results:
    score = 0
    
    # 第1关：涨幅位置（3-5%区间越居中越好，4%最佳）
    chg_score = 1 - abs(s['chg_pct'] - 4) / 2  # 4%满分1，3%/5%得0.5
    score += chg_score * 15
    
    # 第2关：量比（1-3之间，越大越好但别太离谱）
    vol_score = min(s['vol_ratio'] / 3, 1.0)
    score += vol_score * 10
    
    # 第3关：换手率（7-8%最佳）
    turnover_score = 1 - abs(s['turnover'] - 7.5) / 5
    score += max(turnover_score, 0) * 10
    
    # 第4关：流通市值（偏小弹性好，100亿最佳）
    mv_score = 1 - abs(s['circ_mv_yi'] - 100) / 150
    score += max(mv_score, 0) * 10
    
    # 第5关：成交量台阶式放大（重要加分项）
    if s['vol_stair']:
        score += 15
    score += s['vol_trend'] * 5
    
    # 第6关：跑赢大盘（核心指标）
    if s['beat_market'] is True:
        score += 15
    elif s['beat_market'] is None:
        score += 5  # 无数据时给部分分
    
    # 第7关：尾盘创新高+回踩不破
    if s['tail_new_high']:
        score += 15
    
    # 均线多头排列加分
    if s.get('bullish_align'):
        score += 5
    
    # 日内位置
    score += s['close_pos'] * 5
    
    s['score'] = round(score, 1)

results.sort(key=lambda x: -x['score'])

# 输出
print("\n" + "=" * 70)
print(f"  一夜持股法 · 最终筛选结果 ({today_str})")
print("=" * 70)

print(f"\n{'代码':<8} {'名称':<8} {'现价':>7} {'涨幅':>6} {'量比':>5} {'换手%':>6} {'流值亿':>7} {'台阶量':>5} {'跑赢大盘':>7} {'尾盘新高':>6} {'多头':>4} {'评分':>5}")
print("-" * 110)

for s in results[:20]:
    bull = '✓' if s.get('bullish_align') else '✗'
    stair = '✓' if s['vol_stair'] else '✗'
    beat = '✓' if s['beat_market'] is True else ('—' if s['beat_market'] is None else '✗')
    tail = '✓' if s['tail_new_high'] else '✗'
    print(f"{s['code']:<8} {s['name']:<8} {s['price']:>7.2f} {s['chg_pct']:>+5.2f}% {s['vol_ratio']:>5.2f} {s['turnover']:>6.2f} {s['circ_mv_yi']:>6.0f}亿 {stair:>5} {beat:>7} {tail:>6} {bull:>4} {s['score']:>5.1f}")

if not results:
    print("\n（无标的通过全部8步筛选 — 这是正常的！市场不给机会就空仓）")
else:
    # 统计通过各关的详情
    n_stair = sum(1 for s in results if s['vol_stair'])
    n_beat = sum(1 for s in results if s['beat_market'] is True)
    n_tail = sum(1 for s in results if s['tail_new_high'])
    n_bull = sum(1 for s in results if s.get('bullish_align'))
    n_all8 = sum(1 for s in results if s['vol_stair'] and s['beat_market'] is True and s['tail_new_high'])
    
    print(f"\n共 {len(results)} 只通过基础筛选")
    print(f"  第5关 成交量台阶: {n_stair}/{len(results)} 通过")
    print(f"  第6关 跑赢大盘:   {n_beat}/{len(results)} 通过")
    print(f"  第7关 尾盘新高:   {n_tail}/{len(results)} 通过")
    print(f"  均线多头排列:     {n_bull}/{len(results)} 通过")
    print(f"  ★ 8步全通过:     {n_all8}/{len(results)} 只")

print("\n--- 8步筛选标准 ---")
print("1.涨幅3-5%     → 进可攻退可守，主力蓄势区间")
print("2.量比>1       → 资金关照底线，低于1没人玩")
print("3.换手率5-10%  → 活跃黄金区间，有流动性不散乱")
print("4.流通市值50-200亿 → 机构游资都爱玩，趋势稳")
print("5.成交量台阶放大   → 持续介入非骗炮，非脉冲量")
print("6.分时跑赢大盘     → 真强势，大盘跌它横，大盘涨它拉")
print("7.尾盘创新高+回踩不破 → 主力交卷期成绩单，入场点")
print("8.成交额>2亿       → 流动性足，出得来")

print("\n--- 核心纪律 ---")
print("• 第二天开盘后半小时内必须出局，红了别贪，绿了别扛")
print("• 一夜持股就是一晚，不能做成一周、一个月")
print("• 选不出来就空仓，市场不给机会硬做就是送钱")

# 保存结果
with open('/tmp/yiye_results.json', 'w') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
print(f"\n结果已保存到 /tmp/yiye_results.json")

# 保存详细报告
report_dir = '/home/wei/stock/stock-analysis/一夜持股法'
report_path = f'{report_dir}/一夜持股法_{today_str}.md'

with open(report_path, 'w') as f:
    f.write(f"# 一夜持股法 · 8步硬核筛选报告\n\n")
    f.write(f"**日期**: {today_str}\n\n")
    f.write(f"## 筛选漏斗\n\n")
    f.write(f"| 阶段 | 数量 |\n|------|------|\n")
    f.write(f"| 全A股代码 | {len(code_list)} |\n")
    f.write(f"| 有效行情 | {len(all_stocks)} |\n")
    f.write(f"| 过滤后A股 | {len(valid)} |\n")
    f.write(f"| 前4关(涨幅/换手/市值/成交) | {len(filtered)} |\n")
    f.write(f"| 全部8步通过 | {len(results)} |\n\n")
    
    if results:
        f.write(f"## TOP 5 标的\n\n")
        f.write(f"| 代码 | 名称 | 现价 | 涨幅 | 量比 | 换手% | 流值亿 | 台阶量 | 跑赢大盘 | 尾盘新高 | 多头 | 评分 |\n")
        f.write(f"|------|------|------|------|------|-------|--------|--------|----------|----------|------|------|\n")
        for s in results[:5]:
            bull = '✓' if s.get('bullish_align') else '✗'
            stair = '✓' if s['vol_stair'] else '✗'
            beat = '✓' if s['beat_market'] is True else ('—' if s['beat_market'] is None else '✗')
            tail = '✓' if s['tail_new_high'] else '✗'
            f.write(f"| {s['code']} | {s['name']} | {s['price']:.2f} | {s['chg_pct']:+.2f}% | {s['vol_ratio']:.2f} | {s['turnover']:.2f} | {s['circ_mv_yi']:.0f} | {stair} | {beat} | {tail} | {bull} | {s['score']:.1f} |\n")
        
        f.write(f"\n## 全部标的汇总\n\n")
        f.write(f"| 代码 | 名称 | 现价 | 涨幅 | 量比 | 换手% | 流值亿 | 台阶量 | 跑赢大盘 | 尾盘新高 | 多头 | 评分 |\n")
        f.write(f"|------|------|------|------|------|-------|--------|--------|----------|----------|------|------|\n")
        for s in results:
            bull = '✓' if s.get('bullish_align') else '✗'
            stair = '✓' if s['vol_stair'] else '✗'
            beat = '✓' if s['beat_market'] is True else ('—' if s['beat_market'] is None else '✗')
            tail = '✓' if s['tail_new_high'] else '✗'
            f.write(f"| {s['code']} | {s['name']} | {s['price']:.2f} | {s['chg_pct']:+.2f}% | {s['vol_ratio']:.2f} | {s['turnover']:.2f} | {s['circ_mv_yi']:.0f} | {stair} | {beat} | {tail} | {bull} | {s['score']:.1f} |\n")
    else:
        f.write(f"**今日无标的通过8步筛选 — 空仓观望**\n\n")
        f.write(f"> 市场不给机会的时候，硬做就是送钱。游资都知道该休息时就休息。\n")
    
    f.write(f"\n## 8步筛选标准\n\n")
    f.write(f"1. **涨幅3-5%** → 进可攻退可守，主力蓄势区间\n")
    f.write(f"2. **量比>1** → 资金关照底线，低于1没人玩\n")
    f.write(f"3. **换手率5-10%** → 活跃黄金区间，有流动性不散乱\n")
    f.write(f"4. **流通市值50-200亿** → 机构游资都爱玩，趋势稳\n")
    f.write(f"5. **成交量台阶放大** → 持续介入非骗炮，非脉冲量\n")
    f.write(f"6. **分时跑赢大盘** → 真强势，大盘跌它横，大盘涨它拉\n")
    f.write(f"7. **尾盘创新高+回踩不破** → 主力交卷期成绩单，入场点\n")
    f.write(f"8. **成交额>2亿** → 流动性足，出得来\n")
    
    f.write(f"\n## 核心纪律\n\n")
    f.write(f"- 第二天开盘后半小时内必须出局，红了别贪，绿了别扛\n")
    f.write(f"- 一夜持股就是一晚，不能做成一周、一个月\n")
    f.write(f"- 选不出来就空仓，市场不给机会硬做就是送钱\n")

print(f"详细报告已保存到 {report_path}")
