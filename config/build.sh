#!/bin/bash
# build.sh
pyinstaller --clean --onefile --windowed \
    --hidden-import=win32timezone \
    --add-data="app.ico;." \
    --icon=app.ico \
    --name=CmdManager.exe \
    main.py
