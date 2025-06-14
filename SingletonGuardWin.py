import win32con
import win32file
import pywintypes
import winerror
import sys


# singleton guardian for windows
class SingletonGuardWin:
    def __init__(self, lock_file_path: str):
        self._lock_file_path = lock_file_path
        self._lock_file = None

    def _acquire_lock(self):
        try:
            # 创建一个文件用于锁定
            self._lock_file = win32file.CreateFile(
                self._lock_file_path,
                win32file.GENERIC_WRITE,
                0,
                None,
                win32file.CREATE_ALWAYS,
                win32file.FILE_ATTRIBUTE_NORMAL,
                None,
            )

            # 尝试获取文件锁
            win32file.LockFileEx(
                self._lock_file,
                win32con.LOCKFILE_EXCLUSIVE_LOCK | win32con.LOCKFILE_FAIL_IMMEDIATELY,
                0,
                -0x10000,
                pywintypes.OVERLAPPED(),
            )

            return True
        except pywintypes.error as e:
            if (
                e.winerror == winerror.ERROR_LOCK_VIOLATION
                or e.winerror == winerror.ERROR_SHARING_VIOLATION
                or e.winerror == winerror.ERROR_LOCK_FAILED
            ):
                return False
            else:
                raise

    def _release_lock(self):
        if self._lock_file:
            win32file.UnlockFileEx(
                self._lock_file, 0, -0x10000, pywintypes.OVERLAPPED()
            )
            win32file.CloseHandle(self._lock_file)

    def is_already_running(self):
        return not self._acquire_lock()

    def __enter__(self):
        if self.is_already_running():
            print("Another instance is already running.")
            sys.exit(1)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._release_lock()

    def guard(self):
        return self.__enter__()

    def release(self):
        self._release_lock()
