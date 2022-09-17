import wx.adv
import wx
from multiprocessing import Process


# https://stackoverflow.com/questions/6389580/quick-and-easy-trayicon-with-python
class TaskBarIcon(wx.adv.TaskBarIcon):

    def __init__(self, frame, icon_path, default_name, default_callback,
                 exit_name, exit_callback):
        self.frame = frame
        super().__init__()
        self.set_icon(icon_path)
        self.Bind(wx.adv.EVT_TASKBAR_LEFT_DOWN, default_callback)
        self.default_name = default_name
        self.default_callback = default_callback
        self.exit_name = exit_name
        self.exit_callback = exit_callback

    @staticmethod
    def create_menu_item(menu, label, func):
        item = wx.MenuItem(menu, -1, label)
        menu.Bind(wx.EVT_MENU, func, id=item.GetId())
        menu.Append(item)
        return item

    def CreatePopupMenu(self):
        menu = wx.Menu()
        self.create_menu_item(menu, self.default_name, self.default_callback)
        self.create_menu_item(menu, self.exit_name, self.exit_callback)
        return menu

    def set_icon(self, path):
        icon = wx.Icon(path)
        self.SetIcon(icon)


class TrayIconInstance(wx.App):

    def __init__(
            self,
            icon_path,
            default_name='Open',
            default_callback=lambda: print('Open'),
            exit_name='Exit',
            exit_callback=lambda: print('Exit'),
    ):
        self.icon_path = icon_path
        self.default_name = default_name
        self.default_callback = lambda _: default_callback()
        self.exit_name = exit_name
        self.exit_callback = lambda _: exit_callback()
        super().__init__()

    def OnInit(self):
        frame = wx.Frame(None)
        self.SetTopWindow(frame)
        self.task_bar_icon = TaskBarIcon(frame, self.icon_path,
                                         self.default_name,
                                         self.default_callback, self.exit_name,
                                         self.exit_callback)
        return True


class TrayIcon:

    def __init__(self, *args):
        self.args = args
        self._set(args)

    def _set(self, args):
        self.current_icon = args[0]
        if args[0] is None:
            self.p = None
        else:
            self.p = Process(target=lambda: TrayIconInstance(*args).MainLoop())
            self.p.start()

    def set_icon(self, path):
        if path != self.current_icon:
            if self.p is not None:
                self.p.kill()
            self._set([path, *self.args[1:]])


if __name__ == '__main__':

    app = TrayIcon('/home/yu/code/vm-sync/image/icon/tim-no-message.png',
                   'tim', lambda: print('Tim'), 'exit', lambda: print('exit'))
    from time import sleep
    while True:
        sleep(1)
        app.set_icon('/home/yu/code/vm-sync/image/icon/tim-new-message.png')
        sleep(1)
        app.set_icon('/home/yu/code/vm-sync/image/icon/tim-new-message.png')
        sleep(1)
        app.set_icon('/home/yu/code/vm-sync/image/icon/wechat-no-message.png')
