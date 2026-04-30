import os
import shutil
import subprocess
import time
from datetime import datetime
from typing import List, Callable

def fmt_ts() -> str:
    """
    Menghasilkan timestamp string dengan format YYYYMMDDHHMMSS.

    Returns:
        str: String timestamp saat ini.
    """
    return datetime.now().strftime("%Y%m%d%H%M%S")

def safe_mkdir(p: str) -> None:
    """
    Membuat direktori secara aman jika belum ada.

    Args:
        p (str): Path direktori yang akan dibuat.
    """
    os.makedirs(p, exist_ok=True)

def check_ffmpeg() -> bool:
    """
    Memeriksa apakah FFmpeg tersedia di sistem PATH.

    Returns:
        bool: True jika FFmpeg ditemukan, False jika tidak.
    """
    if shutil.which("ffmpeg") is None:
        return False
    return True

def run_proc_and_wait(args: List[str], cancel_check_func: Callable[[], bool]) -> int:
    """
    Menjalankan proses subprocess dan menunggu hingga selesai atau dibatalkan.

    Args:
        args (List[str]): Argumen perintah untuk dijalankan.
        cancel_check_func (Callable): Fungsi untuk memeriksa apakah pembatalan diminta.

    Returns:
        int: Return code dari proses (0 untuk sukses, -1 untuk dibatalkan, -2 untuk error file).
    """
    try:
        p = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        while True:
            if cancel_check_func():
                try:
                    p.terminate()
                except Exception:
                    pass
                return -1
            ret = p.poll()
            if ret is not None:
                return ret
            time.sleep(0.05)
    except FileNotFoundError:
        return -2
