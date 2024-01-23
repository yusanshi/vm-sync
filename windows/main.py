import logging
import subprocess
import ctypes
# https://github.com/PySimpleGUI/PySimpleGUI/issues/1179
# the location matters
ctypes.windll.shcore.SetProcessDpiAwareness(2)

from functools import partial
from multiprocessing import Process
from pathlib import Path
from time import sleep
from typing import Literal

import io
import cv2
import mss
import numpy as np
import psutil
import pyautogui
import requests
import uvicorn
import win32gui
import win32process
import yaml
from fastapi import FastAPI
from hotkey import add_hotkey
from UltraDict import UltraDict
from starlette.responses import StreamingResponse

TRAY_WIDTH = 800
TRAY_HEIGHT = 80
INTERVAL = 0.7
NUM_IMAGES_DETECTING_FLASHING = 5
THRESHOLD = 0.98

template = {
    key:
    cv2.imread(
        str(
            Path(__file__).parent.parent / 'image' / 'template' /
            f'{key}.png'))
    for key in ['tim-new-message', 'tim-no-message', 'wechat-no-message']
}

logging.basicConfig(level=logging.DEBUG, format="[%(asctime)s] %(message)s")

app = FastAPI()

db = UltraDict(name='vm-sync')


@app.get("/")
def hello():
    return 'Hello from Windows'


def take_screenshot():
    with mss.mss() as sct:
        screen = sct.monitors[0]
        assert screen['width'] > TRAY_WIDTH, 'Screen size too small'
        assert screen['height'] > TRAY_HEIGHT, 'Screen size too small'
        area = {
            'left': screen['width'] - TRAY_WIDTH,
            'top': screen['height'] - TRAY_HEIGHT,
            'width': TRAY_WIDTH,
            'height': TRAY_HEIGHT,
        }
        sct_img = sct.grab(area)
    image = np.asarray(sct_img)[:, :, :3]
    return image, screen


def locate_template(image, template):
    """
    locate the smaller image (template) in the larger image
    """
    result = cv2.matchTemplate(image, template, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
    h, w = template.shape[0], template.shape[1]
    return max_val, (max_loc[0] + w // 2, max_loc[1] + h // 2)


def update_status():
    db[('status', 'tim')] = 'not_found'
    db[('status', 'wechat')] = 'not_found'
    db[('coordinates', 'tim')] = None
    db[('coordinates', 'wechat')] = None

    wechat_locating_results = []
    while True:
        try:
            image, screen = take_screenshot()
        except Exception as e:
            logging.error(f'Error while taking screenshot: {repr(e)}')
            sleep(INTERVAL)
            continue

        def offset_cooridate(cooridate):
            return (cooridate[0] + screen['width'] - TRAY_WIDTH,
                    cooridate[1] + screen['height'] - TRAY_HEIGHT)

        # TIM
        no_message_locating_result = locate_template(
            image, template['tim-no-message'])
        no_message = no_message_locating_result[0] > THRESHOLD
        new_message_locating_result = locate_template(
            image, template['tim-new-message'])
        new_message = new_message_locating_result[0] > THRESHOLD
        logging.debug(
            f'TIM: (no) {no_message_locating_result}, (new) {new_message_locating_result}'
        )

        if no_message and not new_message:
            db[('status', 'tim')] = 'no_message'
            db[('coordinates',
                'tim')] = offset_cooridate(no_message_locating_result[1])
        elif not no_message and new_message:
            db[('status', 'tim')] = 'new_message'
            db[('coordinates',
                'tim')] = offset_cooridate(new_message_locating_result[1])
        elif no_message and new_message:
            db[('status', 'tim')] = 'unknown_error'
        elif not no_message and not new_message:
            db[('status', 'tim')] = 'not_found'

        wechat_locating_results.append(
            locate_template(image, template['wechat-no-message']))
        logging.debug(f'WeChat: {wechat_locating_results[-1]}')

        # WeChat
        if len(wechat_locating_results) > NUM_IMAGES_DETECTING_FLASHING:
            wechat_locating_results.pop(0)
            wechat_displayed = [
                x for x in wechat_locating_results if x[0] > THRESHOLD
            ]
            wechat_displayed_count = len(wechat_displayed)
            wechat_hidden_count = len(
                wechat_locating_results) - wechat_displayed_count
            if wechat_displayed_count >= 1 and wechat_hidden_count >= 1:
                db[('status', 'wechat')] = 'new_message'
                db[('coordinates',
                    'wechat')] = offset_cooridate(wechat_displayed[-1][1])
            elif wechat_displayed_count == len(wechat_locating_results):
                db[('status', 'wechat')] = 'no_message'
                db[('coordinates',
                    'wechat')] = offset_cooridate(wechat_displayed[-1][1])
            elif wechat_hidden_count == len(wechat_locating_results):
                db[('status', 'wechat')] = 'not_found'
            else:
                db[('status', 'wechat')] = 'unknown_error'

        logging.debug(f'{list(db.items()) = }')

        sleep(INTERVAL)


App = Literal['tim', 'wechat']


@app.get("/status/{app_name}")
def get_status(app_name: App):
    try:
        return db[('status', app_name)]
    except KeyError:
        return 'unknown_error'


@app.get("/active")
def get_active():
    cwnd = win32gui.GetForegroundWindow()
    _, pid = win32process.GetWindowThreadProcessId(cwnd)
    process = psutil.Process(pid)
    logging.info(f'Current active process: {process}')
    return process.exe()


@app.get("/screenshot")
def get_screenshot():
    image, _ = take_screenshot()
    _, png = cv2.imencode(".png", image)
    return StreamingResponse(io.BytesIO(png.tobytes()), media_type="image/png")


@app.post("/open/{app_name}")
def open_app(app_name: App):
    if app_name == 'tim':
        if db[('status', 'tim')] in ['no_message', 'new_message']:
            logging.info(
                'TIM already opened, click the tray icon to restore the window'
            )
            pyautogui.click(*db[('coordinates', 'tim')])
            return

        logging.info('TIM not opened, run the exe')
        subprocess.Popen(r'C:\\Program Files (x86)\\Tencent\\TIM\Bin\\TIM.exe')

    elif app_name == 'wechat':
        if db[('status', 'wechat')] in ['no_message', 'new_message']:
            logging.info(
                'WeChat already opened, click the tray icon to restore the window'
            )
            pyautogui.click(*db[('coordinates', 'wechat')])
            return

        logging.info('WeChat not opened, run the exe')
        subprocess.Popen(
            r'C:\\Program Files (x86)\\Tencent\\WeChat\\WeChat.exe')


with open(Path(__file__).parent.parent / 'config.yaml') as f:
    config = yaml.safe_load(f)


def hotkey_callback(hotkey):
    logging.info(f"{hotkey} suppressed in VM")
    requests.post(
        f"http://{config['linux']['host']}:{config['linux']['port']}/keypress/{hotkey}"
    )


if __name__ == '__main__':
    for x in config['capture-hotkey']:
        Process(target=add_hotkey,
                args=(
                    x['keycodes'],
                    partial(hotkey_callback, x['hotkey']),
                )).start()

    Process(target=update_status).start()

    uvicorn.run("main:app",
                host=config['windows']['host'],
                port=config['windows']['port'],
                log_level='warning')
