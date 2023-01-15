# vm-sync

Add tray icons for IM apps (WeChat and TIM, currently) in Linux and sync the notification status of them from Windows virtual machine to Linux host.

Click the tray icons <del>or use the hotkey (`alt+w` for WeChat, `alt+q` for TIM)</del> to show or hide the apps in Windows virtual machine.


![image](https://user-images.githubusercontent.com/36265606/193278007-d6a0c542-9ccd-4d4c-8992-e389f8ca9071.png)

https://user-images.githubusercontent.com/36265606/193275913-c37843c5-5bca-4778-8f5c-5611cdb81415.mp4



My environments:
- Host: Ubuntu 22.04, GNOME 42, X11
- Guest: Windows 10 LTSC
- VM software: VirtualBox 6.1


Linux:
```bash
sudo apt install python3-tk xdotool
# https://wxpython.org/pages/downloads/
pip install -f https://extras.wxpython.org/wxPython4/extras/linux/gtk3/ubuntu-22.04 wxPython
```

Windows:

```bash
# Install Microsoft C++ Build Tools
https://visualstudio.microsoft.com/visual-cpp-build-tools/

pip install fastapi uvicorn PyAutoGUI UltraDict mss
```
