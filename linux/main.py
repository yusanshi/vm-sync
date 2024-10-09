#!/usr/bin/env python3
import logging
import re
import subprocess
from datetime import datetime
from multiprocessing import Process
from pathlib import Path
from time import sleep
from typing import Literal

import requests
import uvicorn
import yaml
from fastapi import FastAPI
from tray_icon import TrayIcon

log_dir = Path(__file__).parent / 'log'
log_dir.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(message)s",
    handlers=[
        logging.FileHandler(
            log_dir /
            f"{datetime.now().replace(microsecond=0).isoformat().replace(':','-')}.txt"
        ),
        logging.StreamHandler()
    ])

app = FastAPI()

INTERVAL = 0.5

with open(Path(__file__).parent.parent / 'config.yaml') as f:
    config = yaml.safe_load(f)

BASE_URL = f"http://{config['windows']['host']}:{config['windows']['port']}"
WINDOW_NAME_REGEX = f"{config['windows']['name']} (\(Snapshot .+\) )?\[Running\] \- Oracle VM VirtualBox"


def get_app_status(app_name):
    try:
        return requests.get(f"{BASE_URL}/status/{app_name}",
                            timeout=0.1).json()
    except Exception:
        return 'vm_offline'


def get_vm_active():
    try:
        return requests.get(f"{BASE_URL}/active", timeout=0.1).json()
    except Exception:
        return 'vm_offline'


def update_icon(app_name):
    icons = {
        k: str(
            Path(__file__).parent.parent / 'image' / 'icon' /
            f'{app_name}-{k}.png')
        for k in ['no-message', 'new-message', 'gray']
    }
    tray_icon = TrayIcon(
        icons['gray'],
        lambda: toggle_app_display(app_name),
    )

    while True:
        status = get_app_status(app_name)
        if status in ['no_message', 'new_message']:
            icon = icons[f"{status.replace('_','-')}"]
        else:
            icon = icons['gray']

        tray_icon.change_icon(icon)

        sleep(INTERVAL)


@app.get("/")
def hello():
    return 'Hello from Linux'


Keypress = Literal[tuple(x['hotkey'] for x in config['capture-hotkey'])]


@app.post("/keypress/{keypress}")
def forward_keypress(keypress: Keypress):
    logging.info(f"Receive keypress {keypress}")
    for x in config['capture-hotkey']:
        if keypress == x['hotkey']:
            # use `Popen` (non-blocking) instead of 'run' (blocking)
            subprocess.Popen(x['command'], shell=True, cwd=Path.home())


def wait_vm_start():
    name = config['windows']['name']
    if name not in subprocess.check_output('VBoxManage list runningvms',
                                           shell=True,
                                           text=True):
        subprocess.run(['VBoxManage', 'startvm', name])

    while True:
        try:
            if requests.get(BASE_URL, timeout=0.1).status_code == 200:
                logging.info('Get response from VM')
                sleep(3)  # wait...
                return
        except Exception:
            pass

        sleep(0.1)


def open_app(app_name):
    if get_app_status(app_name) == 'vm_offline':
        logging.info('VM is offline, start it')
        wait_vm_start()

    # Bring vm to front
    subprocess.run(
        ['xdotool', 'search', '--name', WINDOW_NAME_REGEX, 'windowactivate'])

    requests.post(f"{BASE_URL}/open/{app_name}")


def vm_is_active():
    try:
        current_active_name = subprocess.check_output(
            'xdotool getactivewindow getwindowname', shell=True,
            text=True).strip()
    except subprocess.CalledProcessError:
        return False
    return re.fullmatch(WINDOW_NAME_REGEX, current_active_name)


def app_is_active(app_name):
    if app_name == 'tim':
        return '\\Tencent\\TIM\\' in get_vm_active()
    if app_name == 'wechat':
        return '\\Tencent\\WeChat\\' in get_vm_active()


def toggle_app_display(app_name):
    if vm_is_active() and app_is_active(app_name):
        logging.info(f'App {app_name} already active in front, minimize it')
        subprocess.run([
            'xdotool', 'search', '--name', WINDOW_NAME_REGEX, 'windowminimize'
        ])
        return

    logging.info(f'App {app_name} not in front, open it')
    open_app(app_name)


def startup_app():
    logging.info('Open startup apps')
    for app_name in config['startup-app']:
        Process(target=open_app, args=(app_name, )).start()


if __name__ == '__main__':
    for app_name in ['tim', 'wechat']:
        Process(target=update_icon, args=(app_name, )).start()

    # wait for network available
    while True:
        if subprocess.call(['ping', '-c', '1', config['linux']['host']]) == 0:
            break
        sleep(1)

    uvicorn.run("main:app",
                host=config['linux']['host'],
                port=config['linux']['port'])
