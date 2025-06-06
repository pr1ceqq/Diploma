import re

def is_probable_plate(text):
    text = text.replace(" ", "").upper()
    return len(text) >= 5 and bool(re.search(r'[A-Z]', text) and re.search(r'\d', text))

def clean_ocr_text(text):
    return text.replace("/", "I").replace("|", "I").replace("\\", "I").replace("]", "I").replace("[", "I") 