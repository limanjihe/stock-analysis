     1|#!/usr/bin/env python3
     2|"""一夜持股法 - 全腾讯API版"""
     3|import os
     4|for k in list(os.environ.keys()):
     5|    kl = k.lower()
     6|    if 'proxy' in kl:
     7|        del os.environ[k]
     8|os.environ['no_proxy'] = '*'
     9|os.environ['NO_PROXY'] = '*'
    10|
    11|import requests, json, time, re
    12|
    13|session = requests.Session()
    14|session.trust_env = False
    15|no_proxy = {'http': None, 'https': None}
    16|
    17|def parse_tencent_quote(raw_text):
    18|    stocks = {}
    19|    for line in raw_text.strip().split(';'):
    20|        line = line.strip()
    21|        if not line or '=' not in line:
    22|            continue
    23|        m = re.match(r'v_(sh|sz)(\d+)="(.+)"', line)
    24|        if not m:
    25|            continue
    26|        market, code, data = m.group(1), m.group(2), m.group(3)
    27|        parts = data.split('~')
    28|        if len(parts) < 48:
    29|            continue
    30|        try:
    31|            name = parts[1]
    32|            price = float(parts[3]) if parts[3] else 0
    33|            pre_close = float(parts[4]) if parts[4] else 0
    34|            open_p = float(parts[5]) if parts[5] else 0
    35|            volume = int(parts[6]) if parts[6] else 0
    36|            high = float(parts[33]) if len(parts) > 33 and parts[33] else 0
    37|            low = float(parts[34]) if len(parts) > 34 and parts[34] else 0
    38|            amount_wan = float(parts[37]) if len(parts) > 37 and parts[37] else 0
    39|            turnover = float(parts[38]) if len(parts) > 38 and parts[38] else 0
    40|            circ_mv_yi = float(parts[44]) if len(parts) > 44 and parts[44] else 0
    41|            chg_pct = round((price - pre_close) / pre_close * 100, 2) if pre_close > 0 else 0
    42|            stocks[code] = {
    43|                'code': code, 'name': name, 'market': market,
    44|                'price': price, 'pre_close': pre_close, 'open': open_p,
    45|                'high': high, 'low': low, 'volume': volume,
    46|                'amount_wan': amount_wan, 'turnover': turnover,
    47|                'circ_mv_yi': circ_mv_yi, 'chg_pct': chg_pct,
    48|            }
    49|        except:
    50|            continue
    51|    return stocks
    52|
    53|def get_kline_tencent(market_code, days=40):
    54|    """获取前复权日K线 - 腾讯API
    55|    market_code: sh600519 或 sz000001
    56|    返回: list of dict
    57|    """
    58|    # 需要获取足够多天数
    59|    url = 'http://web.ifzq.gtimg.cn/appstock/app/fqkline/get'
    60|    params = {'param': f'{market_code},day,,,60,qfq'}
    61|    try:
    62|        r = session.get(url, params=params, timeout=10, proxies=no_proxy)
    63|        data = r.json()
    64|        d = data.get('data', {}).get(market_code, {})
    65|        klines = d.get('qfqday', []) or d.get('day', [])
    66|        result = []
    67|        for k in klines:
    68|            # [日期, 开, 收, 高, 低, 成交量(手)]
    69|            result.append({
    70|                'date': k[0],
    71|                'open': float(k[1]),
    72|                'close': float(k[2]),
    73|                'high': float(k[3]),
    74|                'low': float(k[4]),
    75|                'volume': float(k[5]),
    76|            })
    77|        return result
    78|    except:
    79|        return []
    80|
    81|print("=" * 70)
    82|print("  一夜持股法 · 7大硬核筛选")
    83|print("  数据源：腾讯财经 API (qt.gtimg.cn + ifzq.gtimg.cn)")
    84|print("  日期：2026-06-10（周三收盘）")
    85|print("=" * 70)
    86|
    87|# Step 1: 全A股代码列表
    88|code_list = []
    89|for i in range(600000, 605000): code_list.append(f'sh{i}')
    90|for i in range(688001, 690000): code_list.append(f'sh{i}')
    91|for i in range(1, 4000):        code_list.append(f'sz{i:06d}')
    92|for i in range(300001, 302000): code_list.append(f'sz{i}')
    93|print(f"代码列表: {len(code_list)} 只")
    94|
    95|# Step 2: 批量获取行情
    96|batch_size = 600
    97|all_stocks = {}
    98|total_batches = (len(code_list) + batch_size - 1) // batch_size
    99|
   100|for batch_idx in range(total_batches):
   101|    start = batch_idx * batch_size
   102|    end = min(start + batch_size, len(code_list))
   103|    batch = code_list[start:end]
   104|    query = ','.join(batch)
   105|    url = f'http://qt.gtimg.cn/q={query}'
   106|    try:
   107|        r = session.get(url, timeout=15, proxies=no_proxy)
   108|        stocks = parse_tencent_quote(r.text)
   109|        all_stocks.update(stocks)
   110|    except:
   111|        pass
   112|    if (batch_idx + 1) % 20 == 0:
   113|        print(f"  批次 {batch_idx+1}/{total_batches}: 累计 {len(all_stocks)} 只有效")
   114|    time.sleep(0.1)
   115|
   116|print(f"获取有效行情: {len(all_stocks)} 只")
   117|
   118|# Step 3: 过滤有效A股
   119|valid = []
   120|for code, s in all_stocks.items():
   121|    if s['price'] <= 0 or s['volume'] <= 0: continue
   122|    if 'ST' in s['name'] or '退' in s['name']: continue
   123|    if s['code'].startswith('8') or s['code'].startswith('9') or s['code'].startswith('4'): continue
   124|    if any(x in s['name'] for x in ['ETF', 'LOF', '债券', '转债', '基金']): continue
   125|    valid.append(s)
   126|print(f"过滤后有效A股: {len(valid)} 只")
   127|
   128|# Step 4: 前五关 + 分时
   129|filtered = []
   130|for s in valid:
   131|    if not (1 <= s['chg_pct'] <= 5): continue
   132|    if not (3 <= s['turnover'] <= 10): continue
   133|    if not (50 <= s['circ_mv_yi'] <= 500): continue
   134|    amt_yi = s['amount_wan'] / 10000
   135|    if amt_yi < 2: continue
   136|    day_range = s['high'] - s['low']
   137|    close_pos = (s['price'] - s['low']) / day_range if day_range > 0 else 0.5
   138|    if close_pos < 0.5: continue
   139|    s['amt_yi'] = amt_yi
   140|    s['close_pos'] = close_pos
   141|    filtered.append(s)
   142|
   143|print(f"\n前5关+分时过滤: {len(filtered)} 只")
   144|
   145|# Step 5: 验证均线 & 量比
   146|print("\n--- 验证均线 & 量比 ---")
   147|results = []
   148|
   149|for i, s in enumerate(filtered):
   150|    mc = f"{s['market']}{s['code']}"
   151|    kline = get_kline_tencent(mc, days=40)
   152|    
   153|    if len(kline) < 10:
   154|        continue
   155|    
   156|    closes = [k['close'] for k in kline]
   157|    volumes = [k['volume'] for k in kline]
   158|    current = closes[-1]
   159|    ma5 = sum(closes[-5:]) / 5
   160|    ma10 = sum(closes[-10:]) / 10
   161|    
   162|    # 第6关：站上5日、10日均线
   163|    if not (current > ma5 and current > ma10):
   164|        continue
   165|    
   166|    # 第2关：量比 = 今日成交量 / 前5日均量
   167|    if len(volumes) >= 6:
   168|        avg5_vol = sum(volumes[-6:-1]) / 5
   169|        vol_ratio = volumes[-1] / avg5_vol if avg5_vol > 0 else 0
   170|    else:
   171|        vol_ratio = 1.0
   172|    
   173|    if vol_ratio < 1.5:
   174|        continue
   175|    
   176|    s['ma5'] = round(ma5, 2)
   177|    s['ma10'] = round(ma10, 2)
   178|    s['vol_ratio'] = round(vol_ratio, 2)
   179|    
   180|    # 均线多头排列
   181|    if len(closes) >= 20:
   182|        ma20 = sum(closes[-20:]) / 20
   183|        s['ma20'] = round(ma20, 2)
   184|        s['bullish_align'] = ma5 > ma10 > ma20
   185|    else:
   186|        s['ma20'] = 0
   187|        s['bullish_align'] = False
   188|    
   189|    results.append(s)
   190|    
   191|    if (i + 1) % 10 == 0:
   192|        print(f"  已验证 {i+1}/{len(filtered)}, 通过 {len(results)} 只")
   193|    time.sleep(0.15)
   194|
   195|print(f"\n全部7关通过: {len(results)} 只")
   196|
   197|# Step 6: 评分排序
   198|for s in results:
   199|    score = 0
   200|    score += s['close_pos'] * 30
   201|    score += min(s['vol_ratio'] / 5, 1) * 25
   202|    score += min(s['chg_pct'] / 5, 1) * 20
   203|    if s.get('bullish_align'): score += 15
   204|    score += (1 - s['circ_mv_yi'] / 500) * 10
   205|    s['score'] = round(score, 1)
   206|
   207|results.sort(key=lambda x: -x['score'])
   208|
   209|# 输出
   210|print("\n" + "=" * 70)
   211|print("  一夜持股法 · 最终筛选结果 (2026-06-10)")
   212|print("=" * 70)
   213|print(f"\n{'代码':<8} {'名称':<8} {'现价':>7} {'涨幅':>6} {'量比':>5} {'换手%':>6} {'流通市值':>8} {'收盘位置':>7} {'MA5':>8} {'MA10':>8} {'多头':>4} {'评分':>5}")
   214|print("-" * 100)
   215|
   216|for s in results[:20]:
   217|    bull = '✓' if s.get('bullish_align') else '✗'
   218|    print(f"{s['code']:<8} {s['name']:<8} {s['price']:>7.2f} {s['chg_pct']:>+5.2f}% {s['vol_ratio']:>5.2f} {s['turnover']:>6.2f} {s['circ_mv_yi']:>6.0f}亿 {s['close_pos']:>7.2%} {s.get('ma5',0):>8.2f} {s.get('ma10',0):>8.2f} {bull:>4} {s['score']:>5.1f}")
   219|
   220|if not results:
   221|    print("\n（无标的通过全部7关）")
   222|
   223|print(f"\n共 {len(results)} 只通过全部7关筛选")
   224|print("\n--- 筛选逻辑 ---")
   225|print("1.涨幅1-5%   → 有动力不追高")
   226|print("2.量比>1.5   → 资金关注度高")
   227|print("3.换手率3-10% → 活跃非妖股")
   228|print("4.流通市值50-500亿 → 弹性好")
   229|print("5.成交额>2亿 → 流动性足")
   230|print("6.站上5/10日均线 → 趋势向上")
   231|print("7.收盘在日内上半区 → 强势收尾")
   232|
   233|with open('/tmp/yiye_results.json', 'w') as f:
   234|    json.dump(results, f, ensure_ascii=False, indent=2)
   235|print("\n结果已保存到 /tmp/yiye_results.json")
   236|