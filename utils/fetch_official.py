import os, tempfile, time, requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

def fetch_official_pdf(qr_url: str) -> str:
    """
    Open the QR URL in headless Chrome, try to find a certificate PDF link/button,
    download it, and return its path.
    """
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.get(qr_url)
    time.sleep(3)

    pdf_url = None
    try:
        # 1) Try by link text heuristics
        keywords = ["Course Certificate", "Download Certificate", "View Certificate", "Certificate"]
        for key in keywords:
            try:
                elem = driver.find_element(By.PARTIAL_LINK_TEXT, key)
                href = elem.get_attribute("href")
                if href and ".pdf" in href.lower():
                    pdf_url = href
                    break
                else:
                    elem.click()
                    time.sleep(3)
                    if ".pdf" in driver.current_url.lower():
                        pdf_url = driver.current_url
                        break
            except:
                continue

        # 2) Fallback: scan all <a> links
        if not pdf_url:
            anchors = driver.find_elements(By.TAG_NAME, "a")
            for a in anchors:
                href = a.get_attribute("href") or ""
                if ".pdf" in href.lower():
                    pdf_url = href
                    break
    finally:
        driver.quit()

    if not pdf_url:
        raise RuntimeError("No PDF link found on QR landing page")


    # Download PDF
    save_dir = r"D:\Profile\Pictures\NPTEL"
    os.makedirs(save_dir, exist_ok=True)
    save_path = os.path.join(save_dir, "official.pdf")

    resp = requests.get(pdf_url, timeout=60000)
    if resp.status_code == 200:
        with open(save_path, "wb") as f:
            f.write(resp.content)
        return save_path
    else:
        raise RuntimeError(f"Failed to download PDF from {pdf_url}, status {resp.status_code}")

