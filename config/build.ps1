pyinstaller --clean --onefile --windowed `
    --hidden-import=win32timezone `
    --upx-dir="D:/Programs/upx-5.0.1-win64" `
    --add-data="app.ico;." `
    --icon="app.ico" `
    --name=CmdManager.exe `
    main.py