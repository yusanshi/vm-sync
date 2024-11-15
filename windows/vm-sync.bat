rem run `shell:startup` and put this file there
if not DEFINED IS_MINIMIZED set IS_MINIMIZED=1 && start "" /min "%~dpnx0" %* && exit
  python C:\path\to\vm-sync\windows\main.py
exit
