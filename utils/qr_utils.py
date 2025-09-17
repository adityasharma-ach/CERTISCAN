import cv2
import fitz  # pymupdf
import tempfile, os

def extract_qr_from_image_path(path: str):
    """
    Read image from path and try to decode QR using OpenCV QRCodeDetector.
    Returns decoded string or None.
    """
    img = cv2.imread(path)
    if img is None:
        raise ValueError("Image not readable by OpenCV")
    detector = cv2.QRCodeDetector()
    data, points, _ = detector.detectAndDecode(img)
    return data if data else None

def extract_qr_from_pdf_path(pdf_path: str):
    """
    Render first page of PDF and try to decode QR using OpenCV QRCodeDetector.
    """
    doc = fitz.open(pdf_path)
    if doc.page_count < 1:
        return None
    page = doc.load_page(0)
    pix = page.get_pixmap(dpi=200)
    img_data = pix.tobytes("png")
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    tmp.write(img_data)
    tmp.flush()
    tmp.close()
    try:
        return extract_qr_from_image_path(tmp.name)
    finally:
        try:
            os.unlink(tmp.name)
        except Exception:
            pass
