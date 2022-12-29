from pynput.keyboard import Listener


def add_hotkey(keycodes, callback):
    # TODO: exclude the modifier keys, e.g., pressing ctrl+shift+x should not trigger ctrl+x callback
    status = {x: False for x in keycodes}

    def win32_event_filter(msg, data):
        if data.vkCode in status:
            if msg == 256 or msg == 260:  # key down
                status[data.vkCode] = True
                if all(status.values()):
                    listener._suppress = True
                    callback()
                    return

            elif msg == 257 or msg == 261:  # key up
                status[data.vkCode] = False

        listener._suppress = False

    with Listener(win32_event_filter=win32_event_filter) as listener:
        listener.join()


if __name__ == '__main__':
    from multiprocessing import Process

    def func():
        print('hahaha')

    # key codes from https://learn.microsoft.com/en-us/windows/win32/inputdev/virtual-key-codes
    Process(
        target=add_hotkey,
        args=(
            [0xA2, 0x20],  # ctrl+space
            func)).start()
    Process(
        target=add_hotkey,
        args=(
            [0x70],  # f1
            func)).start()
    print('fff')
