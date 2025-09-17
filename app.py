import streamlit as st
import os, hashlib
from utils.qr_utils import extract_qr_from_image_path, extract_qr_from_pdf_path
from utils.pdf_utils import save_uploaded_file, extract_text_from_file, render_first_page_as_image
from utils.compare import compute_sha256, text_similarity_score, extract_common_fields, aggregate_score
from utils.fetch_official import fetch_official_pdf

st.set_page_config(page_title="NPTEL Cert Verifier (Demo)", layout="wide")
st.title("NPTEL Certificate Verifier — Demo (EasyOCR + Streamlit)")
st.write("Bhai: bas apna certificate upload kar, baaki kaam system khud karega ✅")

col1, col2 = st.columns([1, 1])

# Globals
official_path = None
official_file = None

with col1:
    user_file = st.file_uploader("1) Upload USER certificate (PDF / JPG / PNG)", 
                                 type=["pdf", "png", "jpg", "jpeg"], key="user")
    if user_file is not None:
        # save user upload to fixed folder
        user_path = save_uploaded_file(user_file, prefix=r"D:\Profile\Pictures\NPTEL")
        st.success(f"User file saved: `{user_path}`")

        # preview
        if user_path.lower().endswith(".pdf"):
            st.write("Preview (first page):")
            img = render_first_page_as_image(user_path)
            st.image(img, use_container_width=True)
        else:
            st.image(user_path, use_container_width=True)

        # Try read QR
        try:
            if user_path.lower().endswith('.pdf'):
                qr = extract_qr_from_pdf_path(user_path)
            else:
                qr = extract_qr_from_image_path(user_path)
        except Exception as e:
            qr = None
            st.warning(f"QR extraction error: {e}")

        if qr:
            st.success("QR detected!")
            st.write("QR content (usually URL):")
            st.code(qr)

            # auto-fetch official pdf
            try:
                official_path = fetch_official_pdf(qr)
                st.success(f"Official PDF downloaded: {official_path}")
            except Exception as e:
                official_path = None
                st.warning(f"Automatic fetch failed: {e}")
        else:
            st.info("Koi QR nahi mila in the uploaded file. Clear image try karo ya high-res scan use karo.")

with col2:
    st.markdown("Optional: Agar auto-download fail ho jaye to yaha official PDF manually upload kar sakte ho 👇")
    official_file = st.file_uploader("2) Upload OFFICIAL certificate (PDF)", type=["pdf"], key="official")

# ---------------- VERIFY BUTTON ----------------
if st.button("Verify" if user_file else "Upload user file first"):
    if not user_file:
        st.error("Pehle user certificate upload karo bhai.")
    elif not official_path and not official_file:
        st.error("Official certificate not available. Please check QR link or upload manually.")
        st.stop()
    else:
        # decide official path
        if official_file:
            official_path = save_uploaded_file(official_file, prefix=r"D:\Profile\Pictures\NPTEL")
            st.success(f"Saved manual official file: `{official_path}`")
        else:
            st.success(f"Using auto-downloaded official file: `{official_path}`")

        # ---------------- HASH COMPARE ----------------
        try:
            if user_path.lower().endswith('.pdf') and official_path.lower().endswith('.pdf'):
                h1 = compute_sha256(user_path)
                h2 = compute_sha256(official_path)
                st.write("SHA-256 (user):", h1)
                st.write("SHA-256 (official):", h2)
                if h1 == h2:
                    st.balloons()
                    st.success("Verified — exact PDF match (100%).")
                    st.stop()
        except Exception as e:
            st.warning(f"Hash compare failed: {e}")

        # ---------------- TEXT COMPARE ----------------
        with st.spinner("Extracting text using PyMuPDF + EasyOCR..."):
            u_text = extract_text_from_file(user_path)
            o_text = extract_text_from_file(official_path)

        st.subheader("Extracted Text (short preview)")
        c1, c2 = st.columns(2)
        with c1:
            st.write("User certificate:")
            st.text(u_text[:800] + ("..." if len(u_text) > 800 else ""))
        with c2:
            st.write("Official certificate:")
            st.text(o_text[:800] + ("..." if len(o_text) > 800 else ""))

        # similarity
        score_text = text_similarity_score(u_text, o_text)
        st.metric("Text similarity (0-100)", f"{score_text:.1f}")

        # field compare
        u_fields = extract_common_fields(u_text)
        o_fields = extract_common_fields(o_text)
        st.write("Extracted fields (heuristic):")
        st.json({"user": u_fields, "official": o_fields})

        # aggregate
        final_score, details = aggregate_score(u_fields, o_fields, score_text)
        st.write("Decision details:")
        st.json(details)

        st.metric("Aggregate confidence (0-100)", f"{final_score*100:.1f}%")
        if final_score >= 0.9:
            st.success("VERIFIED ✅ — High confidence")
            st.balloons()
        elif final_score >= 0.6:
            st.warning("SUSPICIOUS ⚠️ — Partial match; manual review recommended")
        else:
            st.error("FAKE / MISMATCH ❌ — Low confidence")

        # evidence download
        st.download_button("Download user file", data=open(user_path, "rb").read(), file_name=os.path.basename(user_path))
        st.download_button("Download official file", data=open(official_path, "rb").read(), file_name=os.path.basename(official_path))

st.markdown("---")
st.write("Next steps: add visual tampering check (pHash/SSIM), improve field extraction regexes, and DB logging.")
