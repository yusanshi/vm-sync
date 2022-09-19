import logging
import subprocess
from multiprocessing import Process
from pathlib import Path
from time import sleep
from typing import Literal

import pyautogui
import requests
import uvicorn
import yaml
import keyboard
from fastapi import FastAPI

from tray_icon import TrayIcon

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(message)s")

app = FastAPI()

INTERVAL = 1.0

with open(Path(__file__).parent.parent / 'config.yaml') as f:
    config = yaml.safe_load(f)

BASE_URL = f"http://{config['windows']['host']}:{config['windows']['port']}"


def get_app_status(app_name):
    try:
        return requests.get(f"{BASE_URL}/status/{app_name}",
                            timeout=0.1).json()
    except Exception:
        return 'vm_offline'


def update_icons():
    icons = {
        f'{k1}-{k2}': str(
            Path(__file__).parent.parent / 'image' / 'icon' / f'{k1}-{k2}.png')
        for k1 in ['tim', 'wechat']
        for k2 in ['no-message', 'new-message', 'gray']
    }
    tray_icons = {
        'tim': TrayIcon(
            icons['tim-gray'],
            lambda: open_app('tim'),
        ),
        'wechat': TrayIcon(
            icons['wechat-gray'],
            lambda: open_app('wechat'),
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


Keypress = Literal[tuple(config['forward']['keypress'] + ['command:hide'])]


@app.post("/keyboard/{keypress}")
def send_keypress(keypress: Keypress):
    logging.info(f"Receive keypress {keypress.split('+')}")
    if keypress == 'command:hide':
        # Minimize the VM window
        subprocess.run([
            'wmctrl', '-r', config['windows']['vm-name'], '-b', 'toggle,shaded'
        ])
        return

    if keypress == 'f1':
        subprocess.run('flameshot gui', shell=True)
        return

    # fallback: simulate the keypress in host
    pyautogui.hotkey(*config['forward']['host-key'].split('+'))
    sleep(0.1)
    pyautogui.hotkey(*keypress.split('+'))


def wait_vm_start():
    name = config['windows']['vm-name']
    if name not in subprocess.check_output('VBoxManage list runningvms',
                                           shell=True,
                                           text=True):
        subprocess.run(['VBoxManage', 'startvm', name])

    while True:
        try:
            if requests.get(BASE_URL, timeout=0.1).status_code == 200:
                logging.info('Get response from VM')
                sleep(3)  # TOOD wait...
                return
        except Exception:
            pass

        sleep(0.1)


def open_app(app_name):
    if get_app_status(app_name) == 'vm_offline':
        logging.info('VM is offline, start it')
        wait_vm_start()

    # Bring vm to front
    subprocess.run(['wmctrl', '-a', config['windows']['vm-name']])

    requests.get(f"{BASE_URL}/open/{app_name}")


if __name__ == '__main__':
    keyboard.add_hotkey('alt+w', open_app, args=['wechat'], suppress=True)
    keyboard.add_hotkey('alt+q', open_app, args=['tim'], suppress=True)

    Process(target=update_icons).start()

    for app_name in config['startup-app']:
        Process(target=open_app, args=(app_name, )).start()

    # wait for network available
    while True:
        if subprocess.call(['ping', '-c', '1', config['linux']['host']]) == 0:
            break
        sleep(1)

    uvicorn.run("main:app",
                host=config['linux']['host'],
                port=config['linux']['port'])
