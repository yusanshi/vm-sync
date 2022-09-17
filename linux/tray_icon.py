import wx.adv
import wx
from multiprocessing import Process


# https://stackoverflow.com/questions/6389580/quick-and-easy-trayicon-with-python
class TrayIconInstance(wx.App):

    def __init__(self, icon_path, action=lambda: print('Open')):
        self.icon_path = icon_path
        self.action = lambda _: action()
        super().__init__()

    def OnInit(self):
        wx.Frame(None)
        self.task_bar_icon = wx.adv.TaskBarIcon()
        self.task_bar_icon.Bind(wx.adv.EVT_TASKBAR_LEFT_DOWN, self.action)
        icon = wx.Icon(self.icon_path)
        self.task_bar_icon.SetIcon(icon)
        return True


class TrayIcon:

    def __init__(self, *args):
        self.args = args
        self.current_icon = args[0]
        self.p = Process(target=lambda: TrayIconInstance(*args).MainLoop())
        self.p.start()

    def set_icon(self, path):
        if path != self.current_icon:
            self.p.kill()
            self.p = Process(target=lambda: TrayIconInstance(
                *[path, *self.args[1:]]).MainLoop())
            self.p.start()
            self.current_icon = path


if __name__ == '__main__':

    app = TrayIcon('/home/yu/code/vm-sync/image/icon/tim-no-message.png',
                   lambda: print('Open TIM'))
    from time import sleep
    while True:
        sleep(2)
        app.set_icon('/home/yu/code/vm-sync/image/icon/tim-new-message.png')
        sleep(2)
        app.set_icon('/home/yu/code/vm-sync/image/icon/tim-new-message.png')
        sleep(2)
        app.set_icon('/home/yu/code/vm-sync/image/icon/wechat-no-message.png')
