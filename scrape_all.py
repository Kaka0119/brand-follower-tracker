"""
GitHub Action: 珠宝品牌社交平台粉丝数采集脚本 v2
在 GitHub Actions (海外 runner) 上自动抓取 Instagram/Facebook 粉丝数

v2: 修复 Instagram/Facebook 抓取逻辑
- 从 og:description 中提取粉丝数（即使被重定向到登录页，meta 标签也包含数据）
- Facebook 需要从页面的结构化数据中提取
"""
import asyncio
import json
import re
import os
from datetime import datetime

# ===== 品牌配置 =====
BRANDS = [
    ("Mindjewel", "mindjewel.co", "mindjewel.co", "61584065908446"),
    ("Tiffany & Co.", "tiffanyandco", "tiffanyandco", "Tiffany"),
    ("Cartier", "cartier", "cartier", "Cartier"),
    ("Bulgari", "bvlgari", "bvlgari", "Bulgari"),
    ("Van Cleef & Arpels", "vancleefarpels", "vancleefarpels", "vancleef.arpels"),
    ("David Yurman", "davidyurman", "davidyurman", "DavidYurman"),
    ("Monica Vinader", "monicavinader", "monicavinader", "MonicaVinader"),
    ("Stone and Strand", "stoneandstrand", "stoneandstrand", "STONEANDSTRAND"),
    ("Mejuri", "mejuri", "mejuri", "mejuri"),
    ("HEFANG", "hefangjewelry", "hefang_jewelry", "61563959996240"),
    ("Pandora", "pandoralasvegas", "theofficialpandora", "PandoraJewelry"),
    ("Ana Luisa", "analuisany", "analuisany", ""),
    ("Catbird", "catbird.nyc", "catbirdnyc", "catbirdnyc"),
    ("Jeulia", "jeuliajewelry_shop", "jeuliajewelry", "JeuliaJewelry"),
    ("Kendra Scott", "kendrascott", "kendrascott", "KendraScott"),
]

OUTPUT_DIR = "data"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "brand_followers.json")
HISTORY_DIR = os.path.join(OUTPUT_DIR, "history")


def parse_count(text):
    if not text:
        return None
    text = str(text).strip().replace(",", "")
    if text[-1].upper() == "M":
        try:
            return int(float(text[:-1]) * 1000000)
        except:
            pass
    elif text[-1].upper() == "K":
        try:
            return int(float(text[:-1]) * 1000)
        except:
            pass
    try:
        return int(text)
    except:
        return None


def fmt(n):
    if n is None or n == "N/A":
        return "N/A"
    n = int(n)
    if n >= 10000000:
        return f"{n//1000000}M"
    elif n >= 1000000:
        return f"{n/1000000:.1f}M"
    elif n >= 10000:
        return f"{n//10000}w"
    elif n >= 1000:
        return f"{n/1000:.1f}k"
    return str(n)


# ============ TikTok Scraper ============
async def fetch_tiktok(session, handle):
    url = f"https://www.tiktok.com/@{handle}"
    try:
        page = await session.fetch(url, timeout=20000)
        html = page.html_content
        m = re.search(r'"followerCount":(\d+)', html[:200000])
        if m:
            return int(m.group(1))
        rm = re.search(
            r'<script[^>]*id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(.*?)</script>',
            html, re.DOTALL
        )
        if rm:
            fm = re.search(r'"followerCount":(\d+)', rm.group(1))
            if fm:
                return int(fm.group(1))
        return None
    except Exception as e:
        print(f"    TT @{handle} error: {e}")
        return None


# ============ Instagram Scraper ============
async def fetch_instagram(session, handle):
    """
    Instagram forces login for all profile pages now.
    But the og:description meta tag in the login page still contains 
    the follower count from the original profile.
    Example: "2 Followers, 0 Following, 0 Posts - See Instagram photos and videos from Mindjewel (@mindjewel.co)"
    """
    url = f"https://www.instagram.com/{handle}/"
    try:
        page = await session.fetch(url, timeout=20000)
        html = page.html_content

        # Instagram login page still returns meta tags with profile info
        # Try meta name="description" first
        m = re.search(
            r'<meta[^>]*name="description"[^>]*content="([^"]+)"', html
        )
        if m:
            desc = m.group(1)
            # Pattern: "2 Followers, 0 Following, 0 Posts - See Instagram photos and videos from Mindjewel (@mindjewel.co)"
            fm = re.search(
                r"(\d+[.,\d]*(?:K|M|B)?)\s*(?:Follower|follower)", desc
            )
            if fm:
                result = parse_count(fm.group(1))
                if result:
                    return result
        
        # Try og:description
        m2 = re.search(
            r'<meta[^>]*property="og:description"[^>]*content="([^"]+)"', html
        )
        if m2:
            desc = m2.group(1)
            fm = re.search(
                r"(\d+[.,\d]*(?:K|M|B)?)\s*(?:Follower|follower)", desc
            )
            if fm:
                result = parse_count(fm.group(1))
                if result:
                    return result
            
            # Sometimes just the raw number
            fm2 = re.search(r"(\d+[.,\d]+)", desc)
            if fm2:
                return parse_count(fm2.group(1))

        return None
    except Exception as e:
        print(f"    IG @{handle} error: {e}")
        return None


# ============ Facebook Scraper ============
async def fetch_facebook(session, handle):
    if not handle:
        return None
    url = f"https://www.facebook.com/{handle}"
    try:
        page = await session.fetch(url, timeout=20000)
        html = page.html_content

        # Try JSON-LD structured data
        for p in [
            r'"fan_count":(\d+)',
            r'"follower_count":(\d+)',
            r'"page_fans":(\d+)',
        ]:
            m = re.search(p, html[:150000])
            if m:
                return int(m.group(1))

        # Try meta description (FB uses format: "XXX likes · YYY talking")
        m = re.search(
            r'<meta[^>]*name="description"[^>]*content="([^"]+)"', html
        )
        if m:
            desc = m.group(1)
            print(f"      FB desc: {desc[:120]}")
            # FB format: "Tiffany & Co. 10,373,775 likes · 46,769 talking about this."
            fm = re.search(
                r"(\d+[.,\d]*(?:K|M|B)?)\s*(?:likes|followers?|people follow this)",
                desc, re.IGNORECASE
            )
            if fm:
                result = parse_count(fm.group(1))
                if result:
                    print(f"      => {result:,} likes")
                    return result
            # Try OG:description as fallback
            
        # Try og:description as second fallback  
        m2 = re.search(
            r'<meta[^>]*property="og:description"[^>]*content="([^"]+)"', html
        )
        if m2:
            desc = m2.group(1)
            fm = re.search(
                r"(\d+[.,\d]*(?:K|M|B)?)\s*(?:likes|followers?|people follow this)",
                desc, re.IGNORECASE
            )
            if fm:
                return parse_count(fm.group(1))

        return None
    except Exception as e:
        print(f"    FB {handle} error: {e}")
        return None


async def main():
    from scrapling.fetchers import AsyncStealthySession

    os.makedirs(HISTORY_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    date_tag = datetime.now().strftime("%Y%m%d_%H%M%S")

    results = {}

    # ===== TikTok =====
    print("\n===== TikTok =====")
    async with AsyncStealthySession(headless=True, timeout=20000, max_pages=3) as session:
        for brand_name, tt_h, _, _ in BRANDS:
            print(f"  @{tt_h}...", end=" ", flush=True)
            val = await fetch_tiktok(session, tt_h)
            results[brand_name] = {"TikTok": val if val else "N/A", "Instagram": "N/A", "Facebook": "N/A"}
            if val:
                print(f"✅ {val:,}")
            else:
                print("❌")
            await asyncio.sleep(0.5)

    # ===== Instagram =====
    print("\n===== Instagram =====")
    async with AsyncStealthySession(headless=True, timeout=20000, max_pages=2) as session:
        for brand_name, _, ig_h, _ in BRANDS:
            print(f"  @{ig_h}...", end=" ", flush=True)
            val = await fetch_instagram(session, ig_h)
            if val:
                results[brand_name]["Instagram"] = val
                print(f"✅ {val:,}")
            else:
                print("❌")
            await asyncio.sleep(0.5)

    # ===== Facebook =====
    print("\n===== Facebook =====")
    async with AsyncStealthySession(headless=True, timeout=20000, max_pages=2) as session:
        for brand_name, _, _, fb_h in BRANDS:
            print(f"  {fb_h or '(empty)'}...", end=" ", flush=True)
            if not fb_h:
                print("(no handle)")
                continue
            val = await fetch_facebook(session, fb_h)
            if val:
                results[brand_name]["Facebook"] = val
                print(f"✅ {val:,}")
            else:
                print("❌")
            await asyncio.sleep(0.5)

    # ===== 生成输出 =====
    output = {
        "采集时间": timestamp,
        "数据": results,
    }

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    history_file = os.path.join(HISTORY_DIR, f"brand_followers_{date_tag}.json")
    with open(history_file, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    # ===== 输出表格 =====
    print("\n" + "=" * 90)
    print(f"{'品牌':22s} {'TikTok':16s} {'Instagram':16s} {'Facebook':16s}")
    print("=" * 90)
    for brand_name, _, _, _ in BRANDS:
        r = results[brand_name]
        print(
            f"{brand_name:22s} {fmt(r['TikTok']):>16s} {fmt(r['Instagram']):>16s} {fmt(r['Facebook']):>16s}"
        )

    print(f"\n✅ 数据已保存: {OUTPUT_FILE}")
    print(f"   历史存档: {history_file}")


if __name__ == "__main__":
    asyncio.run(main())
