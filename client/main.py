import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from PIL import Image, ImageTk
from image_utils import display_image as display_image_util
import api
import time
import tempfile
import os
import requests
import cv2
import threading
import base64
import numpy as np

PAUSE_SECONDS = 15  

class PlateRecognitionApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Клієнт: Розпізнавання та доступ")
        self.root.geometry("1000x700")
        self.create_widgets()
        self.bind_events()
        self.result_label.config(text="Очікуємо на подальші дії...", fg="blue")

    def create_widgets(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # TAB 1: Розпізнавання
        self.tab_recognition = tk.Frame(self.notebook)
        self.notebook.add(self.tab_recognition, text="Розпізнавання")

        self.frame_main = tk.Frame(self.tab_recognition)
        self.frame_main.pack(fill=tk.BOTH, expand=True)

        self.frame_left = tk.Frame(self.frame_main)
        self.frame_left.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)

        self.button_capture = tk.Button(self.frame_left, text="📷 Зробити фото", width=22, height=2, command=self.capture_and_send_once)
        self.button_capture.pack(pady=10)

        self.button_mode = tk.Button(self.frame_left, text="🔁 Режим: Ручний", width=22, height=2, command=self.toggle_mode)
        self.button_mode.pack(pady=10)

        self.button_barrier = tk.Button(self.frame_left, text="🛑 Відкрити шлагбаум", width=22, height=2, command=self.toggle_barrier)
        self.button_barrier.pack(pady=10)

        self.barrier_status_label = tk.Label(self.frame_left, text="", font=("Arial", 12))
        self.barrier_status_label.pack(pady=5)

        self.frame_right = tk.Frame(self.frame_main)
        self.frame_right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.label_image = tk.Label(self.frame_right)
        self.label_image.pack()

        self.result_label = tk.Label(self.frame_right, text="", font=("Arial", 16))
        self.result_label.pack(pady=10)

        # TAB 2: База номерів
        self.tab_db = tk.Frame(self.notebook)
        self.notebook.add(self.tab_db, text="База дозволених номерів")

        self.frame_db = tk.Frame(self.tab_db)
        self.frame_db.pack(pady=10)

        tk.Label(self.frame_db, text="Номер:").grid(row=0, column=0, padx=5)
        self.plate_entry = tk.Entry(self.frame_db, width=20)
        self.plate_entry.grid(row=0, column=1, padx=5)

        self.plate_list = tk.Listbox(self.tab_db, width=50, height=20)
        self.plate_list.pack(padx=10, pady=10)

        tk.Button(self.frame_db, text="Додати", command=self.add_plate).grid(row=0, column=2, padx=5)
        tk.Button(self.frame_db, text="Видалити обраний", command=self.delete_plate).grid(row=0, column=3, padx=5)

        # TAB 3: Журнал доступу
        self.tab_log = tk.Frame(self.notebook)
        self.notebook.add(self.tab_log, text="Журнал доступу")

        self.log_output = scrolledtext.ScrolledText(self.tab_log, height=25, width=100, font=("Courier", 10))
        self.log_output.pack(padx=10, pady=10)

        self.update_barrier_status()

    def bind_events(self):
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)

    def on_tab_changed(self, event):
        selected_tab = event.widget.index("current")
        tab_name = self.notebook.tab(selected_tab, "text")
        if tab_name == "База дозволених номерів":
            self.update_plate_list()
        elif tab_name == "Журнал доступу":
            self.load_access_log()

    # --- API logic wrappers ---
    def display_image(self, image):
        display_image_util(image, self.label_image)

    def send_frame_to_server(self, frame):
        api.display_image_util(frame, self.label_image)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
            tmp_path = tmp.name
            cv2.imwrite(tmp_path, frame)
        encoded_image = api.encode_image_to_base64(tmp_path)
        os.unlink(tmp_path)
        response = requests.post(f"{api.SERVER_URL}/recognize", json={'image': encoded_image})
        allowed = False
        if response.status_code == 200:
            plates = response.json().get("plates", [])
            matched = response.json().get("matched", plates)
            status = response.json().get("status", "")
            boxed_image_b64 = response.json().get("boxed_image")
            if boxed_image_b64:
                img_bytes = base64.b64decode(boxed_image_b64)
                img_array = np.frombuffer(img_bytes, np.uint8)
                img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
                display_image_util(img, self.label_image)
            if matched:
                is_allowed = "дозволений" in status
                color = "green" if is_allowed else "red"
                self.result_label.config(text=f"{', '.join(matched)} ({status})", fg=color)
                allowed = is_allowed
                if allowed:
                    self.update_barrier_status()
            else:
                self.result_label.config(text="❌ Номер не знайдено", fg="red")
        else:
            self.result_label.config(text="Проблема з визначенням номера", fg="red")
        return allowed

    def capture_and_send_once(self, auto=False):
        self.display_scanning()
        frame = api.get_camera_frame()
        if frame is not None:
            self.send_frame_to_server(frame)
        else:
            self.result_label.config(text="[ERROR] Не вдалося зчитати кадр", fg="red")

    def toggle_mode(self):
        api.toggle_mode(self)

    def toggle_barrier(self):
        current_status = api.get_barrier_status()
        new_state = "lowered" if current_status == "raised" else "raised"
        api.set_barrier_status(new_state)
        self.update_barrier_status()

    def update_plate_list(self):
        api.update_plate_list(self)

    def add_plate(self):
        api.add_plate(self)

    def delete_plate(self):
        api.delete_plate(self)

    def load_access_log(self):
        api.load_access_log(self)

    def update_barrier_status(self):
        status = api.get_barrier_status()
        if status == "raised":
            self.barrier_status_label.config(text="🔓 Шлагбаум піднятий", fg="green")
            self.button_barrier.config(text="🛑 Опустити шлагбаум")
        else:
            self.barrier_status_label.config(text="🔒 Шлагбаум опущений", fg="red")
            self.button_barrier.config(text="🛑 Відкрити шлагбаум")

    def start_pause(self, seconds=PAUSE_SECONDS):
        if getattr(self, 'pause_active', False):
            return  # Do not start another pause if already active
        self.pause_active = True
        # Set barrier to raised on server
        api.set_barrier_status('raised')
        # Wait a short moment and update GUI to reflect new barrier status
        self.root.after(200, self.update_barrier_status)
        def pause_loop():
            for i in range(seconds, 0, -1):
                if not self.pause_active:
                    break
                self.result_label.config(text=f"Пауза: {i} с", fg="orange")
                self.root.update()
                time.sleep(1)
            self.pause_active = False
            self.result_label.config(text="Пауза завершена", fg="green")
            # Restore real barrier status after pause
            self.update_barrier_status()
        threading.Thread(target=pause_loop, daemon=True).start()


    def auto_capture_loop(self):
        while getattr(self, 'auto_mode', False):
            if getattr(self, 'pause_active', False):
                time.sleep(0.2)
                continue
            self.display_scanning()
            frame = api.get_camera_frame()
            if frame is not None:
                allowed = self.send_frame_to_server(frame)
                if allowed:
                    self.start_pause()
            else:
                self.result_label.config(text="[ERROR] Не вдалося зчитати кадр", fg="red")
            time.sleep(1)

    def display_scanning(self):
        self.result_label.config(text="Скануємо кадр...", fg="blue")
        self.root.update()

if __name__ == "__main__":
    root = tk.Tk()
    app = PlateRecognitionApp(root)
    root.mainloop()