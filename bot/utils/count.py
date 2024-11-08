import os
import json
from bot.utils import logger

os.makedirs('data', exist_ok=True)

total_balance = 0
banned_count = 0

for filename in os.listdir('data'):
    if filename.endswith('.json'):
        file_path = os.path.join('data', filename)
        
        if os.path.getsize(file_path) == 0:
            continue
        
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)

                total_balance += data.get('balance', 0)

                if data.get('banned', False):
                    banned_count += 1
                    
        except json.JSONDecodeError:
            pass
        except Exception as e:
            pass

logger.info(f'💰 Total Balance: {total_balance}')
logger.info(f'😨 Number of <red>banned</red> sessions (in @WheelOfWhalesBot): {banned_count}')
