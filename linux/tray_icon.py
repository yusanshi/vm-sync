import wx
import wx.adv
import wx.lib.newevent
from threading import Thread


class TaskBarIcon(wx.adv.TaskBarIcon):

    def __init__(self, frame, icon, action, CustomEventBinder):
        self.frame = frame
        wx.adv.TaskBarIcon.__init__(self)
        self.OnSetIcon(icon)
        self.Bind(CustomEventBinder, lambda e: self.OnSetIcon(e.path))
        self.Bind(wx.adv.EVT_TASKBAR_LEFT_DOWN, lambda _: action())

    def OnSetIcon(self, path):
        icon = wx.Icon(path)
        self.SetIcon(icon)


class TrayIcon:

    def __init__(self, icon, action):
        self.CustomEvent, CustomEventBinder = wx.lib.newevent.NewEvent()
        app = wx.App()
        frame = wx.Frame(None)
        self.task_bar_icon = TaskBarIcon(frame, icon, action,
                                         CustomEventBinder)
        Thread(target=app.MainLoop).start()

    def change_icon(self, path):
        wx.PostEvent(self.task_bar_icon, self.CustomEvent(path=path))


if __name__ == '__main__':
    from time import sleep

    def work():
        icon = TrayIcon("image/icon/wechat-gray.png", lambda: print('fff'))
        # TODO: multiple instance in one process is not supported
        # icon2 = TrayIcon("image/icon/wechat-gray.png", lambda: print('fff'))
        while True:
            sleep(0.2)
            icon.change_icon("image/icon/wechat-gray.png")
            sleep(0.2)
            icon.change_icon("image/icon/tim-gray.png")

    from multiprocessing import Process
    Process(target=work).start()

    sleep(0.1)
    Process(target=work).start()
    print('ff')
