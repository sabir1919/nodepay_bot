import aiohttp
import asyncio
import os
from itertools import cycle
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.live import Live

# ------------------ CONFIG ------------------
PING_INTERVAL = 60           # seconds between cycles
REQUEST_TIMEOUT = 30
SUMMARY_INTERVAL = 300       # seconds for auto-summary
BASE_URL = "https://api.nodepay.ai/api"
PING_URL = "https://nw.nodepay.ai/api/network/ping"

console = Console()

# ------------------ SOUND ALERT ------------------
def alert_sound(message="Alert!"):
    # Termux / Linux beep or TTS
    try:
        if os.name == "posix":  # Linux/Android
            os.system(f"termux-tts-speak '{message}' 2>/dev/null || echo '\a'")
        else:
            print("\a")  # fallback beep
    except Exception:
        print("\a")

# ------------------ LOAD TOKENS / PROXIES ------------------
def load_tokens(filename="tokens.txt"):
    if not os.path.exists(filename):
        console.print("[red][!] tokens.txt not found[/red]")
        return []
    with open(filename, "r") as f:
        return [line.strip() for line in f if line.strip()]

def load_proxies(filename="proxies.txt"):
    if not os.path.exists(filename):
        return []
    proxies = []
    with open(filename, "r") as f:
        for line in f:
            proxy = line.strip()
            if not proxy:
                continue
            if "://" not in proxy:
                proxy = "http://" + proxy
            proxies.append(proxy)
    return proxies

# ------------------ ACCOUNT CLASS ------------------
class Account:
    def __init__(self, token, index, proxy=None):
        self.token = token
        self.index = index
        self.proxy = proxy
        self.balance = 0
        self.claimed = 0
        self.last_ping = "N/A"
        self.last_claim_time = "N/A"

# ------------------ API REQUEST ------------------
async def fetch(session, url, token, method="GET", payload=None, proxy=None):
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    try:
        async with session.request(method, url, headers=headers, json=payload,
                                   proxy=proxy, timeout=REQUEST_TIMEOUT) as resp:
            return await resp.json()
    except Exception as e:
        return {"success": False, "error": str(e)}

# ------------------ TASKS ------------------
async def check_rewards(session, account):
    url = f"{BASE_URL}/earn/info"
    data = await fetch(session, url, account.token, proxy=account.proxy)
    if data and data.get("success"):
        account.balance = data.get("data", {}).get("balance", 0)

async def auto_claim(session, account):
    mission_url = f"{BASE_URL}/mission?platform=MOBILE"
    missions = await fetch(session, mission_url, account.token, proxy=account.proxy)
    if not missions or not missions.get("success"):
        alert_sound(f"Account {account.index} failed to fetch missions!")
        return

    claim_url = f"{BASE_URL}/mission/complete-mission"
    claimed_count = 0
    for mission in missions.get("data", []):
        if mission.get("isCompleted") is False:
            payload = {"missionId": mission.get("id"), "platform": "MOBILE"}
            res = await fetch(session, claim_url, account.token, method="POST", payload=payload, proxy=account.proxy)
            if res and res.get("success"):
                claimed_count += 1
            else:
                alert_sound(f"Account {account.index} failed to claim mission {mission.get('title')}")
    account.claimed += claimed_count
    if claimed_count > 0:
        account.last_claim_time = datetime.now().strftime("%H:%M:%S")

async def send_ping(session, account):
    data = await fetch(session, PING_URL, account.token, method="POST", proxy=account.proxy)
    if data and data.get("success"):
        account.last_ping = "✅ OK"
    else:
        account.last_ping = "❌ FAIL"
        alert_sound(f"Account {account.index} ping failed!")

# ------------------ WORKER ------------------
async def worker(account):
    async with aiohttp.ClientSession() as session:
        while True:
            await check_rewards(session, account)
            await auto_claim(session, account)
            await send_ping(session, account)
            await asyncio.sleep(PING_INTERVAL)

# ------------------ DASHBOARD ------------------
def render_table(accounts):
    table = Table(title="🚀 NODEPAY DASHBOARD", expand=True)
    table.add_column("ID", justify="center", style="cyan")
    table.add_column("Balance", justify="center")
    table.add_column("Missions Claimed", justify="center", style="yellow")
    table.add_column("Last Ping", justify="center")
    table.add_column("Last Claim Time", justify="center", style="blue")

    for acc in accounts:
        balance_style = "green" if float(acc.balance) > 50 else "yellow"
        ping_style = "green" if acc.last_ping == "✅ OK" else "red"
        table.add_row(
            str(acc.index),
            f"[{balance_style}]{acc.balance}[/{balance_style}]",
            str(acc.claimed),
            f"[{ping_style}]{acc.last_ping}[/{ping_style}]",
            str(acc.last_claim_time)
        )
    return table

# ------------------ AUTO SUMMARY ------------------
async def auto_summary(accounts):
    while True:
        total_claims = sum(acc.claimed for acc in accounts)
        total_pings = sum(1 for acc in accounts if acc.last_ping == "✅ OK")
        console.print(f"[bold magenta]\n[SUMMARY] Total Claims: [green]{total_claims}[/green], Successful Pings: [green]{total_pings}[/green] at {datetime.now().strftime('%H:%M:%S')}[/bold magenta]")
        await asyncio.sleep(SUMMARY_INTERVAL)

# ------------------ MAIN ------------------
async def main():
    tokens = load_tokens()
    proxies = load_proxies()
    if not tokens:
        return

    proxy_cycle = cycle(proxies) if proxies else None
    accounts = [Account(token, i+1, next(proxy_cycle) if proxy_cycle else None) for i, token in enumerate(tokens)]
    tasks = [asyncio.create_task(worker(acc)) for acc in accounts]
    tasks.append(asyncio.create_task(auto_summary(accounts)))

    with Live(render_table(accounts), refresh_per_second=1, screen=True) as live:
        while True:
            live.update(render_table(accounts))
            await asyncio.sleep(1)

    await asyncio.gather(*tasks)

# ------------------ ENTRY POINT ------------------
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("[red]\n[!] Stopped by user[/red]")
