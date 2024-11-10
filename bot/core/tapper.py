import asyncio
import string
import os
import random

import aiohttp
import json

from aiocfscrape import CloudflareScraper
from aiohttp_proxy import ProxyConnector
import cloudscraper
from better_proxy import Proxy
from urllib.parse import unquote

from faker import Faker
from pyrogram import Client
from pyrogram.errors import Unauthorized, UserDeactivated, AuthKeyUnregistered, FloodWait
from pyrogram.raw.functions.messages import RequestWebView
from datetime import datetime, timedelta, timezone
import brotli

from bot.config import settings
from bot.utils import logger
from bot.exceptions import InvalidSession

from .headers import headers
from .agents import generate_random_user_agent


class Tapper:
    def __init__(self, tg_client: Client):
        self.session_name = tg_client.name
        self.tg_client = tg_client
        self.user_id = 0
        self.username = None
        self.url = 'https://clicker-api.crashgame247.io'
        self.ws_id = 1
        self.ws_task = None
        self.recoverable = None
        self.epoch = None
        self.offset = None

        self.session_ug_dict = self.load_user_agents() or []
        self.user_data = self.load_user_data()

        headers['User-Agent'] = self.check_user_agent()

    async def generate_random_user_agent(self):
        return generate_random_user_agent(device_type='android', browser_type='chrome')

    def save_user_agent(self):
        user_agents_file_name = "user_agents.json"

        if not any(session['session_name'] == self.session_name for session in self.session_ug_dict):
            user_agent_str = generate_random_user_agent()

            self.session_ug_dict.append({
                'session_name': self.session_name,
                'user_agent': user_agent_str})

            with open(user_agents_file_name, 'w') as user_agents:
                json.dump(self.session_ug_dict, user_agents, indent=4)

            logger.success(f"<light-yellow>{self.session_name}</light-yellow> | ⚡️ User agent saved <green>successfully</green>")

            return user_agent_str

    def load_user_agents(self):
        user_agents_file_name = "user_agents.json"

        try:
            with open(user_agents_file_name, 'r') as user_agents:
                session_data = json.load(user_agents)
                if isinstance(session_data, list):
                    return session_data

        except FileNotFoundError:
            logger.warning("✨ User agents file <red>not found</red>, creating...")

        except json.JSONDecodeError:
            logger.warning("😨 User agents file is <red>empty</red> or corrupted.")

        return []

    def check_user_agent(self):
        load = next(
            (session['user_agent'] for session in self.session_ug_dict if session['session_name'] == self.session_name),
            None)

        if load is None:
            return self.save_user_agent()

        return load

    def load_user_data(self):
        user_data_file_name = f"data/{self.session_name}.json"
        if not os.path.exists('data'):
            os.makedirs('data')

        try:
            with open(user_data_file_name, 'r') as user_data_file:
                return json.load(user_data_file)

        except FileNotFoundError:
            logger.warning(f"😳 User data file for {self.session_name} <red>not found</red>, creating a new one...")
            return {"referred": None, "last_click_time": None, "last_sleep_time": None, "acknowledged": False, "squad_name": None, "in_squad": False, "sleep_time": None}

        except json.JSONDecodeError:
            logger.warning(f"😳 User data file for {self.session_name} <red>is empty</red> or corrupted. Creating a new one...")
            return {"referred": None, "last_click_time": None, "last_sleep_time": None, "acknowledged": False, "squad_name": None, "in_squad": False, "sleep_time": None}

        except Exception as error:
            logger.error(f"🚫 An unexpected <red>error</red> occurred while loading user data for {self.session_name}: {error}")
            return {"referred": None, "last_click_time": None, "last_sleep_time": None, "acknowledged": False, "squad_name": None, "in_squad": False, "sleep_time": None}

    def save_user_data(self):
        user_data_file_name = f"data/{self.session_name}.json"
        with open(user_data_file_name, 'w') as user_data_file:
            json.dump(self.user_data, user_data_file, indent=4)

    async def get_tg_web_data(self, proxy: str | None, http_client: aiohttp.ClientSession) -> str:
        if proxy:
            proxy = Proxy.from_str(proxy)
            proxy_dict = dict(
                scheme=proxy.protocol,
                hostname=proxy.host,
                port=proxy.port,
                username=proxy.login,
                password=proxy.password
            )
        else:
            proxy_dict = None

        self.tg_client.proxy = proxy_dict
        ref_param = settings.REF_ID if settings.REF_ID != '' else False
        if ref_param and not ref_param.endswith("pub"):
            self.user_data["referred"] = "gold"
        elif ref_param:
            self.user_data["referred"] = "regular"

        self.save_user_data()

        try:
            with_tg = True

            if not self.tg_client.is_connected:
                with_tg = False
                try:
                    await self.tg_client.connect()
                    start_command_found = False

                    async for message in self.tg_client.get_chat_history("WheelOfWhalesBot"):
                        if (message.text and message.text.startswith("/start")) or (message.caption and message.caption.startswith("/start")):
                            start_command_found = True
                            break

                    if start_command_found:
                        self.user_data["acknowledged"] = True
                        self.save_user_data()
                    else:
                        if ref_param:
                            await self.tg_client.send_message("WheelOfWhalesBot", f"/start {ref_param}")
                            if not ref_param.endswith("pub"):
                                logger.success(f"<light-yellow>{self.session_name}</light-yellow> | ⭐️ Referred by a <yellow>gold</yellow> ticket.")
                            else:
                                logger.success(f"<light-yellow>{self.session_name}</light-yellow> | 🖥 Referred by a <light-blue>regular</light-blue> referral.")

                except (Unauthorized, UserDeactivated, AuthKeyUnregistered):
                    raise InvalidSession(self.session_name)

            while True:
                try:
                    peer = await self.tg_client.resolve_peer('WheelOfWhalesBot')
                    break
                except FloodWait as fl:
                    fls = fl.value

                    logger.warning(f"{self.session_name} | 😞 FloodWait <red>{fl}</red>")
                    logger.info(f"{self.session_name} | 😴 Sleep <light-cyan>{fls}s</light-cyan>")

                    await asyncio.sleep(fls + 3)

            web_view = await self.tg_client.invoke(RequestWebView(
                peer=peer,
                bot=peer,
                platform='android',
                from_bot_menu=False,
                url="https://clicker.crashgame247.io/"
            ))

            auth_url = web_view.url
            tg_web_data = unquote(
                string=unquote(
                    string=auth_url.split('tgWebAppData=', maxsplit=1)[1].split('&tgWebAppVersion', maxsplit=1)[0]))

            me = await self.tg_client.get_me()
            self.user_id = me.id
            self.username = me.username if me.username else ''
            if self.username == '':
                while True:
                    fake = Faker('en_US')

                    name_english = fake.name()
                    name_modified = name_english.replace(" ", "").lower()

                    random_letters = ''.join(random.choices(string.ascii_lowercase, k=random.randint(1, 7)))
                    final_name = name_modified + random_letters
                    status = await self.tg_client.set_username(final_name)
                    if status:
                        logger.info(f"<light-yellow>{self.session_name}</light-yellow> | 💾 Set username <cyan>@{final_name}</cyan>")
                        break
                    else:
                        continue

            if with_tg is False:
                await self.tg_client.disconnect()

            return tg_web_data

        except InvalidSession as error:
            raise error

        except Exception as error:
            logger.error(f"<light-yellow>{self.session_name}</light-yellow> | 🚫 Unknown <red>error</red> during Authorization: {error}")
            await asyncio.sleep(3)

    async def check_proxy(self, http_client: aiohttp.ClientSession, proxy: Proxy) -> None:
        try:
            response = await http_client.get(url='https://httpbin.org/ip', timeout=aiohttp.ClientTimeout(5))
            ip = (await response.json()).get('origin')
            logger.info(f"<light-yellow>{self.session_name}</light-yellow> | 🛡 Proxy IP: <blue>{ip}</blue>")
        except Exception as error:
            logger.error(f"<light-yellow>{self.session_name}</light-yellow> | 🛡 Proxy: {proxy} | 🚫 <red>Error:</red> {error}")

    async def login(self, http_client: aiohttp.ClientSession, init_data):
        if init_data is None:
            logger.info(f"<light-yellow>{self.session_name}</light-yellow> | 🚫 init_data is <red>None</red>")
            await asyncio.sleep(999999999999)

        params = dict(item.split('=') for item in init_data.split('&'))
        user_data = json.loads(unquote(params['user']))

        data = {
            "dataCheckChain": init_data,
            "initData": {
                "query_id": params['query_id'],
                "user": user_data,
                "auth_date": params['auth_date'],
                "hash": params['hash']
            }
        }

        try:
            resp = await http_client.post(f"{self.url}/user/sync", json=data)
            
            resp.raise_for_status()

            resp_json = await resp.json()
            if settings.DEBUG:
                logger.debug(f"<light-yellow>{self.session_name}</light-yellow> | 🫡 Login Response: {resp_json}")

            token = resp_json.get("token")
            whitelisted = resp_json.get("user", {}).get("whitelisted")
            banned = resp_json.get("user", {}).get("isBanned")
            balance = resp_json.get("balance", {}).get("amount")
            streak = resp_json.get("meta", {}).get("dailyLoginStreak")
            last_login = resp_json.get("meta", {}).get("lastFirstDailyLoginAt")
            referrer = resp_json.get("referrerUsername")
            tribe = resp_json.get("user", {}).get("tribeId")
            tasks = resp_json.get("meta", {}).get("regularTasks")
            nanoid = resp_json.get("user", {}).get("nanoid")
            flappy_score = resp_json.get("meta", {}).get("flappyScore")
            dino_score = resp_json.get("meta", {}).get("dinoScore")

            return (token, whitelisted, banned, balance, streak, last_login, referrer, tribe, tasks, nanoid, flappy_score, dino_score)

        except aiohttp.ContentTypeError as e:
            logger.error(f"<light-yellow>{self.session_name}</light-yellow> | 🚫 ContentTypeError: {str(e)}. Response: {await resp.text()}")
            return None

        except Exception as e:
            logger.error(f"<light-yellow>{self.session_name}</light-yellow> | 🚫 An unexpected <red>error</red> occurred: {str(e)}")
            return None

    async def claim_daily_bonus(self, http_client, proxy):
        url = f"{self.url}/user/bonus/claim"
        
        headers = {
            'Accept': 'application/json, text/plain, */*',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Accept-Language': 'ru-RU,ru;q=0.9',
            'Authorization': http_client.headers.get('Authorization'),
            'Origin': 'https://clicker.crashgame247.io',
            'Priority': 'u=1, i',
            'Referer': 'https://clicker.crashgame247.io/',
            'Sec-Ch-Ua': '"Google Chrome";v="129", "Not=A?Brand";v="8", "Chromium";v="129"',
            'Sec-Ch-Ua-Mobile': '?1',
            'Sec-Ch-Ua-Platform': '"Android"',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-site',
            'User-Agent': http_client.headers.get('User-Agent')
        }
        
        try:
            scraper = cloudscraper.create_scraper()

            proxies = {
                'http': proxy,
                'https': proxy,
            } if proxy else None

            response = scraper.patch(url, headers=headers, proxies=proxies)
            
            if response.status_code == 200:
                json_data = response.json()
                points = json_data.get("incrementBy", 0)
                logger.success(f"<light-yellow>{self.session_name}</light-yellow> | 💘 Daily bonus <green>successfully claimed!</green> (+{points} points)")
            else:
                try:
                    error_data = response.json()
                    logger.error(f"<light-yellow>{self.session_name}</light-yellow> | 🚫 <red>Error</red> when claiming the daily bonus: {error_data}")
                except json.JSONDecodeError:
                    logger.error(f"<light-yellow>{self.session_name}</light-yellow> | 💀 Failed to decode error response: {response.text}")
                
                if response.status_code == 500:
                    return False
        
        except cloudscraper.exceptions.CloudflareChallengeError as e:
            logger.error(f"{self.session_name} | 🚫 Cloudflare challenge <red>error</red> occurred: {e}")
        except Exception as e:
            logger.error(f"{self.session_name} | 🤷‍♂️ Unexpected <red>error</red>: {str(e)}")

    async def send_clicks(self, http_client: aiohttp.ClientSession, click_count: int):
        clicks = {"clicks": click_count}
        try:
            async with http_client.put(
                f"{self.url}/meta/clicks", 
                json=clicks
            ) as response:
                if response.status == 200:
                    pass
                else:
                    logger.error(f"<light-yellow>{self.session_name}</light-yellow> | 🚫 <red>Failed</red> with status: {response.status} (send_clicks)")

        except Exception as e:
            pass

    async def refresh_tokens(self, proxy, http_client: aiohttp.ClientSession):
        init_data = await self.get_tg_web_data(proxy=proxy, http_client=http_client)

        params = dict(item.split('=') for item in init_data.split('&'))
        user_data = json.loads(unquote(params['user']))

        data = {
            "dataCheckChain": init_data,
            "initData": {
                "query_id": params['query_id'],
                "user": user_data,
                "auth_date": params['auth_date'],
                "hash": params['hash']
            }
        }

        async with http_client.post(f"{self.url}/user/sync", json=data) as resp:
            if resp.status == 200:
                resp_json = await resp.json()
            else:
                logger.error(f"<light-yellow>{self.session_name}</light-yellow> | 🚫 <red>Failed</red> with status: {resp.status} (refresh_tokens)")
                return None

        token = resp_json.get("token")
        wsToken = resp_json.get("wsToken")
        wsSubToken = resp_json.get("wsSubToken")
        id_for_ws = resp_json.get("user", {}).get("id")

        return token, wsToken, wsSubToken, id_for_ws

    async def play_flappy(self, http_client, proxy):
        try:
            logger.info(f"<light-yellow>{self.session_name}</light-yellow> | 🎮 Started <blue>playing</blue> FlappyWhale...")
            sleep = random.uniform(40, 90)
            await asyncio.sleep(sleep)

            headers = {
                'Accept': 'application/json, text/plain, */*',
                'Accept-Encoding': 'gzip, deflate, br, zstd',
                'Accept-Language': 'en-US,en;q=0.9',
                'Authorization': http_client.headers.get('Authorization'),
                'Origin': 'https://clicker.crashgame247.io',
                'Referer': 'https://clicker.crashgame247.io/',
                'Sec-Ch-Ua': '"Google Chrome";v="129", "Not=A?Brand";v="8", "Chromium";v="129"',
                'Sec-Ch-Ua-Mobile': '?1',
                'Sec-Ch-Ua-Platform': '"Android"',
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'same-site',
                'User-Agent': http_client.headers.get('User-Agent')
            }

            proxies = {
                'http': proxy,
                'https': proxy,
            } if proxy else None

            scraper = cloudscraper.create_scraper()

            leaderboard_url = 'https://clicker-api.crashgame247.io/meta/minigame/flappy/leaderboards'
            scraper.get(leaderboard_url, headers=headers, proxies=proxies)

            score = random.randint(settings.SCORE[0], settings.SCORE[1])
            payload = {"score": score}

            score_url = 'https://clicker-api.crashgame247.io/meta/minigame/flappy/score'
            score_response = scraper.patch(score_url, headers=headers, proxies=proxies, json=payload)

            if score_response.status_code == 200:
                logger.success(f"<light-yellow>{self.session_name}</light-yellow> | 🐳 <cyan>Finished</cyan> FlappyWhale with a score of {score}!")
                self.user_data["flappy_score"] = score
                self.save_user_data()
            else:
                logger.error(f"<light-yellow>{self.session_name}</light-yellow> | 🔴 <red>Failed</red> to submit FlappyWhale score, status code: {score_response.status_code}")

        except Exception as error:
            logger.error(f"<light-yellow>{self.session_name}</light-yellow> | 😡 <red>Error</red> in play_flappy: {error}")

    async def play_dino(self, http_client, proxy):
        try:
            logger.info(f"<light-yellow>{self.session_name}</light-yellow> | 🎮 Started <blue>playing</blue> DinoWhale...")
            sleep = random.uniform(40, 90)
            await asyncio.sleep(sleep)

            headers = {
                'Accept': 'application/json, text/plain, */*',
                'Accept-Encoding': 'gzip, deflate, br, zstd',
                'Accept-Language': 'en-US,en;q=0.9',
                'Authorization': http_client.headers.get('Authorization'),
                'Origin': 'https://clicker.crashgame247.io',
                'Referer': 'https://clicker.crashgame247.io/',
                'Sec-Ch-Ua': '"Google Chrome";v="129", "Not=A?Brand";v="8", "Chromium";v="129"',
                'Sec-Ch-Ua-Mobile': '?1',
                'Sec-Ch-Ua-Platform': '"Android"',
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'same-site',
                'User-Agent': http_client.headers.get('User-Agent')
            }

            proxies = {
                'http': proxy,
                'https': proxy,
            } if proxy else None

            scraper = cloudscraper.create_scraper()

            leaderboard_url = 'https://clicker-api.crashgame247.io/meta/minigame/dino/leaderboards'
            scraper.get(leaderboard_url, headers=headers, proxies=proxies)

            score = random.randint(settings.SCORE[0], settings.SCORE[1])
            payload = {"score": score}

            score_url = 'https://clicker-api.crashgame247.io/meta/minigame/dino/score'
            score_response = scraper.patch(score_url, headers=headers, proxies=proxies, json=payload)

            if score_response.status_code == 200:
                logger.success(f"<light-yellow>{self.session_name}</light-yellow> | 🐳 <cyan>Finished</cyan> DinoWhale with a score of {score}!")
                self.user_data["dino_score"] = score
                self.save_user_data()
            else:
                logger.error(f"<light-yellow>{self.session_name}</light-yellow> | 🔴 <red>Failed</red> to submit DinoWhale score, status code: {score_response.status_code}")

        except Exception as error:
            logger.error(f"<light-yellow>{self.session_name}</light-yellow> | 😡 <red>Error</red> in play_dino: {error}")

    async def whale_spin(self, http_client, proxy):
        try:
            logger.info(f"<light-yellow>{self.session_name}</light-yellow> | 🎰 WhaleSpin Started...")
            headers = {
                'Accept': 'application/json, text/plain, */*',
                'Accept-Encoding': 'gzip, deflate, br, zstd',
                'Accept-Language': 'ru-RU,ru;q=0.9',
                'Authorization': http_client.headers.get('Authorization'),
                'Origin': 'https://clicker.crashgame247.io',
                'Referer': 'https://clicker.crashgame247.io/',
                'Sec-Ch-Ua': '"Google Chrome";v="129", "Not=A?Brand";v="8", "Chromium";v="129"',
                'Sec-Ch-Ua-Mobile': '?1',
                'Sec-Ch-Ua-Platform': '"Android"',
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'same-site',
                'User-Agent': http_client.headers.get('User-Agent')
            }

            proxies = {
                'http': proxy,
                'https': proxy,
            } if proxy else None

            scraper = cloudscraper.create_scraper()

            reach_url = 'https://clicker-api.crashgame247.io/meta/wheel/reach'
            reach_response = scraper.get(reach_url, headers=headers, proxies=proxies)

            if reach_response.status_code == 200:
                pass
            elif reach_response.status_code != 400:
                logger.error(f"<light-yellow>{self.session_name}</light-yellow> | 🔴 Failed to reach wheel, status code: {reach_response.status_code}")

            await asyncio.sleep(30)
            ack_url = 'https://clicker-api.crashgame247.io/meta/wheel/ack'
            ack_response = scraper.put(ack_url, headers=headers, proxies=proxies)

            if ack_response.status_code == 200:
                content_encoding = ack_response.headers.get('Content-Encoding', '')

                if b'"opensGame"' in ack_response.content:
                    ack_content = ack_response.content.decode('utf-8', errors='replace')
                else:
                    if 'br' in content_encoding:
                        try:
                            ack_content = brotli.decompress(ack_response.content).decode('utf-8', errors='replace')
                        except brotli.error as e:
                            logger.error(f"<light-yellow>{self.session_name}</light-yellow> | 🔴 Brotli decompression failed: {e}")
                            ack_content = '{}'
                    else:
                        ack_content = ack_response.content.decode('utf-8', errors='replace')

                try:
                    ack_json = json.loads(ack_content)
                    opens_game = ack_json.get('opensGame', 'N/A')
                except ValueError as e:
                    logger.error(f"<light-yellow>{self.session_name}</light-yellow> | 🔴 Failed to parse JSON response: {e}")

                if opens_game == "flappy":
                    logger.info(f"<light-yellow>{self.session_name}</light-yellow> | 🐤 WhaleSpin Result: <light-yellow>FlappyWhale</light-yellow>")
                    await self.save_result("🐤 FlappyWhale")
                    await self.play_flappy(http_client, proxy)
                elif opens_game == "dino":
                    logger.info(f"<light-yellow>{self.session_name}</light-yellow> | 🦖 WhaleSpin Result: <green>DinoWhale</green>")
                    await self.save_result("🦖 DinoWhale")
                    await self.play_dino(http_client, proxy)
                elif opens_game == "slot":
                    logger.info(f"<light-yellow>{self.session_name}</light-yellow> | 🎰 WhaleSpin Result: <cyan>Slot</cyan>")
                    await self.save_result("🎰 Slot")
                elif opens_game == "death":
                    logger.info(f"<light-yellow>{self.session_name}</light-yellow> | ☠️ WhaleSpin Result: <red>Death</red>")
                    await self.save_result("☠️ Death")
                elif opens_game == "whale_free_spin":
                    logger.info(f"<light-yellow>{self.session_name}</light-yellow> | 🐋 WhaleSpin Result: <blue>5 Free Spins</blue> awarded in @whale")
                    await self.save_result("🐋 5 Free Spins awarded in @whale")
                else:
                    logger.warning(f"<light-yellow>{self.session_name}</light-yellow> | ❓ WhaleSpin Result: Unknown result type '{opens_game}' detected")

            elif ack_response.status_code != 400:
                logger.error(f"<light-yellow>{self.session_name}</light-yellow> | 🔴 Failed to acknowledge wheel, status code: {ack_response.status_code}")

        except Exception as error:
            logger.error(f"<light-yellow>{self.session_name}</light-yellow> | 😡 <red>Error</red> in whale_spin: {error}")

    async def save_result(self, result):
        try:
            current_time = datetime.now().strftime("%d.%m.%Y | %H:%M")
            message = f"{current_time} | {self.session_name} | {result}\n"

            with open("WhaleSpins.txt", "a", encoding="utf-8") as file:
                file.write(message)
        except Exception as error:
            logger.error(f"<light-yellow>{self.session_name}</light-yellow> | 😡 <red>Error</red> in save_result: {error}")

    async def send_websocket_messages(self, ws_url, wsToken, wsSubToken, id_for_ws, proxy, http_client):
        while True:
            try:
                proxy_conn = ProxyConnector.from_url(proxy) if proxy else None

                async with aiohttp.ClientSession(connector=proxy_conn) as ws_session:
                    async with ws_session.ws_connect(ws_url) as websocket:
                        connect_message = {
                            "connect": {"token": wsToken, "name": "js"},
                            "id": self.ws_id
                        }
                        await websocket.send_json(connect_message)
                        if settings.DEBUG:
                            logger.debug(f"<light-yellow>{self.session_name}</light-yellow> | 🌐 Sent connect message: {connect_message}")
                        await websocket.receive()

                        self.ws_id += 1

                        subscribe_message = {
                            "subscribe": {
                                "channel": f"user:{id_for_ws}",
                                "token": wsSubToken
                            },
                            "id": self.ws_id
                        }
                        
                        if self.ws_id == 2:
                            await websocket.send_json(subscribe_message)
                            if settings.DEBUG:
                                logger.debug(f"<light-yellow>{self.session_name}</light-yellow> | 🌐 Sent subscribe message: {subscribe_message}")
                            response = await websocket.receive()

                            if response.type == aiohttp.WSMsgType.TEXT:
                                data = response.data.strip().splitlines()
                                for line in data:
                                    try:
                                        json_response = json.loads(line)
                                        if json_response.get("id") == 2:
                                            self.recoverable = json_response["subscribe"].get("recoverable")
                                            self.epoch = json_response["subscribe"].get("epoch")
                                            self.offset = json_response["subscribe"].get("offset")
                                            break
                                    except json.JSONDecodeError:
                                        pass
                            elif response.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                                pass

                        if self.ws_id > 2:
                            subscribe_message = {
                                "subscribe": {
                                    "channel": f"user:{id_for_ws}",
                                    "token": wsSubToken,
                                    **({"recover": self.recoverable} if self.recoverable is not None else {}),
                                    **({"epoch": self.epoch} if self.epoch is not None else {}),
                                    **({"offset": self.offset} if self.offset is not None else {})
                                },
                                "id": self.ws_id
                            }
                            await websocket.send_json(subscribe_message)
                            if settings.DEBUG:
                                logger.debug(f"<light-yellow>{self.session_name}</light-yellow> | 🌐 Sent subscribe message: {subscribe_message}")
                            await websocket.receive()

                        self.ws_id += 1

                        while True:
                            response = await websocket.receive()
                            
                            if response.type == aiohttp.WSMsgType.TEXT:
                                data = response.data.strip().splitlines()
                                for line in data:
                                    try:
                                        json_response = json.loads(line)
                                        if settings.DEBUG:
                                            logger.debug(f"<light-yellow>{self.session_name}</light-yellow> | 🌐 Received JSON: {json_response}")
                                        if "push" in json_response:
                                            push_data = json_response["push"].get("pub", {}).get("data", {})
                                            
                                            if push_data.get("type") == "show_wheel":
                                                await self.whale_spin(http_client, proxy)
                                                
                                                if "offset" in json_response["push"]["pub"]:
                                                    self.offset = json_response["push"]["pub"]["offset"]

                                        if json_response == {}:
                                            await websocket.send_json({})
                                            if settings.DEBUG:
                                                logger.debug(f"<light-yellow>{self.session_name}</light-yellow> | 🌐 Sent ping response")
                                            break
                                                    
                                    except json.JSONDecodeError:
                                        pass
                            elif response.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                                break

            except Exception as e:
                logger.error(f"<light-yellow>{self.session_name}</light-yellow> | 🚫 WebSocket <red>error</red>: {str(e)}. Reconnecting...")
                continue

    async def clicker(self, proxy, http_client: aiohttp.ClientSession):
        logger.success(f"<light-yellow>{self.session_name}</light-yellow> | ✅ AutoTapper <light-green>started!</light-green>")

        while True:
            refresh = await self.refresh_tokens(proxy, http_client)
            
            if refresh is not None:
                token, wsToken, wsSubToken, id_for_ws = refresh
                http_client.headers.update({'Authorization': f'Bearer {token}'})
                break
            else:
                logger.warning(f"<light-yellow>{self.session_name}</light-yellow> | ⚠️ Could not retrieve all data, going to sleep 30s before the next attempt...")
                await asyncio.sleep(30)

        ws_url = "wss://clicker-socket.crashgame247.io/connection/websocket"
        self.ws_task = asyncio.create_task(self.send_websocket_messages(ws_url, wsToken, wsSubToken, id_for_ws, proxy, http_client))

        while True:
            if settings.NIGHT_MODE:
                current_time = datetime.now(timezone.utc).time()
                night_start = datetime.strptime("22:00", "%H:%M").time()
                night_end = datetime.strptime("06:00", "%H:%M").time()

                if night_start <= current_time or current_time < night_end:
                    now = datetime.now(timezone.utc)
                    if current_time >= night_start:
                        next_morning = now + timedelta(days=1)
                        next_morning = next_morning.replace(hour=6, minute=0, second=0, microsecond=0)
                    else:
                        next_morning = now.replace(hour=6, minute=0, second=0, microsecond=0)

                    sleep_duration = (next_morning - now).total_seconds()
                    logger.info(f"<light-yellow>{self.session_name}</light-yellow> | 🌙 It's night time! Sleeping until <cyan>06:00 UTC</cyan> (~{int(sleep_duration // 3600)} hours)")
                    
                    if self.ws_task:
                        self.ws_task.cancel()
                        self.ws_id = 1

                    await asyncio.sleep(sleep_duration)

                    while True:
                        refresh = await self.refresh_tokens(proxy, http_client)
                        
                        if refresh is not None:
                            token, wsToken, wsSubToken, id_for_ws = refresh
                            http_client.headers.update({'Authorization': f'Bearer {token}'})
                            break
                        else:
                            logger.warning(f"<light-yellow>{self.session_name}</light-yellow> | ⚠️ Could not retrieve all data, going to sleep 30s before the next attempt...")
                            await asyncio.sleep(30)

                    self.ws_task = asyncio.create_task(self.send_websocket_messages(ws_url, wsToken, wsSubToken, id_for_ws, proxy, http_client))

            last_click_time = self.user_data.get("last_click_time")
            last_sleep_time = self.user_data.get("last_sleep_time")

            if last_sleep_time:
                last_sleep_time = datetime.strptime(last_sleep_time, "%Y-%m-%d %H:%M:%S.%f").replace(tzinfo=timezone.utc)
                time_since_last_sleep = datetime.now(timezone.utc) - last_sleep_time

                if time_since_last_sleep < timedelta(seconds=self.user_data.get("sleep_time", 0)):
                    remaining_time = timedelta(seconds=self.user_data["sleep_time"]) - time_since_last_sleep

                    remaining_minutes = remaining_time.seconds // 60
                    remaining_seconds = remaining_time.seconds % 60

                    logger.info(f"<light-yellow>{self.session_name}</light-yellow> | ⏳ Sleep time <cyan>not yet reached</cyan>, waiting for {remaining_minutes} minutes {remaining_seconds} seconds until next click...")

                    if self.ws_task:
                        self.ws_task.cancel()
                        self.ws_id = 1

                    await asyncio.sleep(remaining_time.total_seconds())

                    while True:
                        refresh = await self.refresh_tokens(proxy, http_client)
                        
                        if refresh is not None:
                            token, wsToken, wsSubToken, id_for_ws = refresh
                            http_client.headers.update({'Authorization': f'Bearer {token}'})
                            break
                        else:
                            logger.warning(f"<light-yellow>{self.session_name}</light-yellow> | ⚠️ Could not retrieve all data, going to sleep 30s before the next attempt...")
                            await asyncio.sleep(30)

                    self.ws_task = asyncio.create_task(self.send_websocket_messages(ws_url, wsToken, wsSubToken, id_for_ws, proxy, http_client))

            total_clicks = 0
            clicks = []

            while total_clicks < 1000:
                click_count = random.randint(1, 15)
                if total_clicks + click_count > 1000:
                    click_count = 1000 - total_clicks
                clicks.append(click_count)
                total_clicks += click_count

            intervals = [random.uniform(1, 3) for _ in clicks]
            total_time = sum(intervals)

            logger.success(f"<light-yellow>{self.session_name}</light-yellow> | 🕘 Estimated clicking time: <light-magenta>~{total_time / 60:.2f} minutes</light-magenta>")

            total_clicks = 0
            for click_count, interval in zip(clicks, intervals):
                await self.send_clicks(http_client=http_client, click_count=click_count)
                total_clicks += click_count

                self.user_data["last_click_time"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")
                self.save_user_data()

                await asyncio.sleep(interval)

                if total_clicks >= 1000:
                    break

            if self.ws_task:
                self.ws_task.cancel()
                self.ws_id = 1

            sleep_time = random.randint(1100, 2000)  # Примерно от 18 до 33 минут
            self.user_data["last_sleep_time"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")
            self.user_data["sleep_time"] = sleep_time
            self.save_user_data()

            logger.success(f"<light-yellow>{self.session_name}</light-yellow> | ✅ {total_clicks} clicks sent, <light-blue>sleeping for {sleep_time // 60} minutes.</light-blue>")

            await asyncio.sleep(sleep_time)

            while True:
                refresh = await self.refresh_tokens(proxy, http_client)
                
                if refresh is not None:
                    token, wsToken, wsSubToken, id_for_ws = refresh
                    http_client.headers.update({'Authorization': f'Bearer {token}'})
                    break
                else:
                    logger.warning(f"<light-yellow>{self.session_name}</light-yellow> | ⚠️ Could not retrieve all data, going to sleep 30s before the next attempt...")
                    await asyncio.sleep(30)

            self.ws_task = asyncio.create_task(self.send_websocket_messages(ws_url, wsToken, wsSubToken, id_for_ws, proxy, http_client))

    async def complete_tasks(self, tasks, http_client, proxy):
        methods = {
            'FOLLOW_WHALE_EN': self.verify,
            'FOLLOW_WHEEL_OF_WHALES': self.verify,
            'FOLLOW_TON_NEWS': self.verify,
            'FOLLOW_WHALE_SPORTS': self.verify,
            'SHARE_TO_STORY': self.verify,
            'FOLLOW_WHALE_DISCORD': self.verify,
            'FOLLOW_WHALE_YT': self.verify,
            'FOLLOW_WHALE_MEMES': self.verify,
            'FOLLOW_WHALE_INST': self.verify,
            'FOLLOW_WHALE_TIKTOK': self.verify,
            'FOLLOW_WHALE_X': self.verify,
            'FOLLOW_WHALE_SOCIALS': self.verify,
            'FOLLOW_WHALE_KICK': self.verify,
            'ROOLZ': self.verify,
            'DOWNLOAD_WALLET': self.verify,
            'LIKE_RETWEET': self.verify,
            'BITS': self.verify,
            'BOOM': self.verify,
            'DEJEN_DOG': self.verify,
            'DUCKS': self.verify,
            'TON_KOMBAT': self.verify,
            'OWLS': self.verify,
            'CLAYTON': self.verify
        }

        codes = {
            'CODE_VERIFY_redwhale': 'REDWHALE'
        }

        for task in methods.keys():
            if task not in tasks or not tasks[task]:
                await methods[task](task, http_client, proxy)

        for task, code in codes.items():
            if task not in tasks or not tasks[task]:
                await self.verify_code(code, http_client, proxy)

    async def verify(self, task, http_client, proxy): 
        try:
            sleep = random.randint(10, 30)
            logger.info(f"<light-yellow>{self.session_name}</light-yellow> | ⏳ Waiting {sleep} seconds before verifying task '{task}'")
            
            await asyncio.sleep(sleep)

            headers = {
                'Accept': 'application/json, text/plain, */*',
                'Accept-Encoding': 'gzip, deflate, br, zstd',
                'Accept-Language': 'ru-RU,ru;q=0.9',
                'Authorization': http_client.headers.get('Authorization'),
                'Origin': 'https://clicker.crashgame247.io',
                'Priority': 'u=1, i',
                'Referer': 'https://clicker.crashgame247.io/',
                'Sec-Ch-Ua': '"Google Chrome";v="129", "Not=A?Brand";v="8", "Chromium";v="129"',
                'Sec-Ch-Ua-Mobile': '?1',
                'Sec-Ch-Ua-Platform': '"Android"',
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'same-site',
                'User-Agent': http_client.headers.get('User-Agent')
            }
            
            url = f'{self.url}/meta/tasks/{task}'
            
            scraper = cloudscraper.create_scraper()
            
            proxies = {
                'http': proxy,
                'https': proxy,
            } if proxy else None

            response = scraper.patch(url, headers=headers, json={}, proxies=proxies)
            resp_json = response.json()

            if response.status_code == 200:
                increment_score = resp_json.get('incrementScore', 'unknown')
                logger.info(f"<light-yellow>{self.session_name}</light-yellow> | 🥰 Task '{task}' <green>completed successfully.</green> <light-yellow>+{increment_score}</light-yellow>")
            else:
                logger.error(f"<light-yellow>{self.session_name}</light-yellow> | 😡 <red>Failed</red> to verify task '{task}', status code: {response.status_code}")
        
        except Exception as error:
            logger.error(f"<light-yellow>{self.session_name}</light-yellow> | 😡 <red>Error</red> verifying task '{task}': {error}")

    async def verify_code(self, code, http_client, proxy):
        try:
            sleep = random.randint(10, 30)
            logger.info(f"<light-yellow>{self.session_name}</light-yellow> | ⏳ Waiting {sleep} seconds before verifying code '{code}'")
            
            await asyncio.sleep(sleep)
            
            headers = {
                'Accept': 'application/json, text/plain, */*',
                'Accept-Encoding': 'gzip, deflate, br, zstd',
                'Accept-Language': 'ru-RU,ru;q=0.9',
                'Authorization': http_client.headers.get('Authorization'),
                'Origin': 'https://clicker.crashgame247.io',
                'Priority': 'u=1, i',
                'Referer': 'https://clicker.crashgame247.io/',
                'Sec-Ch-Ua': '"Google Chrome";v="129", "Not=A?Brand";v="8", "Chromium";v="129"',
                'Sec-Ch-Ua-Mobile': '?1',
                'Sec-Ch-Ua-Platform': '"Android"',
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'same-site',
                'User-Agent': http_client.headers.get('User-Agent'),
                'Content-Type': 'application/json'
            }

            url = f'{self.url}/meta/tasks/CODE_VERIFY'

            scraper = cloudscraper.create_scraper()

            proxies = {
                'http': proxy,
                'https': proxy,
            } if proxy else None

            payload = {'code': code}
            
            response = scraper.patch(url, headers=headers, json=payload, proxies=proxies)
            resp_json = response.json()

            if response.status_code == 200:
                logger.info(f"<light-yellow>{self.session_name}</light-yellow> | 🥰 Code '{code}' <green>verified successfully.</green> <light-yellow>+{resp_json.get('incrementScore', 'unknown')}</light-yellow>")
            else:
                logger.error(f"<light-yellow>{self.session_name}</light-yellow> | 😡 <red>Failed</red> to verify code '{code}', status code: {response.status_code}")
        
        except Exception as error:
            logger.error(f"<light-yellow>{self.session_name}</light-yellow> | 😡 <red>Error</red> verifying code '{code}': {error}")

    async def get_squad_info(self, http_client, squad_name):
        try:
            response = await http_client.get(f"{self.url}/tribes/{squad_name}")
            response.raise_for_status()
            response_json = await response.json()
            return response_json
        except Exception as error:
            logger.error(f"<light-yellow>{self.session_name}</light-yellow> | 🚫 <red>Error</red> getting squad info for {squad_name}: {error}")
            return None

    async def join_squad(self, squad_name, http_client, proxy):
        try:
            scraper = cloudscraper.create_scraper()

            proxies = {
                'http': proxy,
                'https': proxy,
            } if proxy else None

            headers = {
                'Accept': 'application/json, text/plain, */*',
                'Accept-Encoding': 'gzip, deflate, br, zstd',
                'Accept-Language': 'ru-RU,ru;q=0.9',
                'Origin': 'https://clicker.crashgame247.io',
                'Referer': 'https://clicker.crashgame247.io/',
                'Sec-Ch-Ua': '"Google Chrome";v="129", "Not=A?Brand";v="8", "Chromium";v="129"',
                'Sec-Ch-Ua-Mobile': '?1',
                'Sec-Ch-Ua-Platform': 'Android',
                "Authorization": http_client.headers.get('Authorization'),
                "User-Agent": http_client.headers.get('User-Agent')
            }

            response = scraper.post(
                f"{self.url}/tribes/{squad_name}/join",
                headers=headers,
                proxies=proxies
            )

            if response.status_code == 200:
                if response.text == 'true':
                    return True

                response_json = response.json()
                return response_json
            else:
                raise Exception(f"🚫 <red>Failed</red> to join squad. Status code: {response.status_code}, Message: {response.text}")

        except Exception as error:
            logger.error(f"<light-yellow>{self.session_name}</light-yellow> | 🚫 <red>Error</red> joining squad {squad_name}: {error}")
            return None

    async def run(self, proxy: str | None) -> None:
        if settings.USE_RANDOM_DELAY_IN_RUN:
            random_delay = random.randint(settings.RANDOM_DELAY_IN_RUN[0], settings.RANDOM_DELAY_IN_RUN[1])

            # TODO: remove after initial run
            from bot.utils import proxy_utils_v2
            random_delay = proxy_utils_v2.get_delay_time_for_session(self.tg_client.name) + random_delay

            logger.info(f"<light-yellow>{self.session_name}</light-yellow> | ⏳ Bot will start in <ly>{random_delay}s</ly>")
            await asyncio.sleep(random_delay)

        proxy_conn = ProxyConnector().from_url(proxy) if proxy else None
        http_client = CloudflareScraper(headers=headers, connector=proxy_conn)
        squad_name = settings.SQUAD_NAME if settings.SQUAD_NAME != '' else False

        if proxy:
            await self.check_proxy(http_client=http_client, proxy=proxy)

        init_data = await self.get_tg_web_data(proxy=proxy, http_client=http_client)

        while True:
            login = await self.login(http_client=http_client, init_data=init_data)

            if login is not None:
                token, whitelisted, banned, balance, streak, last_login, referrer, tribe, tasks, nanoid, flappy_score, dino_score = login
                self.user_data["balance"] = balance
                self.user_data["streak"] = streak
                self.user_data["acc_ref_id"] = nanoid
                self.user_data["flappy_score"] = flappy_score
                self.user_data["dino_score"] = dino_score
                self.save_user_data()
                break
            else:
                logger.warning(f"<light-yellow>{self.session_name}</light-yellow> | ⚠️ Could not retrieve all data, going to sleep 30s before the next attempt...")
                await asyncio.sleep(30)

        logger.info(f"<light-yellow>{self.session_name}</light-yellow> | 💰 Balance: <yellow>{balance}</yellow> | ⚡️ Current streak: <cyan>{streak}</cyan>")
        http_client.headers["Authorization"] = f"Bearer {token}"

        if not whitelisted:
            logger.warning(f"<light-yellow>{self.session_name}</light-yellow> | 😔 You are <magenta>not whitelisted</magenta> :(")
            logger.info(f"<light-yellow>{self.session_name}</light-yellow> | 😴 Going <cyan>sleep</cyan> 24h")
            await asyncio.sleep(24 * 3600)

        if banned:
            logger.warning(f"<light-yellow>{self.session_name}</light-yellow> | 😨 You are <red>banned...</red>")
            self.user_data["banned"] = True
            self.save_user_data()
            await asyncio.sleep(999999999999)
        else:
            self.user_data["banned"] = False
            self.save_user_data()

        if self.user_data["referred"] == "gold" and not self.user_data["acknowledged"]:
            self.user_data["acknowledged"] = True
            self.save_user_data()
            if referrer:
                logger.success(f"<light-yellow>{self.session_name}</light-yellow> | 🤗 Referred By: @{referrer}")

        if settings.NIGHT_MODE:
            current_time = datetime.now(timezone.utc).time()
            night_start = datetime.strptime("22:00", "%H:%M").time()
            night_end = datetime.strptime("06:00", "%H:%M").time()

            if night_start <= current_time or current_time < night_end:
                now = datetime.now(timezone.utc)
                if current_time >= night_start:
                    next_morning = now + timedelta(days=1)
                    next_morning = next_morning.replace(hour=6, minute=0, second=0, microsecond=0)
                else:
                    next_morning = now.replace(hour=6, minute=0, second=0, microsecond=0)

                sleep_duration = (next_morning - now).total_seconds()
                logger.info(f"<light-yellow>{self.session_name}</light-yellow> | 🌙 It's night time! Sleeping until <cyan>06:00 UTC</cyan> (~{int(sleep_duration // 3600)} hours)")
                await asyncio.sleep(sleep_duration)

        if squad_name:
            if not tribe:
                if not self.user_data.get("in_squad", False):
                    squad_info = await self.get_squad_info(http_client=http_client, squad_name=settings.SQUAD_NAME)
                    if squad_info:
                        squad_name = squad_info.get("name")
                        if squad_name:
                            join = await self.join_squad(http_client=http_client, proxy=proxy, squad_name=settings.SQUAD_NAME)
                            if join:
                                logger.success(f"<light-yellow>{self.session_name}</light-yellow> | ✅ Successfully <green>joined squad</green>: {squad_name}")
                                self.user_data["squad_name"] = squad_name
                                self.user_data["in_squad"] = True
                                self.save_user_data()
                            else:
                                logger.error(f"<light-yellow>{self.session_name}</light-yellow> | 😔 <red>Failed</red> to join squad: {squad_name}")

        if settings.AUTO_TAP:
            logger.info(f"<light-yellow>{self.session_name}</light-yellow> | 😋 Starting <green>AutoTapper...</green>")
            asyncio.create_task(self.clicker(proxy=proxy, http_client=http_client))

        if settings.AUTO_TASKS:
            await self.complete_tasks(tasks, http_client, proxy)

        while True:
            try:
                if last_login is not None:
                    last_login_time = datetime.strptime(last_login, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
                else:
                    logger.error(f"<light-yellow>{self.session_name}</light-yellow> | 🚫 Last login data is <red>None</red> (please try restarting the bot)")

                if datetime.now(timezone.utc) - last_login_time > timedelta(hours=24):
                    await self.claim_daily_bonus(http_client=http_client, proxy=proxy)

                logger.info(f"<light-yellow>{self.session_name}</light-yellow> | 😴 Going <cyan>sleep</cyan> 8h (This doesn't concern the AutoTapper)")

                await asyncio.sleep(8 * 3600)

            except InvalidSession as error:
                raise error

            except Exception as error:
                logger.error(f"{self.session_name} | 🚫 Unknown <red>error</red>: {error} (Try restarting the bot..)")
                await asyncio.sleep(3)

async def run_tapper(tg_client: Client, proxy: str | None):
    try:
        await Tapper(tg_client=tg_client).run(proxy=proxy)
    except InvalidSession:
        logger.error(f"{tg_client.name} | 🚫 <red>Invalid</red> Session")