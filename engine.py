# language: Python 3.11, file: engine.py, target: Telegram MTProto
import asyncio
from itertools import cycle
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.account import ReportPeerRequest
from telethon.tl.types import (
    InputReportReasonSpam,
    InputReportReasonViolence,
    InputReportReasonPornography,
    InputReportReasonOther,
    InputReportReasonChildAbuse,
)
from config import API_ID, API_HASH, PROXIES
from db import get_active_accounts, deactivate_account

REASON_MAP = {
    "spam":     InputReportReasonSpam(),
    "violence": InputReportReasonViolence(),
    "porn":     InputReportReasonPornography(),
    "other":    InputReportReasonOther(),
    "child":    InputReportReasonChildAbuse(),
}

ALL_REASONS = list(REASON_MAP.keys())

async def report_single(
    session_str: str,
    account_id: int,
    target: str,
    reason_key: str,
    proxy=None
):
    reason = REASON_MAP.get(reason_key, InputReportReasonSpam())
    try:
        async with TelegramClient(
            StringSession(session_str), API_ID, API_HASH,
            proxy=proxy
        ) as client:
            entity = await client.get_entity(target)
            await client(ReportPeerRequest(
                peer=entity,
                reason=reason,
                message=""
            ))
            return True
    except Exception as e:
        err = str(e).lower()
        if any(x in err for x in ["banned", "deactivated", "auth_key"]):
            deactivate_account(account_id)
        return False

async def mass_report(
    target: str,
    reason_key: str = "spam",
    batch_size: int = 5,
    delay: float = 0.8
):
    accounts = get_active_accounts()
    if not accounts:
        return {"ok": 0, "fail": 0, "total": 0}

    results = {"ok": 0, "fail": 0, "total": len(accounts)}
    proxy_pool = cycle(PROXIES) if PROXIES else cycle([None])

    for i in range(0, len(accounts), batch_size):
        batch = accounts[i:i + batch_size]
        tasks = [
            report_single(
                session_str, acc_id, target,
                reason_key, next(proxy_pool)
            )
            for acc_id, session_str, phone in batch
        ]
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)
        for r in batch_results:
            if r is True:
                results["ok"] += 1
            else:
                results["fail"] += 1
        await asyncio.sleep(delay)

    return results

async def full_mass_report(target: str):
    """Все причины подряд — максимальный удар."""
    total = {"ok": 0, "fail": 0}
    for reason in ALL_REASONS:
        r = await mass_report(target, reason)
        total["ok"]   += r["ok"]
        total["fail"] += r["fail"]
        await asyncio.sleep(2)
    return total
