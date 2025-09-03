# CERTISCAN
NPTEL Certificate verifier and data extractor



NPTEL Verifier Demo (Streamlit + EasyOCR)
-----------------------------------------

Files created in this folder:
- app.py                 : Main Streamlit demo app
- utils/qr_utils.py      : QR extraction helpers (pyzbar + PyMuPDF)
- utils/pdf_utils.py     : PDF render + EasyOCR helpers
- utils/compare.py       : Hash & text/field comparison + scoring
- requirements.txt       : Suggested dependencies

How to run (locally):
1) Create a virtualenv and activate it (recommended)
   python -m venv venv
   source venv/bin/activate   # mac/linux
   venv\\Scripts\\activate    # windows

2) Install dependencies
   pip install -r requirements.txt

   NOTE: easyocr requires torch; installation may pull in torch which can be large.
   If you have trouble, consider installing CPU-only torch first: pip install torch --index-url https://download.pytorch.org/whl/cpu

3) Run Streamlit
   streamlit run app.py

Demo notes:
- For demo we expect user to upload the official PDF (downloaded from the QR landing page).
- Next steps: automate fetching official PDF using Playwright, add visual checks (pHash / SSIM), improve field extraction heuristics.

