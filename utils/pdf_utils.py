import fitz  
import easyocr
import tempfile, os, io
from PIL import Image
import os
import numpy as np



_reader = None
def get_easyocr_reader(lang_list=('en',)):
    global _reader
    if _reader is None:
        _reader = easyocr.Reader(list(lang_list), gpu=False)
    return _reader



def save_uploaded_file(uploaded_file, prefix=""):
    """
    Save uploaded file into a fixed folder path if prefix is absolute path,
    otherwise fallback to temporary file.
    """
    # Agar prefix ek absolute folder path hai
    if os.path.isabs(prefix):
        folder = prefix
        os.makedirs(folder, exist_ok=True)
        file_path = os.path.join(folder, uploaded_file.name)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getvalue())
        return file_path
    else:
        # Fallback to original temp behavior
        import tempfile
        suffix = os.path.splitext(uploaded_file.name)[1] if hasattr(uploaded_file, "name") else ".bin"
        tmp = tempfile.NamedTemporaryFile(delete=False, prefix=prefix, suffix=suffix)
        tmp.write(uploaded_file.getvalue())
        tmp.flush()
        tmp.close()
        return tmp.name


def render_first_page_as_image(pdf_path: str):
    doc = fitz.open(pdf_path)
    page = doc.load_page(0)
    pix = page.get_pixmap(dpi=150)
    img_bytes = pix.tobytes("png")
    return img_bytes  # can be passed to st.image directly

def extract_text_from_pdf_path(pdf_path: str):
    """
    Try text extraction using PyMuPDF first. If result is empty or tiny, fallback to EasyOCR on rendered images.
    """
    doc = fitz.open(pdf_path)
    txt_parts = []
    for page in doc:
        t = page.get_text("text")
        if t and t.strip():
            txt_parts.append(t.strip())
    full = "\n".join(txt_parts).strip()
    if len(full) > 20:
        return full
    # fallback to OCR on each page (slower)
    reader = get_easyocr_reader()
    ocr_texts = []
    for i, page in enumerate(doc):
        pix = page.get_pixmap(dpi=200)
        img_bytes = pix.tobytes("png")
        # convert to PIL Image then to numpy for easyocr
        img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        results = reader.readtext(np.array(img))
        page_text = " ".join([r[1] for r in results])
        ocr_texts.append(page_text)
    return "\n".join(ocr_texts)

def extract_text_from_image_path(image_path: str):
    reader = get_easyocr_reader()
    import numpy as np, cv2
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError("Image not readable")
    results = reader.readtext(img)
    return " ".join([r[1] for r in results])

def extract_text_from_file(path_or_tempfile: str):
    """
    Generic helper: if PDF -> extract_text_from_pdf_path else -> extract_text_from_image_path
    """
    ext = os.path.splitext(path_or_tempfile)[1].lower()
    if ext == ".pdf":
        return extract_text_from_pdf_path(path_or_tempfile)
    else:
        return extract_text_from_image_path(path_or_tempfile)
