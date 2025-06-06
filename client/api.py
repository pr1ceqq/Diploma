import requests
import cv2
from PIL import Image, ImageTk
from image_utils import display_image as display_image_util
import base64
import tempfile
import os
import threading
import time
from tkinter import messagebox
import tkinter as tk

SERVER_URL = "http://localhost:5000"
MAX_WIDTH = 800
MAX_HEIGHT = 400
PAUSE_SECONDS = 15

def encode_image_to_base64(image_path):
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode('utf-8')

def resize_image_to_fit(image, max_width=MAX_WIDTH, max_height=MAX_HEIGHT):
    h, w = image.shape[:2]
    scale = min(max_width / w, max_height / h)
    if scale < 1:
        image = cv2.resize(image, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    return image

def send_frame_to_server(frame, gui):
    gui.display_image(frame)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
        tmp_path = tmp.name
        cv2.imwrite(tmp_path, frame)
    encoded_image = encode_image_to_base64(tmp_path)
    os.unlink(tmp_path)
    response = requests.post(f"{SERVER_URL}/recognize", json={'image': encoded_image})
    if response.status_code == 200:
        plates = response.json().get("plates", [])
        matched = response.json().get("matched", plates)
        status = response.json().get("status", "")
        barrier_raised = response.json().get("barrier_raised", False)
        
        if matched:
            is_allowed = "дозволений" in status
            color = "green" if is_allowed else "red"
            gui.result_label.config(text=f"{', '.join(matched)} ({status})", fg=color)
            if is_allowed:
                gui.pause_after_allowed = True
                # Update barrier status in GUI
                gui.update_barrier_status()
        else:
            gui.result_label.config(text="❌ Номер не знайдено", fg="red")
    else:
        gui.result_label.config(text="[ERROR] Сервер не відповідає", fg="red")

def capture_and_send_once(gui):
    cap = cv2.VideoCapture(1)
    if not cap.isOpened():
        gui.result_label.config(text="[ERROR] Не вдалося відкрити камеру", fg="red")
        return
    ret, frame = cap.read()
    cap.release()
    if not ret:
        gui.result_label.config(text="[ERROR] Не вдалося зчитати кадр", fg="red")
        return
    send_frame_to_server(frame, gui)

def auto_capture_loop(gui):
    while gui.auto_mode:
        capture_and_send_once(gui)
        if getattr(gui, 'pause_after_allowed', False):
            for i in range(PAUSE_SECONDS, 0, -1):
                gui.result_label.config(text=f"Пауза: {i} с", fg="orange")
                time.sleep(1)
            # Lower the barrier after pause ends
            set_barrier_status("lowered")
            gui.update_barrier_status()
            gui.pause_after_allowed = False
            gui.result_label.config(text="Шлагбаум опущено", fg="blue")
            time.sleep(1)  # Small delay before next scan
        time.sleep(1)

def toggle_mode(gui):
    gui.auto_mode = not getattr(gui, 'auto_mode', False)
    if gui.auto_mode:
        gui.button_capture.config(state=tk.DISABLED)
        gui.button_mode.config(text="Режим: Авто (натисни для ручного)")
        gui.capture_thread = threading.Thread(target=auto_capture_loop, args=(gui,), daemon=True)
        gui.capture_thread.start()
    else:
        gui.button_capture.config(state=tk.NORMAL)
        gui.button_mode.config(text="Режим: Ручний (натисни для авто)")

def open_barrier(gui):
    messagebox.showinfo("Шлагбаум", "🚗 Шлагбаум відкрито вручну!")

def update_plate_list(gui):
    res = requests.get(f"{SERVER_URL}/list_plates")
    if res.status_code == 200:
        plates = res.json().get("plates", [])
        gui.plate_list.delete(0, tk.END)
        for plate in sorted(plates):
            gui.plate_list.insert(tk.END, plate)
    else:
        messagebox.showerror("Помилка", "Не вдалося отримати список номерів")

def add_plate(gui):
    plate = gui.plate_entry.get().strip().upper()
    if not plate:
        return
    res = requests.post(f"{SERVER_URL}/add_plate", json={"plate": plate})
    if res.status_code == 200:
        messagebox.showinfo("Успіх", f"Додано: {plate}")
        gui.plate_entry.delete(0, tk.END)
        update_plate_list(gui)
    else:
        messagebox.showerror("Помилка", res.json().get("error", "Невідома помилка"))

def delete_plate(gui):
    selected = gui.plate_list.curselection()
    if not selected:
        return
    plate = gui.plate_list.get(selected[0])
    res = requests.post(f"{SERVER_URL}/delete_plate", json={"plate": plate})
    if res.status_code == 200:
        messagebox.showinfo("Успіх", f"Видалено: {plate}")
        update_plate_list(gui)
    else:
        messagebox.showerror("Помилка", res.json().get("error", "Невідома помилка"))

def load_access_log(gui):
    gui.log_output.delete(1.0, tk.END)
    
    # Load both logs
    access_log = []
    barrier_log = []
    
    # Load access log
    res = requests.get(f"{SERVER_URL}/log")
    if res.status_code == 200:
        log_data = res.json().get("log", [])
        for plate, status, timestamp in log_data:
            access_log.append((timestamp, plate, status))
    else:
        gui.log_output.insert(tk.END, "[ERROR] Не вдалося отримати лог доступу\n")
    
    # Load barrier log
    res = requests.get(f"{SERVER_URL}/barrier_log")
    if res.status_code == 200:
        barrier_data = res.json().get("log", [])
        for status, timestamp in barrier_data:
            status_text = "🔓 Шлагбаум піднято" if status == "raised" else "🔒 Шлагбаум опущено"
            barrier_log.append((timestamp, "-"*10, status_text))
    else:
        gui.log_output.insert(tk.END, "[ERROR] Не вдалося отримати лог шлагбауму\n")
    
    # Combine and sort all logs by timestamp
    all_logs = access_log + barrier_log
    all_logs.sort(key=lambda x: x[0], reverse=True)  # Sort by timestamp in descending order
    
    # Display sorted logs
    for timestamp, plate, status in all_logs:
        line = f"{timestamp} | {plate:<10} | {status}\n"
        gui.log_output.insert(tk.END, line)

def get_barrier_status():
    try:
        res = requests.get(f"{SERVER_URL}/barrier_status")
        if res.status_code == 200:
            return res.json().get("status", "lowered")
    except Exception:
        pass
    return "lowered"

def set_barrier_status(state):
    try:
        res = requests.post(f"{SERVER_URL}/set_barrier", json={"state": state})
        if res.status_code == 200:
            return res.json().get("status", state)
    except Exception:
        pass
    return state

def get_camera_frame():
    cap = cv2.VideoCapture(1)
    if not cap.isOpened():
        return None
    ret, frame = cap.read()
    cap.release()
    if not ret:
        return None
    return frame 