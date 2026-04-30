import os
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from tkinterdnd2 import TkinterDnD, DND_FILES
from PIL import Image, ImageTk
import cv2
import numpy as np
from typing import List, Optional

# Import modul internal
from src.helpers import check_ffmpeg
from src.video_processor import extract_video_frames, render_sticker

# ---------------------------
# Konfigurasi WhatsApp
# ---------------------------
TARGET_SIZE: int = 500 * 1024  # Maksimal 500 KB
QUALITY_STEP: int = 1          # Pengurangan kualitas jika file kebesaran

CANVAS_W: int = 520
CANVAS_H: int = 36
HANDLE_R: int = 9
PADDING: int = 12

# ---------------------------
# State Aplikasi
# ---------------------------
current_video_path: Optional[str] = None
video_fps: float = 30.0
frames: List[np.ndarray] = []
start_idx: int = 0
end_idx: int = 0
current_preview: int = 0

left_x: int = PADDING
right_x: int = CANVAS_W - PADDING

drag_left: bool = False
drag_right: bool = False

processing_thread: Optional[threading.Thread] = None
cancel_requested: bool = False
process_lock: threading.Lock = threading.Lock()

# ---------------------------
# Fungsi UI & Event Handlers
# ---------------------------

def handle_video_drop(video_path: str) -> None:
    """
    Menangani event drop file video ke aplikasi.

    Args:
        video_path (str): Path ke file video yang di-drop.
    """
    global frames, start_idx, end_idx, left_x, right_x
    global current_preview, current_video_path, video_fps

    video_path = video_path.strip("{}")
    current_video_path = video_path
    
    extracted_frames, fps = extract_video_frames(video_path)
    if not extracted_frames:
        messagebox.showerror("Error", "Gagal membaca frame video.")
        return

    frames = extracted_frames
    video_fps = fps
    start_idx = 0
    end_idx = len(frames) - 1
    current_preview = 0

    left_x = PADDING
    right_x = CANVAS_W - PADDING

    frame_slider.configure(to=max(0, len(frames) - 1))
    frame_slider.set(0)

    update_canvas()
    show_preview_frame(0)

def show_preview_frame(idx: int) -> None:
    """
    Menampilkan frame tertentu pada area preview.

    Args:
        idx (int): Indeks frame yang akan ditampilkan.
    """
    global current_preview
    if not frames:
        return
        
    idx = max(0, min(len(frames) - 1, int(idx)))
    current_preview = idx
    frm = frames[idx]
    
    # Konversi BGR ke RGB untuk PIL
    rgb = cv2.cvtColor(frm, cv2.COLOR_BGR2RGB)
    
    side = 320
    img = Image.fromarray(rgb)
    w, h = img.size
    side_crop = min(w, h)
    
    # Center crop
    left = (w - side_crop) // 2
    top = (h - side_crop) // 2
    img = img.crop((left, top, left + side_crop, top + side_crop))
    img = img.resize((side, side), Image.Resampling.LANCZOS)
    
    imgtk = ImageTk.PhotoImage(img)
    preview_label.configure(image=imgtk)
    preview_label.image = imgtk
    frame_index_label.config(text=f"{idx + 1} / {len(frames)}")

def canvas_pos_to_index(x: int) -> int:
    """
    Mengonversi posisi horizontal kanvas ke indeks frame.

    Args:
        x (int): Posisi x pada kanvas.

    Returns:
        int: Indeks frame yang sesuai.
    """
    if not frames:
        return 0
    x = max(PADDING, min(CANVAS_W - PADDING, x))
    ratio = (x - PADDING) / (CANVAS_W - 2 * PADDING)
    return max(0, min(len(frames) - 1, int(round(ratio * (len(frames) - 1)))))

def index_to_canvas_x(idx: int) -> int:
    """
    Mengonversi indeks frame ke posisi horizontal kanvas.

    Args:
        idx (int): Indeks frame.

    Returns:
        int: Posisi x pada kanvas.
    """
    if not frames:
        return PADDING
    ratio = idx / max(1, (len(frames) - 1))
    return PADDING + int(ratio * (CANVAS_W - 2 * PADDING))

def update_canvas() -> None:
    """
    Memperbarui tampilan kanvas range selector.
    """
    canvas.delete("all")
    # Track background
    canvas.create_rectangle(PADDING, CANVAS_H // 2 - 6, CANVAS_W - PADDING, CANVAS_H // 2 + 6, fill="#ddd", outline="")
    # Active range highlight
    canvas.create_rectangle(left_x, CANVAS_H // 2 - 6, right_x, CANVAS_H // 2 + 6, fill="#25D366", outline="")
    # Handles
    canvas.create_oval(left_x - HANDLE_R, CANVAS_H // 2 - HANDLE_R, left_x + HANDLE_R, CANVAS_H // 2 + HANDLE_R, fill="#fff", outline="#333", width=1)
    canvas.create_oval(right_x - HANDLE_R, CANVAS_H // 2 - HANDLE_R, right_x + HANDLE_R, CANVAS_H // 2 + HANDLE_R, fill="#fff", outline="#333", width=1)
    
    # Tick marks untuk video pendek
    if 0 < len(frames) <= 120:
        step = max(1, len(frames) // 40)
        for i in range(0, len(frames), step):
            x = index_to_canvas_x(i)
            canvas.create_line(x, CANVAS_H // 2 - 12, x, CANVAS_H // 2 + 12, fill="#bbb")
            
    s_idx = canvas_pos_to_index(left_x) if frames else 0
    e_idx = canvas_pos_to_index(right_x) if frames else 0
    canvas.create_text(PADDING + 40, CANVAS_H - 6, anchor="w", text=f"start: {s_idx + 1}", fill="#333")
    canvas.create_text(CANVAS_W - PADDING - 40, CANVAS_H - 6, anchor="e", text=f"end: {e_idx + 1}", fill="#333")

def on_canvas_press(event: tk.Event) -> None:
    """
    Menangani event klik mouse pada kanvas.
    """
    global drag_left, drag_right, left_x, right_x
    x = event.x
    if abs(x - left_x) <= HANDLE_R + 6:
        drag_left = True
    elif abs(x - right_x) <= HANDLE_R + 6:
        drag_right = True
    else:
        if x < CANVAS_W // 2:
            left_x = max(PADDING, min(right_x - (HANDLE_R * 2 + 6), x))
            show_preview_frame(canvas_pos_to_index(left_x))
        else:
            right_x = min(CANVAS_W - PADDING, max(left_x + (HANDLE_R * 2 + 6), x))
            show_preview_frame(canvas_pos_to_index(right_x))
    update_canvas()

def on_canvas_release(event: tk.Event) -> None:
    """
    Menangani event pelepasan klik mouse pada kanvas.
    """
    global drag_left, drag_right, start_idx, end_idx
    drag_left = drag_right = False
    start_idx = canvas_pos_to_index(left_x)
    end_idx = canvas_pos_to_index(right_x)
    frame_index_label.config(text=f"{current_preview + 1} / {len(frames)}")

def on_canvas_move(event: tk.Event) -> None:
    """
    Menangani event pergerakan mouse (drag) pada kanvas.
    """
    global left_x, right_x
    x = max(PADDING, min(CANVAS_W - PADDING, event.x))
    min_gap = (HANDLE_R * 2 + 6)
    if drag_left:
        left_x = min(x, right_x - min_gap)
        show_preview_frame(canvas_pos_to_index(left_x))
    elif drag_right:
        right_x = max(x, left_x + min_gap)
        show_preview_frame(canvas_pos_to_index(right_x))
    update_canvas()

def update_progress_ui(status_text: str) -> None:
    """
    Menambahkan pesan log ke console antarmuka.

    Args:
        status_text (str): Pesan status yang akan ditambahkan.
    """
    log_text.config(state="normal")
    log_text.insert(tk.END, status_text)
    log_text.see(tk.END)
    log_text.config(state="disabled")

def start_render_workflow() -> None:
    """
    Memulai alur kerja perenderan stiker di thread terpisah.
    """
    global processing_thread, cancel_requested
    if not current_video_path:
        return messagebox.showerror("Error", "Masukkan video dulu!")
    
    if not check_ffmpeg():
        return messagebox.showerror("Error", "FFmpeg tidak ditemukan di sistem!")

    start_btn.config(state="disabled")
    cancel_btn.config(state="normal")
    crf_entry.config(state="disabled")
    
    log_text.config(state="normal")
    log_text.delete("1.0", tk.END)
    log_text.insert(tk.END, "--- Memulai Proses ---\n")
    log_text.config(state="disabled")

    cancel_requested = False
    processing_thread = threading.Thread(target=background_render_task)
    processing_thread.start()

def background_render_task() -> None:
    """
    Tugas background untuk menjalankan proses render.
    """
    global cancel_requested
    
    try:
        s_time = start_idx / video_fps
        e_time = end_idx / video_fps
        
        try:
            initial_q = int(crf_entry.get())
        except ValueError:
            initial_q = 75

        status, out_path, size_kb = render_sticker(
            video_path=current_video_path,
            start_time=s_time,
            end_time=e_time,
            initial_quality=initial_q,
            target_size=TARGET_SIZE,
            quality_step=QUALITY_STEP,
            cancel_check_func=lambda: cancel_requested,
            progress_callback=lambda msg: root.after(0, lambda: update_progress_ui(msg))
        )

        # Update UI di main thread
        root.after(0, lambda: handle_render_result(status, out_path, size_kb))
    finally:
        root.after(0, finish_ui_state)

def handle_render_result(status: int, out_path: str, size_kb: float) -> None:
    """
    Menangani hasil dari proses render untuk ditampilkan ke user.
    """
    if status == 0:
        messagebox.showinfo("Selesai", f"Stiker WA siap!\nUkuran: {size_kb:.2f} KB\nDisimpan di: {out_path}")
    elif status == -1:
        print("[INFO] Render dibatalkan oleh pengguna.")
    else:
        messagebox.showwarning("Peringatan", f"Proses selesai dengan kendala atau kualitas minimal sudah tercapai.\nUkuran akhir: {size_kb:.2f} KB")

def finish_ui_state() -> None:
    """
    Mengembalikan state UI setelah proses selesai atau dibatalkan.
    """
    start_btn.config(state="normal")
    cancel_btn.config(state="disabled")
    crf_entry.config(state="normal")
    
    log_text.config(state="normal")
    log_text.insert(tk.END, "--- Selesai ---\n")
    log_text.config(state="disabled")

def cancel_render() -> None:
    """
    Meminta pembatalan proses render yang sedang berjalan.
    """
    global cancel_requested
    if messagebox.askyesno("Batal", "Batalkan proses rendering?"):
        cancel_requested = True

# ---------------------------
# Inisialisasi GUI
# ---------------------------
if __name__ == "__main__":
    root = TkinterDnD.Tk()
    root.title("WhatsApp Sticker WebP Generator (FFmpeg Pro)")
    root.geometry("760x650")

    # Drop area
    drop_frame = ttk.Frame(root)
    drop_frame.pack(fill="x", padx=20, pady=10)
    drop_label = ttk.Label(drop_frame, text="Drag & Drop Video Di Sini", relief="solid", padding=14, anchor="center")
    drop_label.pack(fill="x")
    drop_label.drop_target_register(DND_FILES)
    drop_label.dnd_bind("<<Drop>>", lambda ev: handle_video_drop(ev.data))

    # Preview area
    preview_frame = ttk.Frame(root)
    preview_frame.pack(padx=20, pady=6)
    preview_label = ttk.Label(preview_frame)
    preview_label.pack()
    frame_index_label = ttk.Label(preview_frame, text="0 / 0")
    frame_index_label.pack()

    # Timeline Selector
    canvas_frame = ttk.Frame(root)
    canvas_frame.pack(padx=20, pady=10)
    canvas = tk.Canvas(canvas_frame, width=CANVAS_W, height=CANVAS_H, bg="#f5f5f5")
    canvas.pack()
    canvas.bind("<Button-1>", on_canvas_press)
    canvas.bind("<ButtonRelease-1>", on_canvas_release)
    canvas.bind("<B1-Motion>", on_canvas_move)

    # Preview Slider
    slider_frame = ttk.Frame(root)
    slider_frame.pack(fill="x", padx=20)
    frame_slider = ttk.Scale(slider_frame, from_=0, to=1, orient="horizontal", command=lambda v: show_preview_frame(int(float(v))))
    frame_slider.pack(fill="x")

    # Controls
    controls_frame = ttk.Frame(root)
    controls_frame.pack(pady=15)

    ttk.Label(controls_frame, text="Kualitas Awal (1-100): ").grid(row=0, column=0, padx=6)
    crf_entry = ttk.Entry(controls_frame, width=8)
    crf_entry.grid(row=0, column=1, padx=6)
    crf_entry.insert(0, "75")

    start_btn = ttk.Button(controls_frame, text="Render Stiker WA", command=start_render_workflow)
    start_btn.grid(row=0, column=2, padx=6)
    cancel_btn = ttk.Button(controls_frame, text="Batalkan", command=cancel_render, state="disabled")
    cancel_btn.grid(row=0, column=3, padx=6)

    # Progress area (Log Console)
    progress_frame = ttk.Frame(root)
    progress_frame.pack(fill="both", expand=True, padx=40, pady=5)
    
    ttk.Label(progress_frame, text="Log Progres:", font=("Segoe UI", 9, "bold")).pack(anchor="w")
    
    log_container = ttk.Frame(progress_frame)
    log_container.pack(fill="both", expand=True)
    
    log_scroll = ttk.Scrollbar(log_container)
    log_scroll.pack(side="right", fill="y")
    
    log_text = tk.Text(log_container, height=6, font=("Consolas", 9), state="disabled", yscrollcommand=log_scroll.set)
    log_text.pack(side="left", fill="both", expand=True)
    log_scroll.config(command=log_text.yview)

    ttk.Button(root, text="Buka Folder Output", command=lambda: os.startfile(os.path.abspath("output"))).pack(pady=8)

    update_canvas()
    root.mainloop()