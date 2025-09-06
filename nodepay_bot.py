import time
import random
import cloudscraper
from colorama import Fore, init

init(autoreset=True)

class NodePayBot:
    def __init__(self, token, proxy=None):
        self.token = token.strip()
        self.proxy = proxy.strip() if proxy else None
        self.session = cloudscraper.create_scraper()
        self.api = "https://api.nodepay.ai/api"
        self.net_api = "https://nw.nodepay.ai/api"
        self.headers = self.make_headers()
        if self.proxy:
            self.session.proxies.update({"http": self.proxy, "https": self.proxy})

    def make_headers(self):
        ua_list = [
            # Realistic mobile browsers
            "Mozilla/5.0 (Linux; Android 13; Pixel 7 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0 Mobile Safari/537.36",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile Safari/604.1",
        ]
        return {
            "User-Agent": random.choice(ua_list),
            "Accept": "application/json, text/plain, */*",
            "Origin": "https://app.nodepay.ai",
            "Referer": "https://app.nodepay.ai/",
            "Authorization": f"Bearer {self.token}",
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "keep-alive"
        }

    def get_info(self):
        try:
            r = self.session.get(f"{self.api}/earn/info", headers=self.headers, timeout=20)
            return r.json() if r.status_code == 200 else {"error": f"{r.status_code} {r.text}"}
        except Exception as e:
            return {"error": str(e)}

    def ping(self):
        try:
            r = self.session.post(f"{self.net_api}/network/ping", headers=self.headers, timeout=20)
            return r.json() if r.status_code == 200 else {"error": f"{r.status_code} {r.text}"}
        except Exception as e:
            return {"error": str(e)}

    def missions(self):
        try:
            r = self.session.get(f"{self.api}/mission?platform=MOBILE", headers=self.headers, timeout=20)
            if r.status_code != 200:
                return {"error": f"{r.status_code} {r.text}"}
            missions = r.json().get("data", [])
            results = []
            for m in missions:
                mid = m.get("_id")
                if not mid:
                    continue
                claim = self.session.post(f"{self.api}/mission/complete-mission",
                                          headers=self.headers,
                                          json={"mission_id": mid}, timeout=20)
                if claim.status_code == 200:
                    results.append({"mission": mid, "status": "claimed"})
            return results
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
            print(Fore.RED + f"[Info Error] {info['error']}")
            continue
        balance = info.get("balance", 0)
        print(Fore.GREEN + f"[Balance] {balance}")

        ping = bot.ping()
        if "error" in ping:
            print(Fore.RED + f"[Ping Error] {ping['error']}")
        else:
            print(Fore.GREEN + "[Ping] Success ✅")

        missions = bot.missions()
        if isinstance(missions, list) and missions:
            print(Fore.MAGENTA + f"[Missions] Claimed {len(missions)}")
        else:
            print(Fore.YELLOW + "[Missions] None available")


if __name__ == "__main__":
    main()
