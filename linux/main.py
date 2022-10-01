import logging
import subprocess
from datetime import datetime
from multiprocessing import Process
from pathlib import Path
from time import sleep

import requests
import yaml
from pynput import keyboard

from message_box import message_box_action
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

INTERVAL = 0.5

with open(Path(__file__).parent.parent / 'config.yaml') as f:
    config = yaml.safe_load(f)

BASE_URL = f"http://{config['windows']['host']}:{config['windows']['port']}"


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
    subprocess.run([
        'xdotool', 'search', '--name', config['windows']['name'],
        'windowactivate'
    ])

    requests.post(f"{BASE_URL}/open/{app_name}")


def vm_is_active():
    return subprocess.check_output('xdotool getactivewindow getwindowname',
                                   shell=True,
                                   text=True).startswith(
                                       config['windows']['name'])


def app_is_active(app_name):
    if app_name == 'tim':
        return '\\Tencent\\TIM\\' in get_vm_active()
    if app_name == 'wechat':
        return '\\Tencent\\WeChat\\' in get_vm_active()


def toggle_app_display(app_name):
    if vm_is_active() and app_is_active(app_name):
        logging.info(f'App {app_name} already active in front, minimize it')
        subprocess.run([
            'xdotool', 'search', '--name', config['windows']['name'],
            'windowminimize'
        ])
        return

    logging.info(f'App {app_name} not in front, open it')
    open_app(app_name)


def register_hotkeys():
    with keyboard.GlobalHotKeys({
            '<alt>+w': lambda: toggle_app_display('wechat'),
            '<alt>+q': lambda: toggle_app_display('tim'),
            **{
                x['hotkey']['pynput']: lambda: vm_is_active() and subprocess.run(x['command'],
                                                                                 shell=True)
                for x in config['capture-hotkey']
            }
    }) as h:
        h.join()


def startup_app():
    logging.info('Open startup apps')
    for app_name in config['startup-app']:
        Process(target=open_app, args=(app_name, )).start()
        sleep(2)


if __name__ == '__main__':
    Process(target=register_hotkeys).start()

    for app_name in ['tim', 'wechat']:
        Process(target=update_icon, args=(app_name, )).start()

    Process(target=message_box_action,
            args=(
                startup_app,
                'Run start-up apps?',
                8000,
            )).start()
