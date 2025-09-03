import streamlit as st
import os, re, hashlib
from datetime import datetime
import pandas as pd
from io import BytesIO

from utils.qr_utils import extract_qr_from_image_path, extract_qr_from_pdf_path
from utils.pdf_utils import save_uploaded_file, extract_text_from_file, render_first_page_as_image
from utils.compare import compute_sha256, text_similarity_score, aggregate_score
from utils.fetch_official import fetch_official_pdf


# ---------------- STREAMLIT CONFIG ----------------
st.set_page_config(page_title="NPTEL Cert Verifier", layout="wide")
st.title("NPTEL Certificate Verifier (Auto Verify)")


# ---------------- GLOBALS ----------------
official_path = None
official_file = None
final_score = None
o_text, u_text, o_fields = "", "", {}


# ---------------- FIELD EXTRACTOR (Improved for NPTEL) ----------------
def extract_nptel_fields(text: str):
    import re
    fields = {}
    lines = [l.strip() for l in text.splitlines() if l.strip()]

    for i, line in enumerate(lines):
        # Roll No
        if line.startswith("Roll No"):
            if i+1 < len(lines):
                fields["roll_no"] = lines[i+1]

        # Course
        if "week course" in line.lower():
            if i+1 < len(lines):
                fields["course"] = lines[i+1]

        # Name (all caps -> candidate name)
        if re.match(r"^[A-Z\s]{3,}$", line):
            fields["name"] = line.title()

        # Certificate ID
        if line.startswith("NPTEL"):
            fields["certificate_id"] = line

        # Date
        if re.search(r"\b\d{4}\b", line) and any(m in line for m in 
                    ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]):
            fields["date"] = line

        # Institute Name
        if any(word in line for word in ["IIT", "NIT", "Institute", "College", "University"]):
            fields["institute"] = line

        # Score (percentage like 66 or 66%)
        if re.fullmatch(r"\d{2,3}", line):   # pure number line
            fields["score"] = f"{line.strip()}%"
        match = re.search(r"(\d{1,3}\s*%)", line)
        if match:
            fields["score"] = match.group(1)

    # fallback: agar institute missing hai
    if "institute" not in fields:
        fields["institute"] = "IIT Roorkee"   # ⚠️ tu apne hisab se set kar sakta hai

    return fields





# ---------------- FILE UPLOAD ----------------
col1 = st.container()
with col1:
    user_file = st.file_uploader("📤 Upload USER certificate (PDF / JPG / PNG)", 
                                 type=["pdf", "png", "jpg", "jpeg"], key="user")

    if user_file is not None:
        user_path = save_uploaded_file(user_file, prefix=r"D:\Profile\Pictures\NPTEL")
        st.success(f"User file saved: `{user_path}`")

        # preview
        if user_path.lower().endswith(".pdf"):
            st.write("Preview (first page):")
            img = render_first_page_as_image(user_path)
            st.image(img, use_container_width=True)
        else:
            st.image(user_path, use_container_width=True)

        # QR extraction
        try:
            if user_path.lower().endswith('.pdf'):
                qr = extract_qr_from_pdf_path(user_path)
            else:
                qr = extract_qr_from_image_path(user_path)
        except Exception as e:
            qr = None
            st.warning(f"QR extraction error: {e}")

        if qr:
            st.success("✅ QR detected!")
            st.write("QR content (usually URL):")
            st.code(qr)

            try:
                official_path = fetch_official_pdf(qr)
                st.success(f"Official PDF downloaded: {official_path}")
            except Exception as e:
                official_path = None
                st.warning(f"Automatic fetch failed: {e}")
        else:
            st.info("⚠️ Koi QR nahi mila in the uploaded file. Clear image try karo ya high-res scan use karo.")


# ---------------- AUTO VERIFY ----------------
if user_file:
    if not official_path and not official_file:
        st.error("Official certificate not available. Please check QR link or upload manually.")
        st.stop()
    else:
        if official_file:
            official_path = save_uploaded_file(official_file, prefix=r"D:\Profile\Pictures\NPTEL")
            st.success(f"Saved manual official file: `{official_path}`")
        else:
            st.success(f"Using auto-downloaded official file: `{official_path}`")

        # HASH COMPARE
        try:
            if user_path.lower().endswith('.pdf') and official_path.lower().endswith('.pdf'):
                h1 = compute_sha256(user_path)
                h2 = compute_sha256(official_path)
                st.write("SHA-256 (user):", h1)
                st.write("SHA-256 (official):", h2)

                if h1 == h2:
                    st.balloons()
                    st.success("Verified — exact PDF match (100%).")
                    final_score = 1.0
                    o_text = extract_text_from_file(official_path)
                    u_text = extract_text_from_file(user_path)
                    o_fields = extract_nptel_fields(o_text)
        except Exception as e:
            st.warning(f"Hash compare failed: {e}")

        # TEXT COMPARE
        if final_score is None:
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

            score_text = text_similarity_score(u_text, o_text)
            st.metric("Text similarity (0-100)", f"{score_text:.1f}")

            u_fields = extract_nptel_fields(u_text)
            o_fields = extract_nptel_fields(o_text)
            st.write("Extracted fields:")
            st.json({"user": u_fields, "official": o_fields})

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


# ---------------- REPORT GENERATION ----------------
if final_score is not None and final_score >= 0.6:
    record = {
    "Uploaded_File": os.path.basename(user_path),
    "Official_File": os.path.basename(official_path),
    "Name": o_fields.get("name", ""),
    "Course": o_fields.get("course", ""),
    "Date": o_fields.get("date", ""),
    # "Roll_No": o_fields.get("roll_no", ""),
    "Certificate_ID": o_fields.get("certificate_id", ""),
    "Institute": o_fields.get("institute", ""),
    "Score": o_fields.get("score", ""),
    "Verification_Score": f"{final_score*100:.1f}%",
    "Uploaded_At": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
}


    df = pd.DataFrame([record])

    st.subheader("📊 Official Certificate Extracted Data")
    st.dataframe(df, use_container_width=True)

    # Save to Excel
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="VerificationData")
    excel_data = output.getvalue()

    st.download_button(
        label="📥 Download Verification Report (Excel)",
        data=excel_data,
        file_name=f"verification_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

elif final_score is not None:
    st.info("❌ Fake certificate detected. No report generated.")
