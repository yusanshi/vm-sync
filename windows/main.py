import logging
import subprocess
from multiprocessing import Process
from pathlib import Path
from time import sleep
from typing import Literal

import cv2
import keyboard
import mss
import numpy as np
import pyautogui
import requests
import uvicorn
import yaml
from fastapi import FastAPI
from sqlitedict import SqliteDict
import win32gui
import win32process
import psutil

TRAY_WIDTH = 800
TRAY_HEIGHT = 80
INTERVAL = 0.7
NUM_IMAGES_DETECTING_FLASHING = 5
THRESHOLD = 0.98

template = {
    key: cv2.imread(
        str(
            Path(__file__).parent.parent / 'image' / 'template' /
            f'{key}.png'))
    for key in ['tim-new-message', 'tim-no-message', 'wechat-no-message']
}

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(message)s")

app = FastAPI()

db_path = Path(__file__).parent / 'db.sqlite'
db = SqliteDict(db_path)

App = Literal['tim', 'wechat']
Status = Literal['no_message', 'new_message', 'not_found', 'unknown_error']


@app.get("/")
def hello():
    return 'Hello from Windows'


def locate_template(image, template):
    """
    locate the smaller image (template) in the larger image
    """
    result = cv2.matchTemplate(image, template, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
    h, w = template.shape[0], template.shape[1]
    return max_val, (max_loc[0] + w // 2, max_loc[1] + h // 2)


def update_status():
    db = SqliteDict(db_path, autocommit=True)
    db[str(('status', 'tim'))] = 'not_found'
    db[str(('status', 'wechat'))] = 'not_found'
    db[str(('coordinates', 'tim'))] = None
    db[str(('coordinates', 'wechat'))] = None

    images = []
    wechat_locating_results = []
    while True:
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
            db[str(('status', 'tim'))] = 'no_message'
            db[str(('coordinates',
                    'tim'))] = offset_cooridate(no_message_locating_result[1])
        elif not no_message and new_message:
            db[str(('status', 'tim'))] = 'new_message'
            db[str(('coordinates',
                    'tim'))] = offset_cooridate(new_message_locating_result[1])
        elif no_message and new_message:
            db[str(('status', 'tim'))] = 'unknown_error'
        elif not no_message and not new_message:
            db[str(('status', 'tim'))] = 'not_found'

        images.append(image)
        wechat_locating_results.append(
            locate_template(image, template['wechat-no-message']))
        logging.debug(f'WeChat: {wechat_locating_results[-1]}')
        if len(images) > NUM_IMAGES_DETECTING_FLASHING:
            images.pop(0)
            wechat_locating_results.pop(0)

        # WeChat
        if len(wechat_locating_results) >= NUM_IMAGES_DETECTING_FLASHING:
            wechat_displayed = [
                x for x in wechat_locating_results if x[0] > THRESHOLD
            ]
            wechat_displayed_count = len(wechat_displayed)
            wechat_hidden_count = len(
                wechat_locating_results) - wechat_displayed_count
            if wechat_displayed_count >= 1 and wechat_hidden_count >= 1:
                db[str(('status', 'wechat'))] = 'new_message'
                db[str(('coordinates',
                        'wechat'))] = offset_cooridate(wechat_displayed[-1][1])
            elif wechat_displayed_count == len(wechat_locating_results):
                db[str(('status', 'wechat'))] = 'no_message'
                db[str(('coordinates',
                        'wechat'))] = offset_cooridate(wechat_displayed[-1][1])
            elif wechat_hidden_count == len(wechat_locating_results):
                db[str(('status', 'wechat'))] = 'not_found'
            else:
                db[str(('status', 'wechat'))] = 'unknown_error'

        logging.debug(f'{list(db.items()) = }')

        sleep(INTERVAL)


@app.get("/status/{app_name}")
def get_status(app_name: App):
    return db[str(('status', app_name))]


@app.get("/open/{app_name}")
def open_app(app_name: App):
    if app_name == 'tim':
        if db[str(('status', 'tim'))] in ['no_message', 'new_message']:
            logging.info(
                'TIM already opened, click the tray icon to restore the window'
            )
            pyautogui.click(*db[str(('coordinates', 'tim'))])
            return

        logging.info('TIM not opened, run the exe')
        subprocess.Popen(r'C:\\Program Files (x86)\\Tencent\\TIM\Bin\\TIM.exe')

    elif app_name == 'wechat':
        if db[str(('status', 'wechat'))] in ['no_message', 'new_message']:
            logging.info(
                'WeChat already opened, click the tray icon to restore the window'
            )
            pyautogui.click(*db[str(('coordinates', 'wechat'))])
            return

        logging.info('WeChat not opened, run the exe')
        subprocess.Popen(
            r'C:\\Program Files (x86)\\Tencent\\WeChat\\WeChat.exe')


with open(Path(__file__).parent.parent / 'config.yaml') as f:
    config = yaml.safe_load(f)


def current_active_window_executable():
    cwnd = win32gui.GetForegroundWindow()
    _, pid = win32process.GetWindowThreadProcessId(cwnd)
    for proc in psutil.process_iter():
        if proc.pid == pid:
            logging.info(f'Current active process: {proc}')
            return proc.exe()
    return None


def forward_keypress(keypress):
    if keypress == 'alt+w':
        if '\\Tencent\\WeChat\\' not in current_active_window_executable():
            open_app('wechat')
            return
        keypress = 'command:hide'
    elif keypress == 'alt+q':
        if '\\Tencent\\TIM\\' not in current_active_window_executable():
            open_app('tim')
            return
        keypress = 'command:hide'

    logging.info(f"Forward keypress {keypress}")
    requests.post(
        f"http://{config['linux']['host']}:{config['linux']['port']}/keyboard/{keypress}"
    )


if __name__ == '__main__':
    for keypress in config['forward']['keypress']:
        logging.info(f"Register forwarding for keypress {keypress}")
        keyboard.add_hotkey(keypress,
                            forward_keypress,
                            args=[keypress],
                            suppress=True)

    Process(target=update_status).start()

    uvicorn.run("main:app",
                host=config['windows']['host'],
                port=config['windows']['port'],
                log_level='warning')
