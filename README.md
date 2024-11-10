[![Static Badge](https://img.shields.io/badge/-CHANNEL-black?style=for-the-badge&logo=telegram&logoColor=white)](https://t.me/hidden_coding)
[![Static Badge](https://img.shields.io/badge/-CHAT-black?style=for-the-badge&logo=telegram&logoColor=white)](https://t.me/hidden_codding_chat)
[![Static Badge](https://img.shields.io/badge/-BOT%20LINK-black?style=for-the-badge&logo=telegram&logoColor=white)](https://t.me/wheelofwhalesbot?start=CGYJGk91pub)
[![Static Badge](https://img.shields.io/badge/-BOT%20MARKET-black?style=for-the-badge&logo=telegram&logoColor=white)](https://t.me/hcmarket_bot?start=referral_5143703753)

## Recommendation before use

# 🔥🔥 PYTHON version must be 3.10 🔥🔥

> 🇷 🇺 README in russian available [here](README-RU.md)

## Features  
|                         Feature                          | Supported |
|:--------------------------------------------------------:|:---------:|
|                      Multithreading                      |     ✅     |
|                 Proxy binding to session                 |     ✅     |
|                      Auto Referral                       |     ✅     |
|                Automatic joining to squad                |     ✅     |
|                       AutoTapper                         |     ✅     |
|              Auto play games (Flappy and Dino)           |     ✅     |
|                       Auto Tasks                         |     ✅     |
|                       WebSockets                         |     ✅     |
|              Support for pyrogram .session               |     ✅     |

## [Settings](https://github.com/yummy1gay/WheelOfWhales/blob/main/.env-example/)
|         Settings            |                                     Description                                     |
|:---------------------------:|:-----------------------------------------------------------------------------------:|
|        **API_ID**           |           Platform data from which to run the Telegram session (default - android)  |
|       **API_HASH**          |           Platform data from which to run the Telegram session (default - android)  |
|       **AUTO_TAP**          |                      Automatic clicking (default - True)                            |
|        **SCORE**            |                 Score per game (default is [5, 30] (That is, 5 to 30))              |
|      **SQUAD_NAME**         |               @username of the squad channel/chat without the '@' symbol            |
|        **REF_ID**           |                         Text after 'start=' in your referral link                   |
|       **AUTO_TASKS**        |                        Automatically performs tasks (default - False)               |
| **USE_RANDOM_DELAY_IN_RUN** |                             Name saying itself (default - True)                     |
|   **RANDOM_DELAY_IN_RUN**   |                     Random seconds delay for ^^^ (default is [5, 30])               |
|       **NIGHT_MODE**        |               Pauses operations from 22:00 to 06:00 UTC (default - False)           |
| **USE_PROXY_FROM_FILE**     |      Whether to use a proxy from the `bot/config/proxies.txt` file (True / False)   |

## Quick Start 📚

To fast install libraries and run bot - open run.bat on Windows or run.sh on Linux

## Prerequisites
Before you begin, make sure you have the following installed:
- [Python](https://www.python.org/downloads/) **version 3.10**

## Obtaining API Keys
1. Go to my.telegram.org and log in using your phone number.
2. Select "API development tools" and fill out the form to register a new application.
3. Record the API_ID and API_HASH provided after registering your application in the .env file.

## Installation
You can download the [**repository**](https://github.com/yummy1gay/WheelOfWhales) by cloning it to your system and installing the necessary dependencies:
```shell
git clone https://github.com/yummy1gay/WheelOfWhales.git
cd WheelOfWhales
```

Then you can do automatic installation by typing:

Windows:
```shell
run.bat
```

Linux:
```shell
run.sh
```

# Linux manual installation
```shell
sudo sh install.sh
python3 -m venv venv
source venv/bin/activate
pip3 install -r requirements.txt
cp .env-example .env
nano .env  # Here you must specify your API_ID and API_HASH, the rest is taken by default
python3 main.py
```

You can also use arguments for quick start, for example:
```shell
~/WheelOfWhales >>> python3 main.py --action (1/2)
# Or
~/WheelOfWhales >>> python3 main.py -a (1/2)

# 1 - Run clicker
# 2 - Creates a session
```

# Windows manual installation
```shell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env-example .env
# Here you must specify your API_ID and API_HASH, the rest is taken by default
python main.py
```

You can also use arguments for quick start, for example:
```shell
~/WheelOfWhales >>> python main.py --action (1/2)
# Or
~/WheelOfWhales >>> python main.py -a (1/2)

# 1 - Run clicker
# 2 - Creates a session
```




### Contacts

For support or questions, contact me on Telegram: 
[![Static Badge](https://img.shields.io/badge/telegram-bot_author-link?style=for-the-badge&logo=telegram&logoColor=white&logoSize=auto&color=blue)](https://t.me/yummy1gay)
