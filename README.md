### 打包
使用如下命令打包：
```bash
uv run config/build.sh  # Linux/macOS
./config/build.ps1 # Windows PowerShell/cmd
```

- 打包脚本在 `config` 目录下，分别为 `build.sh` 和 `build.ps1`
- 打包后的文件在 `dist` 目录下
- 打包后的文件为 `exe` 文件，需要在 Windows 系统下运行
