import tkinter
from tkinter import messagebox, TclError


def message_box_action(action, message='Do?', timeout=3000, default=True):
    root = tkinter.Tk()
    root.withdraw()
    root.after(timeout, root.destroy)

    answer = default
    try:
        answer = messagebox.askyesno(
            '', f"{message} (timeout: {timeout}, default: {default})")

    except TclError:
        pass

    if answer:
        action()


if __name__ == '__main__':
    message_box_action(lambda: print('wtf'))
