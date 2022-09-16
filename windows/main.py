from pathlib import Path
from typing import Literal
from time import sleep
from pathlib import Path
import mss
import numpy as np
import cv2
import logging
from datetime import datetime
import requests
import yaml
import uvicorn
import yaml
from fastapi import FastAPI
from pywinauto.application import Application

TRAY_WIDTH = 800
TRAY_HEIGHT = 80
INTERVAL = 0.3
NUM_IMAGES_EACH_CHECK = 4


def get_tray_image():
    with mss.mss() as sct:
        screen = sct.monitors[0]
        assert screen['width'] > TRAY_WIDTH
        assert screen['height'] > TRAY_HEIGHT
        area = {
            'left': screen['width'] - TRAY_WIDTH,
            'top': screen['height'] - TRAY_HEIGHT,
            'width': TRAY_WIDTH,
            'height': TRAY_HEIGHT,
        }
        sct_img = sct.grab(area)
    image = np.asarray(sct_img)[:, :, :3]
    return image


app = FastAPI()

App = Literal['tim', 'wechat']
Status = Literal['no_message', 'new_message', 'not_found', 'unknown_error']


@app.get("/")
def hello():
    return 'Hello!'


tray_images = []
app_status = {}


@app.on_event('startup')
def init_data():
    status['tim'] = 'not_found'
    status['wechat'] = 'not_found'


@app.get("/status/{app_name}")
def get_status(app_name: App):
    return status[app_name]


@app.get("/open/{app_name}")
def open_app(app_name: App):
    if app_name == 'tim':
        if tray.child_window(title_re='^TIM.+').exists():
            tray.child_window(title_re='^TIM.+').click()
            return
        Application().start(
            r'C:\\Program Files (x86)\\Tencent\\TIM\Bin\\TIM.exe')

    elif app_name == 'wechat':
        if tray.child_window(title='WeChat').exists():
            tray.child_window(title='WeChat').click()
            return
        app = Application().start(
            r'C:\\Program Files (x86)\\Tencent\\WeChat\\WeChat.exe')
        app.top_window().set_focus()  # WeChat need to manually bring to top


with open(Path(__file__).parent.parent / 'config.yaml') as f:
    config = yaml.safe_load(f)

if __name__ == '__main__':
    uvicorn.run("main:app",
                host=config['windows']['host'],
                port=config['windows']['port'])
