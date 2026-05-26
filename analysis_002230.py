import datetime
from collections import defaultdict

# Read cached daily data
with open(r"C:\Users\jiayi\.claude\projects\C--Users-jiayi-stock\dcbb05db-acc4-4559-9c42-20c83ff8a9d7\tool-results\b73mzsf9l.txt", "r") as f:
    raw = f.read()

all_daily = []
for line in raw.strip().split("\n"):
    if line.startswith("202") and "O:" in line:
        parts = line.split()
        date = parts[0]
        o = float(parts[1].split(":")[1])
        h = float(parts[2].split(":")[1])
        l = float(parts[3].split(":")[1])
        c = float(parts[4].split(":")[1])
        v = float(parts[5].split(":")[1])
        a = float(parts[6].split(":")[1])
        chg = float(parts[7].split(":")[1].rstrip("%"))
        turn = float(parts[8].split(":")[1].rstrip("%"))
        all_daily.append({"date":date, "o":o, "h":h, "l":l, "c":c, "v":v, "a":a, "chg":chg, "turn":turn})

print(f"Loaded {len(all_daily)} daily bars: {all_daily[0]['date']} ~ {all_daily[-1]['date']}")

closes = [d["c"] for d in all_daily]
highs = [d["h"] for d in all_daily]
lows = [d["l"] for d in all_daily]
volumes = [d["v"] for d in all_daily]
amounts = [d["a"] for d in all_daily]
dates = [d["date"] for d in all_daily]
current = closes[-1]

# Last 30 days
print("\n=== DAILY (last 30) ===")
for i in range(max(0, len(all_daily)-30), len(all_daily)):
    d = all_daily[i]
    ma5 = sum(closes[i-4:i+1])/5 if i >= 4 else 0
    ma10 = sum(closes[i-9:i+1])/10 if i >= 9 else 0
    ma20 = sum(closes[i-19:i+1])/20 if i >= 19 else 0
    ma60 = sum(closes[i-59:i+1])/60 if i >= 59 else 0
    print(f"{d['date']} O:{d['o']:.2f} H:{d['h']:.2f} L:{d['l']:.2f} C:{d['c']:.2f} Chg:{d['chg']:+.2f}% Trn:{d['turn']:.1f}% Amt:{d['a']/1e8:.1f}B MA5:{ma5:.2f} MA10:{ma10:.2f} MA20:{ma20:.2f} MA60:{ma60:.2f}")

# RSI
print("\n=== RSI ===")
for period in [6, 14]:
    gains, losses = [], []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i-1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    for i in range(len(gains) - period - 1, len(gains)):
        avg_gain = (avg_gain * (period-1) + gains[i]) / period
        avg_loss = (avg_loss * (period-1) + losses[i]) / period
    rs = avg_gain / avg_loss if avg_loss > 0 else 100
    rsi = 100 - (100 / (1 + rs))
    print(f"RSI({period}): {rsi:.1f}")

# MACD
print("\n=== MACD ===")
ema12, ema26 = closes[0], closes[0]
dif_values = []
for c in closes[1:]:
    ema12 = c * (2/13) + ema12 * (11/13)
    ema26 = c * (2/27) + ema26 * (25/27)
    dif_values.append(ema12 - ema26)

dea = dif_values[0]
for d in dif_values[1:]:
    dea = d * (2/10) + dea * (8/10)
macd = 2 * (dif_values[-1] - dea)
print(f"DIF: {dif_values[-1]:.4f} | DEA: {dea:.4f} | MACD: {macd:.4f}")
if dif_values[-1] > dea:
    print("DIF above DEA (bullish)")
else:
    print("DIF below DEA (bearish)")

# Check MACD momentum - is histogram growing or shrinking
hist_today = 2 * (dif_values[-1] - dea)
hist_yesterday = 2 * (dif_values[-2] - (dea * 10/8 - dif_values[-2] * 2/8))
print(f"MACD histogram momentum: {'expanding' if hist_today > hist_yesterday else 'contracting'}")

# Volume
print("\n=== VOLUME ===")
avg_amt_20 = sum(amounts[-20:]) / 20
avg_amt_5 = sum(amounts[-5:]) / 5
avg_vol_20 = sum(volumes[-20:]) / 20
avg_vol_5 = sum(volumes[-5:]) / 5
print(f"5d avg amt: {avg_amt_5/1e8:.1f}B | 20d avg: {avg_amt_20/1e8:.1f}B | ratio: {avg_vol_5/avg_vol_20:.2f}")

# Divergence
print("\n=== DIVERGENCE ===")
for i in range(-10, 0):
    if closes[i] > closes[i-1] and volumes[i] < volumes[i-1]:
        print(f"  {dates[i]}: UP on LOWER vol")
    elif closes[i] < closes[i-1] and volumes[i] > volumes[i-1]:
        print(f"  {dates[i]}: DOWN on HIGHER vol")

# Key levels
print("\n=== KEY LEVELS ===")
print(f"120d High: {max(highs[-120:]):.2f} | 120d Low: {min(lows[-120:]):.2f}")

price_zones = defaultdict(int)
for d in all_daily[-120:]:
    for p in [d["h"], d["l"], d["o"], d["c"]]:
        zone = round(p * 2) / 2
        price_zones[zone] += 1

print("Active zones near current price:")
for zone in sorted(price_zones.keys(), key=lambda x: price_zones[x], reverse=True):
    if abs(zone - current) < 10 and price_zones[zone] >= 10:
        label = "RESIST" if zone > current else ("HERE" if abs(zone-current)<0.5 else "SUPPORT")
        print(f"  Y{zone:.1f}: {price_zones[zone]} touches [{label}]")

# MA alignment
print("\n=== MA ALIGNMENT ===")
ma5_v = sum(closes[-5:])/5
ma10_v = sum(closes[-10:])/10
ma20_v = sum(closes[-20:])/20
ma60_v = sum(closes[-60:])/60
print(f"MA5:{ma5_v:.2f} MA10:{ma10_v:.2f} MA20:{ma20_v:.2f} MA60:{ma60_v:.2f}")
if ma5_v > ma10_v > ma20_v > ma60_v:
    print(">>> BULLISH alignment")
elif ma5_v < ma10_v < ma20_v < ma60_v:
    print(">>> BEARISH alignment")
else:
    print(">>> MIXED")
print(f"  vs MA5: {((current/ma5_v)-1)*100:+.1f}%")
print(f"  vs MA10: {((current/ma10_v)-1)*100:+.1f}%")
print(f"  vs MA20: {((current/ma20_v)-1)*100:+.1f}%")
print(f"  vs MA60: {((current/ma60_v)-1)*100:+.1f}%")

# Weekly
print("\n=== WEEKLY (last 20) ===")
weekly = []
week_data = None
for d in all_daily:
    dt = datetime.datetime.strptime(d["date"], "%Y-%m-%d")
    wk = dt.isocalendar()[1]
    year_week = f"{dt.year}-W{wk:02d}"
    if week_data is None or week_data["year_week"] != year_week:
        if week_data:
            weekly.append(week_data)
        week_data = {"year_week": year_week, "o": d["o"], "h": d["h"], "l": d["l"], "c": d["c"], "v": d["v"], "a": d["a"]}
    else:
        week_data["h"] = max(week_data["h"], d["h"])
        week_data["l"] = min(week_data["l"], d["l"])
        week_data["c"] = d["c"]
        week_data["v"] += d["v"]
        week_data["a"] += d["a"]
if week_data:
    weekly.append(week_data)

wcloses = [w["c"] for w in weekly]
for i in range(max(0, len(weekly)-20), len(weekly)):
    w = weekly[i]
    wma5 = sum(wcloses[i-4:i+1])/5 if i >= 4 else 0
    wma10 = sum(wcloses[i-9:i+1])/10 if i >= 9 else 0
    chg = (w["c"]/weekly[i-1]["c"]-1)*100 if i > 0 else 0
    marker = "+++" if chg > 5 else ("---" if chg < -5 else "")
    print(f"{w['year_week']} O:{w['o']:.2f} H:{w['h']:.2f} L:{w['l']:.2f} C:{w['c']:.2f} Amt:{w['a']/1e8:.1f}B Chg:{chg:+.1f}% WMA5:{wma5:.2f} WMA10:{wma10:.2f} {marker}")

wma5 = sum(wcloses[-5:])/5
wma10 = sum(wcloses[-10:])/10
wma20 = sum(wcloses[-20:])/20
print(f"\nWeekly: WMA5:{wma5:.2f} WMA10:{wma10:.2f} WMA20:{wma20:.2f}")
if wma5 > wma10 > wma20:
    print("WEEKLY BULLISH")
elif wma5 < wma10 < wma20:
    print("WEEKLY BEARISH")
else:
    print("WEEKLY MIXED")

# Buyer zones
print("\n=== BUYER ZONES (big vol + up close) ===")
for i in range(-60, 0):
    d = all_daily[i]
    if d["a"] > avg_amt_20 * 1.8 and d["c"] > d["o"]:
        lw = d["o"] - d["l"]
        body = d["c"] - d["o"]
        shape = "HAMMER" if lw > body * 1.5 else ("ENGULF" if d["c"] > all_daily[i-1]["h"] else "BULL")
        print(f"  {d['date']}: Y{d['c']:.2f} {shape} vol:{d['a']/1e8:.1f}B")

# Seller zones
print("\n=== SELLER ZONES (big vol + down close) ===")
for i in range(-60, 0):
    d = all_daily[i]
    if d["a"] > avg_amt_20 * 1.8 and d["c"] < d["o"]:
        uw = d["h"] - d["o"]
        body = d["o"] - d["c"]
        shape = "SHOOTING_STAR" if uw > body * 1.5 else "DISTRIBUTION"
        print(f"  {d['date']}: Y{d['h']:.2f} high, close Y{d['c']:.2f} {shape} vol:{d['a']/1e8:.1f}B")

# Top volume days
print("\n=== TOP 10 VOLUME DAYS ===")
sorted_days = sorted(all_daily[-120:], key=lambda x: x["a"], reverse=True)[:10]
for d in sorted_days:
    direction = "UP" if d["c"] > d["o"] else "DOWN"
    print(f"  {d['date']}: Y{d['c']:.2f} {direction} chg:{d['chg']:+.2f}% amt:{d['a']/1e8:.1f}B turn:{d['turn']:.1f}%")

# Trend structure
print("\n=== SWING STRUCTURE ===")
swing_highs = []
swing_lows = []
for i in range(5, len(all_daily)-5):
    if highs[i] == max(highs[i-5:i+6]):
        swing_highs.append((dates[i], highs[i]))
    if lows[i] == min(lows[i-5:i+6]):
        swing_lows.append((dates[i], lows[i]))

print("Recent swing highs:")
for date, price in swing_highs[-5:]:
    print(f"  {date}: Y{price:.2f}")
print("Recent swing lows:")
for date, price in swing_lows[-5:]:
    print(f"  {date}: Y{price:.2f}")

if len(swing_highs) >= 2:
    if swing_highs[-1][1] > swing_highs[-2][1]:
        print("Swing highs: HIGHER HIGH (bullish)")
    else:
        print("Swing highs: LOWER HIGH (bearish)")
if len(swing_lows) >= 2:
    if swing_lows[-1][1] > swing_lows[-2][1]:
        print("Swing lows: HIGHER LOW (bullish)")
    else:
        print("Swing lows: LOWER LOW (bearish)")

# Streak
print("\n=== STREAK ===")
streak = 1
st = "up" if closes[-1] > closes[-2] else "down"
for i in range(-2, -30, -1):
    if st == "up" and closes[i] > closes[i-1]:
        streak += 1
    elif st == "down" and closes[i] < closes[i-1]:
        streak += 1
    else:
        break
print(f"Current: {streak} consecutive {st} days")
