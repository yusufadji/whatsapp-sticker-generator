import os
import cv2
import math
import numpy as np
from typing import List, Tuple, Callable, Optional
from src.helpers import fmt_ts, run_proc_and_wait, safe_mkdir

def get_video_duration(video_path: str) -> float:
    """
    Mendapatkan durasi video dalam detik tanpa mengekstrak semua frame.

    Args:
        video_path (str): Path ke file video.

    Returns:
        float: Durasi video dalam detik.
    """
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    cap.release()
    
    if fps <= 0 or math.isnan(fps):
        fps = 30.0
        
    return float(frame_count / fps) if fps > 0 else 0.0

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
    progress_callback: Optional[Callable[[str], None]] = None,
    adaptive_mode: bool = False
) -> Tuple[int, str, float]:
    """
    Merender stiker WhatsApp menggunakan FFmpeg dengan kompresi otomatis/adaptif.

    Args:
        video_path (str): Path ke video sumber.
        start_time (float): Waktu mulai dalam detik.
        end_time (float): Waktu akhir dalam detik.
        initial_quality (int): Kualitas awal (1-100).
        target_size (int): Target ukuran file maksimal (byte).
        quality_step (int): Pengurangan kualitas setiap iterasi (diabaikan jika adaptive_mode=True).
        cancel_check_func (Callable): Fungsi untuk cek pembatalan.
        progress_callback (Optional[Callable]): Fungsi opsional untuk update status.
        adaptive_mode (bool): Jika True, gunakan pencarian kualitas cerdas.

    Returns:
        Tuple[int, str, float]: (status_code, output_path, final_size_kb)
    """
    current_quality = initial_quality
    safe_mkdir("output")
    out_name = f"wa_sticker_{fmt_ts()}.webp"
    out_path = os.path.join("output", out_name)
    
    iteration = 1
    best_size_kb = 0.0
    best_quality = 0
    
    tried_qualities = {} # quality -> size_kb

    while iteration <= 40: # Meningkatkan batas iterasi untuk memastikan konvergensi
        if cancel_check_func():
            return -1, "", 0.0
            
        if current_quality in tried_qualities or current_quality < 1 or current_quality > 100:
            break

        # FFmpeg render
        cmd = [
            "ffmpeg", "-y", "-i", video_path,
            "-ss", f"{start_time:.3f}", "-to", f"{end_time:.3f}",
            "-vf", "crop='min(iw,ih)':'min(iw,ih)',scale=512:512,fps=30",
            "-c:v", "libwebp", "-loop", "0", "-lossless", "0",
            "-qscale", str(current_quality), "-an", out_path
        ]

        rc = run_proc_and_wait(cmd, cancel_check_func)
        if rc == -1:
            return -1, "", 0.0
        if rc != 0:
            return -2, "", 0.0

        size_b = os.path.getsize(out_path)
        size_kb = size_b / 1024.0
        tried_qualities[current_quality] = size_kb
        
        if progress_callback:
            progress_callback(f"[Iterasi {iteration}] Kualitas: {current_quality} | Ukuran: {size_kb:.2f} KB\n")

        # Update best so far (yang di bawah target tapi paling besar)
        if size_b <= target_size:
            if size_kb > best_size_kb:
                best_size_kb = size_kb
                best_quality = current_quality
                # Simpan copy file terbaik jika perlu, tapi di sini kita hanya timpa out_path saja untuk efisiensi
        
        if not adaptive_mode:
            if size_b <= target_size:
                return 0, out_path, size_kb
            current_quality -= quality_step
        else:
            # Logika Adaptif
            size_b - target_size
            
            if size_b > target_size:
                # Terlalu besar, kurangi kualitas secara agresif/presisi
                if size_b > 1024 * 1024: # > 1 MB (Ekstrem)
                    step = 20
                elif size_b > 750 * 1024: # 750KB - 1MB
                    step = 10
                elif size_b > 600 * 1024: # 600KB - 750KB
                    step = 5
                else: # 500KB - 600KB
                    step = 1
                current_quality -= step
            else:
                # Sudah di bawah target, tapi apakah bisa lebih dekat?
                if size_kb < 400: # Terlalu kecil (jauh dari 500KB)
                    current_quality += 3
                elif size_kb < 470: # Agak kecil
                    current_quality += 1
                else:
                    # Sudah sangat dekat (470-500 KB)
                    return 0, out_path, size_kb
        
        iteration += 1

    # Jika keluar loop, gunakan yang terbaik yang pernah ditemukan
    if best_quality > 0:
        # Jika file terakhir bukan yang terbaik, render ulang sekali lagi dengan kualitas terbaik
        if current_quality != best_quality:
             cmd[-5] = str(best_quality) # Update qscale
             run_proc_and_wait(cmd, cancel_check_func)
        return 0, out_path, best_size_kb
        
    return -2, out_path, size_kb
