from multiprocessing import Process
from pathlib import Path
from typing import Literal
import subprocess
import uvicorn
import yaml
from fastapi import FastAPI
from pydantic import BaseModel
from tray_icon import TrayIcon
import requests
from time import sleep
import json

app = FastAPI()

INTERVAL = 1.0

with open(Path(__file__).parent.parent / 'config.yaml') as f:
    config = yaml.safe_load(f)

BASE_URL = f"http://{config['windows']['host']}:{config['windows']['port']}"


def get_app_status(app_name):
    try:
        return requests.get(f"{BASE_URL}/status/{app_name}",
                            timeout=0.1).json()
    except (requests.exceptions.ReadTimeout, json.JSONDecodeError):
        return 'vm_offline'


def update_icons():
    icons = {
        f'{k1}-{k2}': str(
            Path(__file__).parent.parent / 'image' / 'icon' / f'{k1}-{k2}.png')
        for k1 in ['tim', 'wechat']
        for k2 in ['no-message', 'new-message', 'gray']
    }
    tray_icons = {
        'tim':
        TrayIcon(
            icons['tim-gray'],
            'Open TIM',
            lambda: open_app('tim'),
            'Exit TIM',
            lambda: exit_app('tim'),
        ),
        'wechat':
        TrayIcon(
            icons['wechat-gray'],
            'Open WeChat',
            lambda: open_app('wechat'),
            'Exit WeChat',
            lambda: exit_app('wechat'),
        )
    }
    while True:
        status = get_app_status('tim')
        if status in ['no_message', 'new_message']:
            icon = icons[f"tim-{status.replace('_','-')}"]
        else:
            icon = icons['tim-gray']
        tray_icons['tim'].set_icon(icon)

        status = get_app_status('wechat')
        if status in ['no_message', 'new_message']:
            icon = icons[f"wechat-{status.replace('_','-')}"]
        else:
            icon = icons['wechat-gray']
        tray_icons['wechat'].set_icon(icon)

        sleep(INTERVAL)


@app.get("/")
def hello():
    return 'Hello from Linux'


def wait_vm_start():
    name = config['windows']['vm-name']
    if name not in subprocess.check_output('VBoxManage list runningvms',
                                           shell=True,
                                           text=True):
        subprocess.run(['VBoxManage', 'startvm', name])

    while True:
        try:
            if requests.get(BASE_URL, timeout=0.1).status_code == 200:
                return
        except requests.exceptions.ReadTimeout:
            pass
        sleep(0.1)

    # TODO showdown vm on linux showdown?


def open_app(app_name):
    if get_app_status(app_name) == 'vm_offline':
        wait_vm_start()

    requests.get(f"{BASE_URL}/open/{app_name}")

    # Bring vm to front
    subprocess.run(['wmctrl', '-a', config['windows']['vm-name']])


def exit_app(app_name):
    subprocess.check_output('VBoxManage list runningvms',
                            shell=True,
                            text=True)


if __name__ == '__main__':
    p = Process(target=update_icons)
    p.start()
    uvicorn.run("main:app",
                host=config['linux']['host'],
                port=config['linux']['port'])
