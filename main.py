import os
import subprocess
import threading
import time
import math
import tkinter as tk
from tkinter import ttk, messagebox
from tkinterdnd2 import TkinterDnD, DND_FILES
from PIL import Image, ImageTk
import cv2
import shutil
from datetime import datetime

# ---------------------------
# Config untuk WhatsApp
# ---------------------------
TARGET_SIZE = 500 * 1024  # Maksimal 500 KB
QUALITY_STEP = 1          # Pengurangan kualitas jika file kebesaran

CANVAS_W = 520
CANVAS_H = 36
HANDLE_R = 9
PADDING = 12

# ---------------------------
# State
# ---------------------------
current_video_path = None
video_fps = 30.0
frames = []
start_idx = 0
end_idx = 0
current_preview = 0

left_x = PADDING
right_x = CANVAS_W - PADDING

drag_left = False
drag_right = False

processing_thread = None
cancel_requested = False
process_lock = threading.Lock()

# ---------------------------
# Helpers
# ---------------------------
def fmt_ts():
    return datetime.now().strftime("%Y%m%d%H%M%S")

def safe_mkdir(p):
    os.makedirs(p, exist_ok=True)

def check_ffmpeg():
    if shutil.which("ffmpeg") is None:
        messagebox.showerror(
            "Error: FFmpeg Tidak Ditemukan!",
            "Sistem tidak dapat menemukan 'ffmpeg'.\nPastikan sudah masuk PATH Windows."
        )
        return False
    return True

def run_proc_and_wait(args):
    global cancel_requested
    try:
        p = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        while True:
            if cancel_requested:
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

# ---------------------------
# Frame extraction / preview
# ---------------------------
def extract_frames(video_path):
    global frames, start_idx, end_idx, left_x, right_x, current_preview, current_video_path, video_fps

    current_video_path = video_path
    frames = []
    cap = cv2.VideoCapture(video_path)
    
    video_fps = cap.get(cv2.CAP_PROP_FPS)
    if video_fps <= 0 or math.isnan(video_fps):
        video_fps = 30.0

    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if total <= 0:
        messagebox.showerror("Error", "Cannot read video frames.")
        return

    print(f"[INFO] Video loaded: {video_path}")
    while True:
        ok, frm = cap.read()
        if not ok:
            break
        frames.append(frm)
    cap.release()

    start_idx = 0
    end_idx = len(frames) - 1
    current_preview = 0

    left_x = PADDING
    right_x = CANVAS_W - PADDING

    frame_slider.configure(to=max(0, len(frames)-1))
    frame_slider.set(0)

    update_canvas()
    show_preview_frame(0)
    canvas.itemconfigure(tick_text_left, text=f"start: {start_idx+1}")
    canvas.itemconfigure(tick_text_right, text=f"end: {end_idx+1}")

def show_preview_frame(idx):
    global current_preview
    if not frames:
        return
    idx = max(0, min(len(frames)-1, int(idx)))
    current_preview = idx
    frm = frames[idx]
    rgb = cv2.cvtColor(frm, cv2.COLOR_BGR2RGB)
    
    side = 320
    img = Image.fromarray(rgb)
    w, h = img.size
    side_crop = min(w, h)
    left = (w - side_crop)//2
    top = (h - side_crop)//2
    img = img.crop((left, top, left + side_crop, top + side_crop))
    img = img.resize((side, side), Image.Resampling.LANCZOS)
    imgtk = ImageTk.PhotoImage(img)
    preview_label.configure(image=imgtk)
    preview_label.image = imgtk
    frame_index_label.config(text=f"{idx+1} / {len(frames)}")

# ---------------------------
# Canvas range selector
# ---------------------------
def canvas_pos_to_index(x):
    if not frames: return 0
    x = max(PADDING, min(CANVAS_W - PADDING, x))
    ratio = (x - PADDING) / (CANVAS_W - 2*PADDING)
    return max(0, min(len(frames)-1, int(round(ratio * (len(frames)-1)))))

def index_to_canvas_x(idx):
    if not frames: return PADDING
    ratio = idx / max(1, (len(frames)-1))
    return PADDING + ratio * (CANVAS_W - 2*PADDING)

def update_canvas():
    canvas.delete("all")
    canvas.create_rectangle(PADDING, CANVAS_H//2 - 6, CANVAS_W - PADDING, CANVAS_H//2 + 6, fill="#ddd", outline="")
    canvas.create_rectangle(left_x, CANVAS_H//2 - 6, right_x, CANVAS_H//2 + 6, fill="#25D366", outline="") # Warna ijo WA
    canvas.create_oval(left_x - HANDLE_R, CANVAS_H//2 - HANDLE_R, left_x + HANDLE_R, CANVAS_H//2 + HANDLE_R, fill="#fff", outline="#333", width=1)
    canvas.create_oval(right_x - HANDLE_R, CANVAS_H//2 - HANDLE_R, right_x + HANDLE_R, CANVAS_H//2 + HANDLE_R, fill="#fff", outline="#333", width=1)
    
    if len(frames) <= 120 and len(frames) > 0:
        step = max(1, len(frames)//40)
        for i in range(0, len(frames), step):
            x = index_to_canvas_x(i)
            canvas.create_line(x, CANVAS_H//2 - 12, x, CANVAS_H//2 + 12, fill="#bbb")
            
    s_idx = canvas_pos_to_index(left_x) if frames else 0
    e_idx = canvas_pos_to_index(right_x) if frames else 0
    canvas.create_text(PADDING+40, CANVAS_H - 6, anchor="w", text=f"start: {s_idx+1}", fill="#333")
    canvas.create_text(CANVAS_W - PADDING-40, CANVAS_H - 6, anchor="e", text=f"end: {e_idx+1}", fill="#333")

def on_canvas_press(event):
    global drag_left, drag_right, left_x, right_x
    x = event.x
    if abs(x - left_x) <= HANDLE_R + 6: drag_left = True
    elif abs(x - right_x) <= HANDLE_R + 6: drag_right = True
    else:
        if x < CANVAS_W // 2:
            move_left_to(x); show_preview_frame(canvas_pos_to_index(x))
        else:
            move_right_to(x); show_preview_frame(canvas_pos_to_index(x))
    update_canvas()

def on_canvas_release(event):
    global drag_left, drag_right, start_idx, end_idx
    drag_left = drag_right = False
    start_idx = canvas_pos_to_index(left_x)
    end_idx = canvas_pos_to_index(right_x)
    frame_index_label.config(text=f"{current_preview+1} / {len(frames)}")

def on_canvas_move(event):
    global left_x, right_x
    x = max(PADDING, min(CANVAS_W - PADDING, event.x))
    min_gap = (HANDLE_R*2 + 6)
    if drag_left:
        left_x = min(x, right_x - min_gap)
        show_preview_frame(canvas_pos_to_index(left_x))
    elif drag_right:
        right_x = max(x, left_x + min_gap)
        show_preview_frame(canvas_pos_to_index(right_x))
    update_canvas()

def move_left_to(x): global left_x; left_x = max(PADDING, min(right_x - (HANDLE_R*2 + 6), x)); update_canvas()
def move_right_to(x): global right_x; right_x = min(CANVAS_W - PADDING, max(left_x + (HANDLE_R*2 + 6), x)); update_canvas()

# ---------------------------
# FFmpeg Auto-Compress Pipeline
# ---------------------------
def build_wa_sticker_thread(crf_entry):
    global cancel_requested
    with process_lock: cancel_requested = False

    if not current_video_path or not frames:
        messagebox.showerror("Error", "No video loaded.")
        return

    if not check_ffmpeg(): return

    s_idx = canvas_pos_to_index(left_x)
    e_idx = canvas_pos_to_index(right_x)
    
    s_time = s_idx / video_fps
    e_time = e_idx / video_fps

    try:
        current_quality = int(crf_entry.get())
    except Exception:
        current_quality = 75

    safe_mkdir("output")
    out_name = f"wa_sticker_{fmt_ts()}.webp"
    out_path = os.path.join("output", out_name)

    print(f"[INFO] Mulai render untuk WA (Target < 500KB)")

    # Looping otomatis jika ukuran file di atas 500KB
    while True:
        if cancel_requested:
            print("[CANCEL] Proses dibatalkan pengguna.")
            return

        print(f"[PROCESS] Merender dengan Quality: {current_quality}...")
        
        # FFmpeg khusus WhatsApp: 512x512, 20 FPS
        cmd = [
            "ffmpeg", "-y",
            "-i", current_video_path,
            "-ss", f"{s_time:.3f}",
            "-to", f"{e_time:.3f}",
            "-vf", "crop='min(iw,ih)':'min(iw,ih)',scale=512:512,fps=30",
            "-c:v", "libwebp",
            "-loop", "0",
            "-lossless", "0",
            "-qscale", str(current_quality),
            "-an", 
            out_path
        ]

        rc = run_proc_and_wait(cmd)
        
        if rc == -1: return # Dibatalkan
        if rc != 0:
            messagebox.showerror("Error", "FFmpeg gagal merender video.")
            return

        # Cek ukuran file
        size_b = os.path.getsize(out_path)
        print(f"[RESULT] Q: {current_quality} | Size: {size_b/1024:.2f} KB")

        if size_b <= TARGET_SIZE:
            messagebox.showinfo("Selesai", f"Stiker WA siap!\nUkuran: {size_b/1024:.2f} KB\nDisimpan di: {out_path}")
            return
            
        # Jika masih lebih dari 500KB, kurangi kualitas dan ulang
        current_quality -= QUALITY_STEP
        if current_quality <= 0:
            print("[WARN] Mentok di kualitas minimum, file mungkin masih terlalu besar.")
            messagebox.showwarning("Peringatan", f"Kualitas sudah minimal tapi file masih {size_b/1024:.2f} KB. Coba potong durasi video di slider.")
            return

# ---------------------------
# UI actions
# ---------------------------
def start_action():
    global processing_thread, cancel_requested
    if not current_video_path: return messagebox.showerror("Error", "Masukkan video dulu!")
    
    start_btn.config(state="disabled")
    cancel_btn.config(state="normal")
    crf_entry.config(state="disabled")

    cancel_requested = False
    processing_thread = threading.Thread(target=lambda: background_wrapper())
    processing_thread.start()

def background_wrapper():
    global processing_thread
    try: build_wa_sticker_thread(crf_entry)
    finally: root.after(0, finish_processing_ui)

def finish_processing_ui():
    start_btn.config(state="normal")
    cancel_btn.config(state="disabled")
    crf_entry.config(state="normal")

def cancel_action():
    global cancel_requested
    if messagebox.askyesno("Cancel", "Batalkan proses?"):
        cancel_requested = True

# ---------------------------
# GUI init
# ---------------------------
root = TkinterDnD.Tk()
root.title("WhatsApp Sticker WebP Generator (FFmpeg Pro)")
root.geometry("760x650")
root.after(500, check_ffmpeg)

drop_frame = ttk.Frame(root)
drop_frame.pack(fill="x", padx=20, pady=10)
drop_label = ttk.Label(drop_frame, text="Drag & Drop Video Di Sini", relief="solid", padding=14, anchor="center")
drop_label.pack(fill="x")
drop_label.drop_target_register(DND_FILES)
drop_label.dnd_bind("<<Drop>>", lambda ev: extract_frames(ev.data.strip("{}")))

preview_frame = ttk.Frame(root)
preview_frame.pack(padx=20, pady=6)
preview_label = ttk.Label(preview_frame)
preview_label.pack()
frame_index_label = ttk.Label(preview_frame, text="0 / 0")
frame_index_label.pack()

canvas_frame = ttk.Frame(root)
canvas_frame.pack(padx=20, pady=10)
canvas = tk.Canvas(canvas_frame, width=CANVAS_W, height=CANVAS_H, bg="#f5f5f5")
canvas.pack()
canvas.bind("<Button-1>", on_canvas_press)
canvas.bind("<ButtonRelease-1>", on_canvas_release)
canvas.bind("<B1-Motion>", on_canvas_move)

slider_frame = ttk.Frame(root)
slider_frame.pack(fill="x", padx=20)
frame_slider = ttk.Scale(slider_frame, from_=0, to=1, orient="horizontal", command=lambda v: show_preview_frame(int(float(v))))
frame_slider.pack(fill="x")

controls_frame = ttk.Frame(root)
controls_frame.pack(pady=15)

ttk.Label(controls_frame, text="Mulai Kualitas (1-100): ").grid(row=0, column=0, padx=6)
crf_entry = ttk.Entry(controls_frame, width=8)
crf_entry.grid(row=0, column=1, padx=6)
crf_entry.insert(0, "75")

start_btn = ttk.Button(controls_frame, text="Render Stiker WA", command=start_action)
start_btn.grid(row=0, column=2, padx=6)
cancel_btn = ttk.Button(controls_frame, text="Batalkan", command=cancel_action, state="disabled")
cancel_btn.grid(row=0, column=3, padx=6)

ttk.Button(root, text="Buka Folder Output", command=lambda: os.startfile(os.path.abspath("output"))).pack(pady=8)

tick_text_left = canvas.create_text(10, CANVAS_H - 6, anchor="w", text="start: 0")
tick_text_right = canvas.create_text(CANVAS_W - 10, CANVAS_H - 6, anchor="e", text="end: 0")
update_canvas()

root.mainloop()