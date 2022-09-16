from time import sleep
from pathlib import Path
import mss
import numpy as np
import cv2
import logging
from datetime import datetime
import requests
import yaml

TRAY_WIDTH = 800
TRAY_HEIGHT = 80
SHORT_INTERVAL = 0.3
LONG_INTERVAL = 1.5
NUM_IMAGES_EACH_CHECK = 4
THRESHOLD = 0.99

template = {
    key: cv2.imread(
        str(
            Path(__file__).parent.parent / 'image' / 'template' /
            f'{key}.png'))
    for key in ['tim-new-message', 'tim-no-message', 'wechat-no-message']
}

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

with open(Path(__file__).parent.parent / 'config.yaml') as f:
    config = yaml.safe_load(f)
status_url = f"http://{config['linux']['host']}:{config['linux']['port']}/status"

while True:
    images = []
    for _ in range(NUM_IMAGES_EACH_CHECK):
        sleep(SHORT_INTERVAL)
        image = get_tray_image()
        images.append(image)

    # TIM
    tim_no_message_confidence = cv2.matchTemplate(images[-1],
                                                  template['tim-no-message'],
                                                  cv2.TM_CCOEFF_NORMED).max()
    tim_no_message = tim_no_message_confidence > THRESHOLD
    tim_new_message_confidence = cv2.matchTemplate(images[-1],
                                                   template['tim-new-message'],
                                                   cv2.TM_CCOEFF_NORMED).max()
    tim_new_message = tim_new_message_confidence > THRESHOLD
    logging.info(
        f'{tim_no_message_confidence = }, {tim_new_message_confidence = }')
    if tim_no_message and not tim_new_message:
        status = 'no_message'
    elif not tim_no_message and tim_new_message:
        status = 'new_message'
    elif tim_no_message and tim_new_message:
        status = 'unknown_error'
    elif not tim_no_message and not tim_new_message:
        status = 'not_found'
    data = {'name': 'tim', 'status': status}
    logging.info(data)
    try:
        requests.post(status_url, json=data)
    except requests.exceptions.ConnectionError:
        pass  # TODO

    # WeChat
    wechat_confidences = [
        cv2.matchTemplate(image, template['wechat-no-message'],
                          cv2.TM_CCOEFF_NORMED).max() for image in images
    ]
    wechat_no_message = [x > THRESHOLD for x in wechat_confidences]
    logging.info(f'{wechat_confidences = }')
    wechat_true_count = wechat_no_message.count(True)
    wechat_false_count = wechat_no_message.count(False)
    if wechat_true_count >= 1 and wechat_false_count >= 1:
        status = 'new_message'
    elif wechat_true_count == NUM_IMAGES_EACH_CHECK:
        status = 'no_message'
    elif wechat_false_count == NUM_IMAGES_EACH_CHECK:
        status = 'not_found'
    else:
        status = 'unknown_error'
    data = {'name': 'wechat', 'status': status}
    logging.info(data)
    try:
        requests.post(status_url, json=data)
    except requests.exceptions.ConnectionError:
        pass  # TODO

    sleep(LONG_INTERVAL)
