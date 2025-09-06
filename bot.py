import asyncio
import websockets
import json
import random
import time
import requests
from colorama import Fore, init

init(autoreset=True)

API_BASE = "https://api.nodepay.ai/api"
WS_URL = "wss://nw.nodepay.ai/api/network/ping"

# Interval between claim cycles (seconds) → 1800 = 30 minutes
CLAIM_INTERVAL = 1800  

class NodePayBot:
    def __init__(self, token, proxy=None):
        self.token = token.strip()
        self.proxy = proxy
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 13; Pixel 7 Pro) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/122.0 Mobile Safari/537.36",
            "Authorization": f"Bearer {self.token}"
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        if proxy:
            self.session.proxies.update({"http": proxy, "https": proxy})

    def get_info(self):
        try:
            r = self.session.get(f"{API_BASE}/earn/info", timeout=15)
            return r.json() if r.status_code == 200 else {"error": r.text}
        except Exception as e:
            return {"error": str(e)}

    def claim(self):
        try:
            r = self.session.post(f"{API_BASE}/earn/claim", timeout=15)
            return r.json() if r.status_code == 200 else {"error": r.text}
        except Exception as e:
            return {"error": str(e)}

    def missions(self):
        try:
            r = self.session.get(f"{API_BASE}/mission?platform=MOBILE", timeout=15)
            return r.json() if r.status_code == 200 else {"error": r.text}
        except Exception as e:
            return {"error": str(e)}

    async def ping_loop(self, duration=60):
        try:
            async with websockets.connect(WS_URL, extra_headers=self.headers) as ws:
                start = time.time()
                while time.time() - start < duration:
                    msg = {"type": "ping", "id": random.randint(1000, 9999)}
                    await ws.send(json.dumps(msg))
                    print(Fore.GREEN + f"[Ping Sent] {msg}")

                    try:
                        reply = await asyncio.wait_for(ws.recv(), timeout=5)
                        print(Fore.YELLOW + f"[Reply] {reply}")
                    except asyncio.TimeoutError:
                        print(Fore.RED + "[!] No reply to ping")

                    await asyncio.sleep(10)
        except Exception as e:
            print(Fore.RED + f"[Ping Error] {e}")


def load_list(filename):
    try:
        with open(filename, "r") as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        return []


async def run_bot(token, proxy, acc_id):
    bot = NodePayBot(token, proxy)
    while True:
        print(Fore.CYAN + f"\n=== Account {acc_id} ===")
        if proxy:
            print(Fore.YELLOW + f"[Proxy] {proxy}")

        # Balance
        info = bot.get_info()
        if "error" in info:
            print(Fore.RED + f"[Error] {info['error']}")
        else:
            balance = info.get("balance", 0)
            print(Fore.GREEN + f"[Balance] {balance}")

        # Claim
        claim = bot.claim()
        if "error" in claim:
            print(Fore.RED + f"[Claim Error] {claim['error']}")
        else:
            print(Fore.MAGENTA + f"[Claimed] {claim}")

        # Missions
        missions = bot.missions()
        if "error" in missions:
            print(Fore.RED + f"[Missions Error] {missions['error']}")
        else:
            print(Fore.CYAN + f"[Missions] {missions}")

        # WebSocket ping loop
        await bot.ping_loop(duration=60)

        # Wait before next cycle
        print(Fore.BLUE + f"[Sleep] Waiting {CLAIM_INTERVAL // 60} minutes...")
        await asyncio.sleep(CLAIM_INTERVAL)


async def main():
    tokens = load_list("tokens.txt")
    proxies = load_list("proxies.txt")

    if not tokens:
        print(Fore.RED + "[-] No tokens found in tokens.txt")
        return

    tasks = []
    for i, token in enumerate(tokens, start=1):
        proxy = random.choice(proxies) if proxies else None
        tasks.append(asyncio.create_task(run_bot(token, proxy, i)))

    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
