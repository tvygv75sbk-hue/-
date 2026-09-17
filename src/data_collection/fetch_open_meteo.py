# -*- coding: utf-8 -*-
import os, json
from datetime import date
import requests
import pandas as pd
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
CONFIG = yaml.safe_load(open(os.path.join(ROOT, 'config.yaml'), 'r', encoding='utf-8'))
RAW_DIR = os.path.join(ROOT, CONFIG['paths']['data_raw'])
os.makedirs(RAW_DIR, exist_ok=True)

lat, lon = CONFIG['project']['lat'], CONFIG['project']['lon']
start_date = str(CONFIG['project']['start_date'])
end_date = str(CONFIG['project']['end_date'])

def main():
    url = (
        'https://archive-api.open-meteo.com/v1/era5'
        f'?latitude={lat}&longitude={lon}'
        f'&start_date={start_date}&end_date={end_date}'
        '&daily=temperature_2m_mean,temperature_2m_max,temperature_2m_min,precipitation_sum'
        '&timezone=Asia%2FShanghai'
    )
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    data = r.json()
    df = pd.DataFrame({
        'dt': pd.to_datetime(data['daily']['time']),
        'temp_mean': data['daily']['temperature_2m_mean'],
        'temp_max': data['daily']['temperature_2m_max'],
        'temp_min': data['daily']['temperature_2m_min'],
        'precipitation': data['daily']['precipitation_sum'],
    })
    df.to_csv(os.path.join(RAW_DIR, 'weather_open_meteo.csv'), index=False, encoding='utf-8-sig')
    with open(os.path.join(RAW_DIR, 'weather_open_meteo.meta.json'), 'w', encoding='utf-8') as f:
        json.dump({'url': url}, f, ensure_ascii=False, indent=2)

if __name__ == '__main__':
    main()
