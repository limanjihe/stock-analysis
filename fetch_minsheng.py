import os
for k in list(os.environ.keys()):
    kl = k.lower()
    if 'proxy' in kl:
        del os.environ[k]

os.environ['no_proxy'] = '*'
os.environ['NO_PROXY'] = '*'

import requests, json

session = requests.Session()
session.trust_env = False

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'https://quote.eastmoney.com/',
}

no_proxy = {'http': None, 'https': None}

# 民生银行
stocks = {
    '600016': '1.600016',
    '600036': '1.600036',  # 招行
    '601398': '1.601398',  # 工行
    '601166': '1.601166',  # 兴业
}

for code, secid in stocks.items():
    url = f'http://82.push2.eastmoney.com/api/qt/stock/get'
    params = {
        'secid': secid,
        'fields': 'f43,f44,f45,f46,f47,f48,f50,f51,f52,f55,f57,f58,f60,f116,f117,f162,f167,f168,f169,f170,f173,f177,f183,f184,f185',
    }
    try:
        r = session.get(url, params=params, headers=headers, timeout=10, proxies=no_proxy)
        data = r.json()
        d = data.get('data', {})
        print(f"=== {code} ===")
        print(json.dumps(d, indent=2, ensure_ascii=False))
        print()
    except Exception as e:
        print(f"=== {code} FAILED: {e} ===")
        print()

# K线数据 - 民生银行近60日
try:
    kline_url = 'http://push2his.eastmoney.com/api/qt/stock/kline/get'
    kline_params = {
        'secid': '1.600016',
        'fields1': 'f1,f2,f3,f4,f5,f6',
        'fields2': 'f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61',
        'klt': '101',  # 日K
        'fqt': '1',    # 前复权
        'beg': '20260301',
        'end': '20260527',
        'lmt': '60',
    }
    r = session.get(kline_url, params=kline_params, headers=headers, timeout=10, proxies=no_proxy)
    kdata = r.json()
    klines = kdata.get('data', {}).get('klines', [])
    print("=== 民生银行 近期K线 ===")
    for k in klines[-20:]:
        print(k)
except Exception as e:
    print(f"K线获取失败: {e}")
