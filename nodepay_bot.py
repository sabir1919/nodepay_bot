import time
import random
import cloudscraper
from colorama import Fore, Style, init

init(autoreset=True)

class NodePayBot:
    def __init__(self, token, proxy=None):
        self.token = token.strip()
        self.proxy = proxy.strip() if proxy else None
        self.session = cloudscraper.create_scraper()
        self.base_api = "https://api.nodepay.ai/api"
        self.headers = {
            "User-Agent": self.random_user_agent(),
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://nodepay.ai/",
            "Origin": "https://nodepay.ai",
            "Accept-Language": "en-US,en;q=0.9",
            "Authorization": f"Bearer {self.token}",
            "Connection": "keep-alive"
        }
        if self.proxy:
            self.session.proxies.update({"http": self.proxy, "https": self.proxy})

    def random_user_agent(self):
        ua_list = [
            # Mobile Chrome
            "Mozilla/5.0 (Linux; Android 12; Pixel 5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.6045.134 Mobile Safari/537.36",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 16_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile Safari/604.1",
            # Firefox Mobile
            "Mozilla/5.0 (Android 11; Mobile; rv:109.0) Gecko/109.0 Firefox/109.0",
        ]
        return random.choice(ua_list)

    def get_info(self):
        try:
            r = self.session.get(f"{self.base_api}/earn/info", headers=self.headers, timeout=15)
            if r.status_code == 200:
                return r.json()
            else:
                return {"error": f"Status {r.status_code}: {r.text}"}
        except Exception as e:
            return {"error": str(e)}

    def claim(self):
        try:
            r = self.session.post(f"{self.base_api}/earn/claim", headers=self.headers, timeout=15)
            if r.status_code == 200:
                return r.json()
            else:
                return {"error": f"Status {r.status_code}: {r.text}"}
        except Exception as e:
            return {"error": str(e)}


def load_list(filename):
    try:
        with open(filename, "r") as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        return []


def main():
    tokens = load_list("tokens.txt")
    proxies = load_list("proxies.txt")

    if not tokens:
        print(Fore.RED + "[-] No tokens found in tokens.txt")
        return

    for i, token in enumerate(tokens, start=1):
        proxy = random.choice(proxies) if proxies else None
        bot = NodePayBot(token, proxy)

        print(Fore.CYAN + f"\n=== Account {i} ===")
        if proxy:
            print(Fore.YELLOW + f"[Proxy] {proxy}")

        info = bot.get_info()
        if "error" in info:
            print(Fore.RED + f"[Error] {info['error']}")
            continue

        balance = info.get("balance", 0)
        print(Fore.GREEN + f"[Balance] {balance}")

        claim = bot.claim()
        if "error" in claim:
            print(Fore.RED + f"[Claim Error] {claim['error']}")
        else:
            print(Fore.MAGENTA + f"[Claimed] {claim}")


if __name__ == "__main__":
    main()
