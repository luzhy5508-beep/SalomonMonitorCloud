import requests
from bs4 import BeautifulSoup
import json
import os
import time
from datetime import datetime

# 配置信息
MONITOR_URL = "https://www.the-broken-arm.com/en/module/iqitsearch/searchiqit?s=salomon&order=product.id_product.desc"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64 ) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# 从环境变量获取配置
SERVERJ_SCKEY = os.environ.get("SERVERJ_SCKEY")
KEYWORDS_STR = os.environ.get("KEYWORDS", "rier") # 默认关键词
KEYWORDS = [k.strip().lower() for k in KEYWORDS_STR.split(',') if k.strip()]

# 存储已发现商品ID的文件路径
SEEN_IDS_FILE = "seen_ids.json"

def load_seen_ids():
    """加载已见过的商品 ID"""
    if os.path.exists(SEEN_IDS_FILE):
        try:
            with open(SEEN_IDS_FILE, 'r') as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return set(data.get("product_ids", []))
                else:
                    return set(data)
        except Exception as e:
            print(f"加载 seen_ids 文件出错: {e}，将创建新文件")
            return set()
    return set()

def save_seen_ids(seen_ids):
    """保存已见过的商品 ID"""
    try:
        with open(SEEN_IDS_FILE, 'w') as f:
            json.dump({
                "product_ids": list(seen_ids),
                "last_updated": datetime.now().isoformat()
            }, f, indent=2)
    except Exception as e:
        print(f"保存 seen_ids 文件出错: {e}")

def send_serverj_notification(title, desp, product_url):
    """通过 Server酱发送微信通知"""
    if not SERVERJ_SCKEY:
        print("SERVERJ_SCKEY 未设置，跳过通知发送。")
        return False

    api_url = f"https://sctapi.ftqq.com/{SERVERJ_SCKEY}.send"
    payload = {
        "title": title,
        "desp": f"{desp}\n\n[点击查看商品]({product_url} )"
    }
    try:
        response = requests.post(api_url, data=payload, timeout=10)
        response.raise_for_status()
        result = response.json()
        if result.get("code") == 0:
            print(f"✓ Server酱通知发送成功: {title}")
            return True
        else:
            print(f"✗ Server酱通知发送失败: {result.get('message', '未知错误')}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"✗ Server酱通知发送异常: {e}")
        return False

def main():
    print(f"\n{'='*60}")
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 开始监测 Salomon 商品上新...")
    print(f"监测关键词: {', '.join(KEYWORDS)}")
    print(f"{'='*60}\n")
    
    seen_ids = load_seen_ids()
    print(f"已记录的商品数: {len(seen_ids)}")
    
    new_products_found = []

    try:
        response = requests.get(MONITOR_URL, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        products = soup.select(".product-miniature")

        print(f"当前页面商品总数: {len(products)}\n")

        for idx, product in enumerate(products, 1):
            product_id = product.get('data-id-product')
            product_name_elem = product.select_one(".product-title")
            product_link_elem = product.select_one("a")

            if not product_id or not product_name_elem or not product_link_elem:
                continue

            product_name = product_name_elem.get_text(strip=True)
            product_link = product_link_elem['href']

            # 检查是否是新商品
            if product_id not in seen_ids:
                # 检查关键词匹配
                if any(keyword in product_name.lower() for keyword in KEYWORDS):
                    new_products_found.append({
                        "id": product_id,
                        "name": product_name,
                        "link": product_link
                    })
                    print(f"[新商品] #{idx} ID:{product_id} | {product_name[:50]}")
                else:
                    print(f"[已有] #{idx} ID:{product_id} | {product_name[:50]} (不匹配关键词)")
                
                # 立即添加到 seen_ids，避免重复通知
                seen_ids.add(product_id)
            else:
                print(f"[已记录] #{idx} ID:{product_id} | {product_name[:50]}")

        print(f"\n{'='*60}")
        if new_products_found:
            print(f"发现 {len(new_products_found)} 个新商品！")
            print(f"{'='*60}\n")
            for p in new_products_found:
                title = f"🎉 Salomon 新商品: {p['name'][:30]}"
                desp = f"商品名称: {p['name']}\n\n商品 ID: {p['id']}"
                send_serverj_notification(title, desp, p['link'])
                time.sleep(1)
        else:
            print("未发现新的符合关键词的商品。")
            print(f"{'='*60}\n")

        # 保存更新后的 seen_ids
        save_seen_ids(seen_ids)
        print(f"已保存 {len(seen_ids)} 个商品记录。")

    except requests.exceptions.RequestException as e:
        print(f"✗ 网络请求失败: {e}")
    except Exception as e:
        print(f"✗ 发生错误: {e}")

    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 监测结束。\n")

if __name__ == "__main__":
    main()
