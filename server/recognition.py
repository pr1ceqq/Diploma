import base64
import cv2
import numpy as np
from flask import jsonify
from ultralytics import YOLO
from ocr import run_ocr, resize_for_ocr, enhance_contrast
from db import log_access, is_plate_allowed
import re
import os
import requests
import tkinter as tk
import tkinter.messagebox as messagebox

# Server configuration
SERVER_URL = "http://localhost:5000"

# Get the directory where this file is located
current_dir = os.path.dirname(os.path.abspath(__file__))
# Construct path to the model file
model_path = os.path.join(current_dir, "models", "best.pt")

model = YOLO(model_path)

def is_probable_plate(text):
    text = text.replace(" ", "").upper()
    return len(text) >= 4 and bool(re.search(r'[A-Z]', text) and re.search(r'\d', text))

def clean_ocr_text(text):
    return text.replace("/", "I").replace("|", "I").replace("\\", "I").replace("]", "I").replace("[", "I")

def recognize_plate(request):
    data = request.get_json()
    if 'image' not in data:
        return jsonify({'error': 'No image provided'}), 400

    image_data = base64.b64decode(data['image'])
    nparr = np.frombuffer(image_data, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    results = model(image)
    final_texts = []
    matched_texts = []
    status = "пропуск заборонений"
    barrier_raised = False

    # Draw rectangles for all detected plates
    if results[0].boxes is not None:
        boxes = results[0].boxes.xyxy.cpu().numpy()
        for i, box in enumerate(boxes):
            x1, y1, x2, y2 = map(int, box[:4])
            # Draw rectangle (green by default)
            cv2.rectangle(image, (x1, y1), (x2, y2), (0, 255, 0), 2)
            plate_img = image[y1:y2, x1:x2]

            if plate_img is None or plate_img.shape[0] < 40 or plate_img.shape[1] < 100:
                continue

            resized = resize_for_ocr(plate_img)
            processed = enhance_contrast(resized)
            ocr_result = run_ocr(processed)

            if ocr_result and len(ocr_result) > 0:
                for line in ocr_result[0]:
                    text = line[1][0]
                    # Прибираємо ':' з номера
                    text = text.replace(':', '')
                    text = text.replace('=', '')
                    text_cleaned = clean_ocr_text(text.replace(" ", "").upper())

                    if is_probable_plate(text_cleaned):
                        allowed, corrected_plate = is_plate_allowed(text_cleaned)
                        final_texts.append(text_cleaned)
                        matched_texts.append(corrected_plate)
                        if allowed:
                            status = "пропуск дозволений"
                            # Automatically raise the barrier for allowed plates
                            requests.post(f"http://localhost:5000/set_barrier", json={"state": "raised"})
                            barrier_raised = True
                        log_access(corrected_plate, status)

    # Encode image with rectangles to base64
    _, img_encoded = cv2.imencode('.jpg', image)
    img_base64 = base64.b64encode(img_encoded).decode('utf-8')

    return jsonify({
        'plates': final_texts, 
        'matched': matched_texts, 
        'status': status,
        'barrier_raised': barrier_raised,
        'boxed_image': img_base64
    })

def update_plate_list(self):
    res = requests.get(f"{SERVER_URL}/list_plates")
    if res.status_code == 200:
        plates = res.json().get("plates", [])
        self.plate_list.delete(0, tk.END)
        for plate in sorted(plates):
            self.plate_list.insert(tk.END, plate)
    else:
        messagebox.showerror("Помилка", "Не вдалося отримати список номерів")

class ClientApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Клієнт: Розпізнавання та доступ")
        self.root.geometry("1000x700")
        self.create_widgets()
        self.bind_events()
        self.update_plate_list() 