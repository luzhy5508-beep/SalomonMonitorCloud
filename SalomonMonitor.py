import requests
from bs4 import BeautifulSoup
import json
import os
import time

# 配置信息
MONITOR_URL = "https://www.the-broken-arm.com/en/module/iqitsearch/searchiqit?s=salomon&order=product.id_product.desc"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# 从环境变量获取配置
SERVERJ_SCKEY = os.environ.get("SERVERJ_SCKEY")
KEYWORDS_STR = os.environ.get("KEYWORDS", "XT-6, Speedcross") # 默认关键词
KEYWORDS = [k.strip().lower() for k in KEYWORDS_STR.split(',') if k.strip()]

# 存储已发现商品ID的文件路径
SEEN_IDS_FILE = "seen_ids.json"

def load_seen_ids():
    if os.path.exists(SEEN_IDS_FILE):
        with open(SEEN_IDS_FILE, 'r') as f:
            return set(json.load(f))
    return set()

def save_seen_ids(seen_ids):
    with open(SEEN_IDS_FILE, 'w') as f:
        json.dump(list(seen_ids), f)

def send_serverj_notification(title, desp, product_url):
    if not SERVERJ_SCKEY:
        print("SERVERJ_SCKEY 未设置，跳过通知发送。")
        return

    api_url = f"https://sctapi.ftqq.com/{SERVERJ_SCKEY}.send"
    payload = {
        "title": title,
        "desp": f"{desp}\n\n[点击查看商品]({product_url})"
    }
    try:
        response = requests.post(api_url, data=payload)
        response.raise_for_status()
        print(f"Server酱通知发送成功: {response.json()}")
    except requests.exceptions.RequestException as e:
        print(f"Server酱通知发送失败: {e}")

def main():
    print("开始监测 Salomon 商品上新...")
    seen_ids = load_seen_ids()
    new_products_found = []

    try:
        response = requests.get(MONITOR_URL, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        products = soup.select(".product-miniature")

        current_product_ids = set()
        for product in products:
            product_id = product.get('data-id-product')
            product_name_elem = product.select_one(".product-title")
            product_link_elem = product.select_one("a")

            if not product_id or not product_name_elem or not product_link_elem:
                continue

            product_name = product_name_elem.get_text(strip=True)
            product_link = product_link_elem['href']
            current_product_ids.add(product_id)

            if product_id not in seen_ids:
                # 检查关键词
                if any(keyword in product_name.lower() for keyword in KEYWORDS):
                    new_products_found.append({
                        "id": product_id,
                        "name": product_name,
                        "link": product_link
                    })
                    seen_ids.add(product_id) # 立即添加到seen_ids，避免重复通知

        if new_products_found:
            print(f"发现 {len(new_products_found)} 个新商品！")
            for p in new_products_found:
                title = f"Salomon 新商品: {p['name']}"
                desp = f"商品名称: {p['name']}\n商品链接: {p['link']}"
                send_serverj_notification(title, desp, p['link'])
                time.sleep(1) # 避免API请求过快
        else:
            print("未发现符合关键词的新商品。")

        # 更新 seen_ids 文件，只保留当前页面上的商品ID，避免文件过大
        # 考虑到网站可能下架商品，这里只添加新的，不移除旧的，以防止已下架商品再次上架时被误报为新商品
        # 更严谨的做法是维护一个长期列表，但对于 demo 而言，当前逻辑足够
        save_seen_ids(seen_ids)

    except requests.exceptions.RequestException as e:
        print(f"网络请求失败: {e}")
    except Exception as e:
        print(f"发生错误: {e}")

    print("监测结束。")

if __name__ == "__main__":
    main()
