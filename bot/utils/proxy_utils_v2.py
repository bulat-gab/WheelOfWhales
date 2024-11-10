import os
from better_proxy import Proxy
from pyrogram import Client
import json
import sys

from .logger import logger

PROXY_FILE_PATH = "sessions/do_not_commit.proxies.json"
def create_tg_client_proxy_pairs(tg_clients: list[Client]) -> list[tuple[Client, Proxy]]:
    """For each tg client fetches the corresponding proxy from do_not_commit.proxies.json
    
    Returns
    -------
    list[tuple[Client, Proxy]]
        List of tuples
        First element of a tuple - Pyrogram.Client
        Second element - better_proxy.Proxy
    """
    if not tg_clients:
        logger.error("Input argument 'tg_clients' is empty.")
        sys.exit()

    proxies = _load_proxies_from_file()
    result = []
    for tg in tg_clients:
        proxy = proxies.get(tg.name)
        if not proxy:
            logger.warning(f"Session {tg.name} does not have a matching proxy. Skipping it.")
            continue

        pair = (tg, proxy)
        result.append(pair)
    
    logger.info(f"Found {len(result)} sessions with proxies.")
    return result

def get_delay_time_for_session(session_name: str, base_delay=600) -> int:
    try:
        number = session_name[2:]
        number = int(number)
        if number <= 1:
            number = 1

        base_delay = base_delay * (number - 1)
        return base_delay
    except:
        return base_delay

def _load_proxies_from_file() -> dict[str, Proxy]:
    if not os.path.exists(PROXY_FILE_PATH):
        logger.critical(f"File with proxies {PROXY_FILE_PATH} was not found. Stopping application...")
        sys.exit()

    proxies_json = None
    with open(file=PROXY_FILE_PATH, mode="r", encoding="utf-8-sig") as file:
        proxies_json = json.load(file)

    result = {}
    for session_name, proxy_str in proxies_json.items():
        result[session_name] = Proxy.from_str(proxy=proxy_str.strip())
    
    if not result:
        logger.error(f"File {PROXY_FILE_PATH} does not contain proxies.")
        sys.exit()

    return result