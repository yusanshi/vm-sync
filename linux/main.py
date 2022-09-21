import logging
import subprocess
from multiprocessing import Process
from pathlib import Path
from time import sleep

import requests
import uvicorn
import yaml
from fastapi import FastAPI
from pynput import keyboard

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


def get_vm_active():
    try:
        return requests.get(f"{BASE_URL}/active", timeout=0.1).json()
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
    subprocess.run([
        'xdotool', 'search', '--name', config['windows']['vm-name'],
        'windowactivate'
    ])

    requests.get(f"{BASE_URL}/open/{app_name}")


def vm_is_active():
    return subprocess.check_output('xdotool getactivewindow getwindowname',
                                   shell=True,
                                   text=True).startswith(
                                       config['windows']['vm-name'])


def app_is_active(app_name):
    if app_name == 'tim':
        return '\\Tencent\\TIM\\' in get_vm_active()
    if app_name == 'wechat':
        return '\\Tencent\\WeChat\\' in get_vm_active()


def toggle_app_display(app_name):
    if vm_is_active() and app_is_active(app_name):
        logging.info(f'App {app_name} already active in front, minimize it')
        subprocess.run([
            'xdotool', 'search', '--name', config['windows']['vm-name'],
            'windowminimize'
        ])
        return

    logging.info(f'App {app_name} not in front, open it')
    open_app(app_name)


def register_hotkeys():
    with keyboard.GlobalHotKeys({
            '<alt>+w': lambda: toggle_app_display('wechat'),
            '<alt>+q': lambda: toggle_app_display('tim'),
    }) as h:
        h.join()


def register_single_hotkey(hotkey, callback):
    """
    keyboard.GlobalHotKeys({'<f1>': lambda: print('f1')}) is not working,
    use this instead
    """

    def on_press(key):
        if key == hotkey:
            callback()

    with keyboard.Listener(on_press=on_press) as listener:
        listener.join()


if __name__ == '__main__':
    Process(target=register_hotkeys).start()
    Process(target=register_single_hotkey,
            args=(
                keyboard.Key.f1,
                lambda: vm_is_active() and subprocess.run('flameshot gui',
                                                          shell=True),
            )).start()

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
