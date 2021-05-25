#!/usr/bin/env python

import json
import time
from pathlib import Path

import requests


CONFIG_FILE_PATH = Path('config.json')


def ratelimit(headers):
    requests_remaining = int(headers['requests-remaining'])
    print(f'{requests_remaining} requests remaining')
    if not requests_remaining:
        requests_reset = int(headers['requests-reset'])
        print(f'sleeping for {requests_reset} seconds')
        time.sleep(requests_reset)


def main():
    with open(CONFIG_FILE_PATH) as config_file:
        config = json.load(config_file)

    bearer_token = f"Bearer {config['token']}"


if __name__ == '__main__':
    main()
