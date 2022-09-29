import logging
import subprocess
from multiprocessing import Process
from pathlib import Path
from time import sleep
from datetime import datetime

import requests
import uvicorn
import yaml
from fastapi import FastAPI
from pynput import keyboard

from tray_icon import TrayIcon
from message_box import message_box_action

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


def flameshot_callback():
    if vm_is_active():
        logging.info('VM is active, run the flameshot command')
        subprocess.run('flameshot gui', shell=True)
        return
    logging.info('Host is active, skip flameshot command')


def startup_app():
    logging.info('Open startup apps')
    for app_name in config['startup-app']:
        Process(target=open_app, args=(app_name, )).start()
        sleep(2)


if __name__ == '__main__':
    Process(target=register_hotkeys).start()
    Process(target=register_single_hotkey,
            args=(
                keyboard.Key.f1,
                flameshot_callback,
            )).start()

    for app_name in ['tim', 'wechat']:
        Process(target=update_icon, args=(app_name, )).start()

    Process(target=message_box_action,
            args=(
                startup_app,
                'Run start-up apps?',
                5000,
            )).start()

    # wait for network available
    while True:
        if subprocess.call(['ping', '-c', '1', config['linux']['host']]) == 0:
            break
        sleep(1)

    uvicorn.run("main:app",
                host=config['linux']['host'],
                port=config['linux']['port'])
