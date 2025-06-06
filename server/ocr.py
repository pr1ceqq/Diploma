import cv2
import numpy as np
from paddleocr import PaddleOCR
import gc

def run_ocr(processed_image):
    ocr_model = PaddleOCR(use_angle_cls=False, lang='en', show_log=False)
    result = ocr_model.ocr(processed_image, cls=False)
    del ocr_model
    gc.collect()
    return result

def resize_for_ocr(img, scale=3):
    return cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

def enhance_contrast(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (3, 3), 0)
    adaptive = cv2.adaptiveThreshold(
        blur, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, 15, 11
    )
    return cv2.cvtColor(adaptive, cv2.COLOR_GRAY2BGR) 