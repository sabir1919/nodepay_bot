import os
import sys
import time
import asyncio
import aiohttp
from aiohttp import ClientSession
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich import box
from rich.panel import Panel

# ------------------ CONFIG ------------------
PING_INTERVAL = 60
REQUEST_TIMEOUT = 30
SUMMARY_INTERVAL = 300
RETRY_DELAY = 15
DEBUG = True   # 👈 Enable debug logging

# ------------------ CONSTANTS ------------------
SESSION_ENDPOINT = "https://api.nodepay.ai/api/auth/session"
PING_ENDPOINT = "https://nw.nodepay.ai/api/network/ping"
BALANCE_ENDPOINT = "https://api.nodepay.ai/api/earn/info"
MISSION_ENDPOINT = "https://api.nodepay.ai/api/mission?platform=MOBILE"
CLAIM_ENDPOINT = "https://api.nodepay.ai/api/mission/complete-mission"

console = Console()

# ------------------ CLASSES ------------------
class AccountState:
    def __init__(self, index, token, proxy=None):
        self.index = index
        self.token = token
        self.proxy = proxy
        self.balance = 0
        self.missions_claimed = 0
        self.last_ping = "N/A"
        self.last_claim = "N/A"
        self.last_error = "None"

# ------------------ UTILS ------------------
def alert_sound(msg):
    console.print(f"[bold red]{msg}[/bold red]")
    sys.stdout.write("\a")
    sys.stdout.flush()

def load_tokens():
    if not os.path.exists("tokens.txt"):
        console.print("[red][!] tokens.txt not found[/red]")
        sys.exit(1)
    with open("tokens.txt") as f:
        return [line.strip() for line in f if line.strip()]

def load_proxies():
    if not os.path.exists("proxies.txt"):
        return []
    with open("proxies.txt") as f:
        return [line.strip() for line in f if line.strip()]

async def fetch(session, url, token, method="GET", payload=None, proxy=None, account=None):
    while True:
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        try:
            async with session.request(method, url, headers=headers, json=payload, proxy=proxy, timeout=REQUEST_TIMEOUT) as resp:
                try:
                    data = await resp.json()
                except Exception:
                    text = await resp.text()
                    data = {"error": f"Non-JSON response: {text}"}

                if DEBUG:
                    console.print(f"[yellow][DEBUG][/yellow] [cyan]URL:[/cyan] {url}\n[cyan]Response:[/cyan] {data}")

                if resp.status == 401:
                    account.last_error = "❌ Invalid/Expired Token"
                    return None

                account.last_error = "None"
                return data

        except Exception as e:
            account.last_error = str(e)
            account.last_ping = "❌ FAIL"
            alert_sound(f"Account {account.index} request failed, retrying in {RETRY_DELAY}s...")
            await asyncio.sleep(RETRY_DELAY)

async def check_balance(session, account):
    data = await fetch(session, BALANCE_ENDPOINT, account.token, account=account, proxy=account.proxy)
    if data and "data" in data:
        account.balance = data["data"].get("balance", 0)

async def claim_missions(session, account):
    missions = await fetch(session, MISSION_ENDPOINT, account.token, account=account, proxy=account.proxy)
    if missions and "data" in missions:
        for m in missions["data"]:
            if not m.get("is_claimed", True):
                payload = {"mission_id": m["id"]}
                res = await fetch(session, CLAIM_ENDPOINT, account.token, method="POST", payload=payload, account=account, proxy=account.proxy)
                if res and res.get("success"):
                    account.missions_claimed += 1
                    account.last_claim = datetime.now().strftime("%H:%M:%S")
                    console.print(f"[green][✓] Account {account.index} claimed mission {m['title']}[/green]")

async def send_ping(session, account):
    res = await fetch(session, PING_ENDPOINT, account.token, method="POST", payload={"timestamp": int(time.time())}, account=account, proxy=account.proxy)
    if res and res.get("success"):
        account.last_ping = datetime.now().strftime("%H:%M:%S")

async def worker(account):
    async with ClientSession() as session:
        while True:
            try:
                await check_balance(session, account)
                await claim_missions(session, account)
                await send_ping(session, account)
            except Exception as e:
                account.last_error = str(e)
            await asyncio.sleep(PING_INTERVAL)

async def dashboard(accounts):
    while True:
        table = Table(title="Nodepay Bot Dashboard", box=box.DOUBLE_EDGE, style="bold blue")
        table.add_column("ID", justify="center")
        table.add_column("Balance", justify="center")
        table.add_column("Missions Claimed", justify="center")
        table.add_column("Last Ping", justify="center")
        table.add_column("Last Claim Time", justify="center")
        table.add_column("Last Error", justify="center", style="red")

        for acc in accounts:
            table.add_row(str(acc.index), str(acc.balance), str(acc.missions_claimed),
                          acc.last_ping, acc.last_claim, acc.last_error)

        console.clear()
        console.print(Panel(table, title="[bold cyan]Nodepay Auto Bot[/bold cyan]", border_style="bright_magenta"))
        await asyncio.sleep(SUMMARY_INTERVAL)

async def main():
    console.print("[bold cyan]Nodepay Bot Starting...[/bold cyan]")

    tokens = load_tokens()
    proxies = load_proxies()

    # ------------------ MENU ------------------
    console.print("\n[bold yellow]Select Run Mode:[/bold yellow]")
    console.print("[cyan]1)[/cyan] Run with proxies")
    console.print("[cyan]2)[/cyan] Run without proxies")
    choice = input("[bold green]Enter choice (1/2): [/bold green] ")

    accounts = []
    if choice == "1" and proxies:
        console.print(f"[yellow]Loaded {len(proxies)} proxies[/yellow]")
        for i, token in enumerate(tokens, 1):
            proxy = proxies[(i - 1) % len(proxies)]
            accounts.append(AccountState(i, token, proxy))
    else:
        console.print("[yellow]Running without proxies[/yellow]")
        for i, token in enumerate(tokens, 1):
            accounts.append(AccountState(i, token))

    # ✅ Validate tokens first
    console.print("[bold cyan]Validating tokens...[/bold cyan]")
    async with aiohttp.ClientSession() as session:
        for acc in accounts:
            resp = await fetch(session, SESSION_ENDPOINT, acc.token, account=acc, proxy=acc.proxy)
            if not resp or not resp.get("success"):
                acc.last_error = "❌ Invalid Token"
                console.print(f"[red][!] Token {acc.index} is invalid or expired[/red]")
            else:
                console.print(f"[green][✓] Token {acc.index} is valid[/green]")

    tasks = [asyncio.create_task(worker(acc)) for acc in accounts]
    tasks.append(asyncio.create_task(dashboard(accounts)))
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[red]Bot stopped by user[/red]")
