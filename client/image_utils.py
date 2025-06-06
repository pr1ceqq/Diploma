import cv2
import base64
import tempfile
import os
from PIL import Image, ImageTk

MAX_WIDTH = 800
MAX_HEIGHT = 400

def encode_image_to_base64(image_path):
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode('utf-8')

def resize_image_to_fit(image, max_width=MAX_WIDTH, max_height=MAX_HEIGHT):
    h, w = image.shape[:2]
    scale = min(max_width / w, max_height / h)
    if scale < 1:
        image = cv2.resize(image, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    return image

def display_image(image, label_image):
    resized_img = resize_image_to_fit(image)
    img_rgb = cv2.cvtColor(resized_img, cv2.COLOR_BGR2RGB)
    img_pil = Image.fromarray(img_rgb)
    img_tk = ImageTk.PhotoImage(img_pil)
    label_image.config(image=img_tk, width=img_pil.width, height=img_pil.height)
    label_image.image = img_tk 