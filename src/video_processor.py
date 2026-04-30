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
            if os.path.exists(out_path):
                try:
                    os.remove(out_path)
                except OSError:
                    pass
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
            if os.path.exists(out_path):
                try:
                    os.remove(out_path)
                except OSError:
                    pass
            return -1, "", 0.0
        if rc != 0:
            if os.path.exists(out_path):
                try:
                    os.remove(out_path)
                except OSError:
                    pass
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
            
            if size_b > target_size:
                # Estimasi kualitas target (500 KB) menggunakan rasio atau interpolasi linear
                target_kb = target_size / 1024.0
                
                if len(tried_qualities) >= 2:
                    # Interpolasi linear antara dua percobaan terakhir
                    qs = list(tried_qualities.keys())
                    q1, q2 = qs[-2], qs[-1]
                    s1, s2 = tried_qualities[q1], tried_qualities[q2]
                    
                    if abs(s1 - s2) > 0.1:
                        # Rumus interpolasi: q = q1 + (target_s - s1) * (q2 - q1) / (s2 - s1)
                        estimated_q = q1 + (target_kb - s1) * (q2 - q1) / (s2 - s1)
                        next_q = int(round(estimated_q))
                    else:
                        next_q = current_quality - 5
                else:
                    # Estimasi awal berbasis rasio (dengan faktor redaman 0.8 agar tidak terlalu drastis)
                    ratio = size_kb / target_kb
                    next_q = int(current_quality / (ratio ** 0.6))
                
                # Pastikan ada perubahan minimal 1 poin dan maksimal lompatan 30 poin
                if next_q >= current_quality:
                    next_q = current_quality - 1
                if current_quality - next_q > 30:
                    next_q = current_quality - 30
                    
                current_quality = max(1, next_q)
            else:
                # Sudah di bawah target, coba dekati 500 KB jika masih memungkinkan
                if size_kb < 480: # Hanya jika masih ada ruang untuk naik
                    target_kb = target_size / 1024.0
                    if len(tried_qualities) >= 2:
                        qs = list(tried_qualities.keys())
                        q1, q2 = qs[-2], qs[-1]
                        s1, s2 = tried_qualities[q1], tried_qualities[q2]
                        if abs(s1 - s2) > 0.1:
                            estimated_q = q1 + (target_kb - s1) * (q2 - q1) / (s2 - s1)
                            next_q = int(round(estimated_q))
                        else:
                            next_q = current_quality + 1
                    else:
                        next_q = current_quality + 2
                    
                    if next_q <= current_quality:
                        next_q = current_quality + 1
                    current_quality = min(100, next_q)
                else:
                    # Sudah sangat dekat (480-500 KB)
                    return 0, out_path, size_kb
        
        iteration += 1

    # Jika keluar loop, gunakan yang terbaik yang pernah ditemukan
    if best_quality > 0:
        # Jika file terakhir bukan yang terbaik, render ulang sekali lagi dengan kualitas terbaik
        if current_quality != best_quality:
             cmd[-5] = str(best_quality) # Update qscale
             run_proc_and_wait(cmd, cancel_check_func)
        return 0, out_path, best_size_kb
    
    # Jika sampai sini berarti gagal menemukan kualitas yang pas di bawah target
    if os.path.exists(out_path):
        try:
            os.remove(out_path)
        except OSError:
            pass
            
    return -2, "", 0.0
