from pathlib import Path
from typing import Literal
import subprocess
import uvicorn
import yaml
from fastapi import FastAPI
from pydantic import BaseModel
from tray_icon import TrayIcon

app = FastAPI()

tray_icons = {}


@app.on_event('startup')
def init_data():
    tray_icons['tim'] = TrayIcon(
        None,
        'Open TIM',
        lambda: print('Open'),
        'Exit TIM',
        lambda: print('Exit'),
    )
    tray_icons['wechat'] = TrayIcon(
        None,
        'Open WeChat',
        lambda: print('Open'),
        'Exit WeChat',
        lambda: print('Exit'),
    )


@app.get("/")
def hello():
    return 'Hello!'


class AppStatus(BaseModel):
    name: Literal['tim', 'wechat']
    status: Literal['no_message', 'new_message', 'not_found', 'unknown_error']


@app.post("/status")
def status(app_status: AppStatus):
    if app_status.name == 'tim':
        if app_status.status == 'no_message':
            new_icon = icons['tim-no-message']
        elif app_status.status == 'new_message':
            new_icon = icons['tim-new-message']
        else:
            new_icon = None
        tray_icons['tim'].set_icon(new_icon)
    elif app_status.name == 'wechat':
        if app_status.status == 'no_message':
            new_icon = icons['wechat-no-message']
        elif app_status.status == 'new_message':
            new_icon = icons['wechat-new-message']
        else:
            new_icon = None
        tray_icons['wechat'].set_icon(new_icon)


icons = {
    f'{k1}-{k2}':
    str(Path(__file__).parent.parent / 'image' / 'icon' / f'{k1}-{k2}.png')
    for k1 in ['tim', 'wechat']
    for k2 in ['no-message', 'new-message', 'gray']
}

with open(Path(__file__).parent.parent / 'config.yaml') as f:
    config = yaml.safe_load(f)


def wait_vm_start():
    name = config['windows']['vm-name']
    if name not in subprocess.check_output('VBoxManage list runningvms',
                                           shell=True,
                                           text=True):
        subprocess.run(['VBoxManage', 'startvm', name])
    config['windows']['host']

    subprocess.run(['VBoxManage', 'guestcontrol', name])


if __name__ == '__main__':
    uvicorn.run("main:app",
                host=config['linux']['host'],
                port=config['linux']['port'])
