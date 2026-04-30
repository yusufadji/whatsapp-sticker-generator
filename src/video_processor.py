import os
import cv2
import math
import numpy as np
from typing import List, Tuple, Callable, Optional
from src.helpers import fmt_ts, run_proc_and_wait, safe_mkdir

def extract_video_frames(video_path: str) -> Tuple[List[np.ndarray], float]:
    """
    Mengekstrak semua frame dari file video.

    Args:
        video_path (str): Path ke file video.

    Returns:
        Tuple[List[np.ndarray], float]: Daftar frame (sebagai array numpy) dan FPS video.
    """
    frames = []
    cap = cv2.VideoCapture(video_path)
    
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0 or math.isnan(fps):
        fps = 30.0

    while True:
        ok, frm = cap.read()
        if not ok:
            break
        frames.append(frm)
    cap.release()
    
    return frames, fps

def render_sticker(
    video_path: str,
    start_time: float,
    end_time: float,
    initial_quality: int,
    target_size: int,
    quality_step: int,
    cancel_check_func: Callable[[], bool],
    progress_callback: Optional[Callable[[str], None]] = None
) -> Tuple[int, str, float]:
    """
    Merender stiker WhatsApp menggunakan FFmpeg dengan kompresi otomatis.

    Args:
        video_path (str): Path ke video sumber.
        start_time (float): Waktu mulai dalam detik.
        end_time (float): Waktu akhir dalam detik.
        initial_quality (int): Kualitas awal (1-100).
        target_size (int): Target ukuran file maksimal (byte).
        quality_step (int): Pengurangan kualitas setiap iterasi.
        cancel_check_func (Callable): Fungsi untuk cek pembatalan.
        progress_callback (Optional[Callable]): Fungsi opsional untuk update status.

    Returns:
        Tuple[int, str, float]: (status_code, output_path, final_size_kb)
            status_code: 0 sukses, -1 dibatalkan, -2 error.
    """
    current_quality = initial_quality
    safe_mkdir("output")
    out_name = f"wa_sticker_{fmt_ts()}.webp"
    out_path = os.path.join("output", out_name)
    iteration = 1

    while True:
        if cancel_check_func():
            return -1, "", 0.0

        # FFmpeg khusus WhatsApp: 512x512, 30 FPS, Crop 1:1
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-ss", f"{start_time:.3f}",
            "-to", f"{end_time:.3f}",
            "-vf", "crop='min(iw,ih)':'min(iw,ih)',scale=512:512,fps=30",
            "-c:v", "libwebp",
            "-loop", "0",
            "-lossless", "0",
            "-qscale", str(current_quality),
            "-an", 
            out_path
        ]

        rc = run_proc_and_wait(cmd, cancel_check_func)
        
        if rc == -1:
            return -1, "", 0.0
        if rc != 0:
            return -2, "", 0.0

        size_b = os.path.getsize(out_path)
        if progress_callback:
            progress_callback(f"[Iterasi {iteration}] Kualitas: {current_quality} | Ukuran: {size_b/1024:.2f} KB\n")

        if size_b <= target_size:
            return 0, out_path, size_b / 1024.0
            
        current_quality -= quality_step
        iteration += 1
        if current_quality <= 0:
            return -2, out_path, size_b / 1024.0
