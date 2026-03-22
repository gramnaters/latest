#!/usr/bin/env python3
"""
Scan working_sites.txt with one card and report per-site CAPTCHA/result.
Usage: python3 scan_sites.py [--proxy host:port:user:pass] [--workers N]
"""
import sys, os, time, argparse, concurrent.futures, threading
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import neww as checkout

CARD = {'number':'5136070130579948','month':1,'year':2027,'verification_value':'831','name':'Test Card'}
TEST_CARD_STR = "5136070130579948|01|27|831"

results = []
lock = threading.Lock()

STATUS_ICON = {
    'charged':  '💎',
    'approved': '✅',
    'declined': '❌',
    'captcha':  '⚠️ CAPTCHA',
    'unknown':  '❓',
}

def check_site(site, proxy_mapping):
    t0 = time.time()
    try:
        from bott import check_single_card
        status, code, amount, site_label, used_proxy, shop_url, receipt = check_single_card(
            CARD, [site], proxy_mapping
        )
    except Exception as e:
        status, code = 'unknown', str(e)[:60]
        elapsed = time.time() - t0
        return site, status, code, elapsed

    elapsed = time.time() - t0
    return site, status, code, elapsed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--proxy', default=None, help='host:port:user:pass')
    parser.add_argument('--workers', type=int, default=20)
    parser.add_argument('--sites', default='working_sites.txt')
    args = parser.parse_args()

    sites = checkout.read_sites_from_file(args.sites)
    if not sites:
        print(f"No sites in {args.sites}")
        return

    proxy_mapping = None
    if args.proxy:
        from bott import normalize_proxy_url
        n = normalize_proxy_url(args.proxy)
        if n:
            proxy_mapping = {'http': n, 'https': n}
            print(f"Proxy: {n}")
        else:
            print(f"Invalid proxy format: {args.proxy}")

    print(f"\nCard: {TEST_CARD_STR}")
    print(f"Sites: {len(sites)}")
    print(f"Workers: {args.workers}")
    print(f"{'='*100}")
    print(f"{'RESULT':16s} | {'SITE':50s} | {'CODE':40s} | TIME")
    print(f"{'='*100}")

    captcha_sites = []
    working_sites = []   # approved/charged/declined (not captcha)
    unknown_sites = []

    start = time.time()

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(check_site, s, proxy_mapping): s for s in sites}
        done = 0
        for fut in concurrent.futures.as_completed(futs):
            site, status, code, elapsed = fut.result()
            done += 1
            icon = STATUS_ICON.get(status, '❓')
            code_short = (code or '').replace('"', '').replace('code: ','')[:40]
            print(f"{icon:16s} | {site:50s} | {code_short:40s} | {elapsed:.1f}s  [{done}/{len(sites)}]")
            if status == 'captcha':
                captcha_sites.append(site)
            elif status in ('approved', 'charged', 'declined'):
                working_sites.append((site, status, code))
            else:
                unknown_sites.append((site, code))

    total_elapsed = time.time() - start
    print(f"\n{'='*100}")
    print(f"\n📊 SCAN SUMMARY — {TEST_CARD_STR}")
    print(f"{'='*100}")
    print(f"Total sites scanned : {len(sites)}")
    print(f"Total time          : {total_elapsed:.1f}s")
    print()
    print(f"✅/❌/💎 Working (non-CAPTCHA) : {len(working_sites)}")
    print(f"⚠️  CAPTCHA sites              : {len(captcha_sites)}")
    print(f"❓  Unknown/error              : {len(unknown_sites)}")

    if working_sites:
        print(f"\n--- NON-CAPTCHA SITES ({len(working_sites)}) ---")
        for s, st, cd in working_sites:
            icon = STATUS_ICON.get(st, '❓')
            cd_short = (cd or '').replace('"', '').replace('code: ','')[:60]
            print(f"  {icon} {s}  |  {cd_short}")

    if captcha_sites:
        print(f"\n--- CAPTCHA SITES ({len(captcha_sites)}) ---")
        for s in captcha_sites:
            print(f"  ⚠️  {s}")

    if unknown_sites:
        print(f"\n--- UNKNOWN/ERROR ({len(unknown_sites)}) ---")
        for s, cd in unknown_sites[:20]:
            print(f"  ❓ {s}  |  {(cd or '')[:60]}")


if __name__ == '__main__':
    main()
