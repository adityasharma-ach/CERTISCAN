import hashlib, re
from rapidfuzz import fuzz

def compute_sha256(path: str):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(8192)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()

def text_similarity_score(a: str, b: str):
    """
    Return a 0..100 similarity using rapidfuzz token_set_ratio
    """
    if not a or not b:
        return 0.0
    return fuzz.token_set_ratio(a, b)

def extract_common_fields(text: str):
    """
    Heuristic extraction of fields: certificate id (NPTEL...), candidate name (all-caps line), course name (line with week or known words), score numbers.
    Returns dict with keys: name, course, cert_id, score, term
    """
    if not text:
        return {}
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    text_upper = text.upper()
    # cert id
    cert_id = None
    m = re.search(r'(NPTEL[0-9A-Z\-]{4,})', text_upper)
    if m:
        cert_id = m.group(1)

    # try to find name: look for a line with 2-4 words and mostly alphabets (not too long), often in Title Case or UPPER
    candidate_name = None
    for ln in lines[:12]:  # first 12 lines probably contain name/course
        words = ln.split()
        if 1 < len(words) <= 4 and all(re.match(r'^[A-Z][A-Z\.\-]*$', w) or re.match(r'^[A-Z][a-z\-]+$', w) for w in words):
            # treat as name if looks like title-case or upper-case words
            candidate_name = ln
            break
    # fallback: search for lines containing typical name label
    if not candidate_name:
        for ln in lines:
            if "NAME" in ln.upper() and len(ln.split()) <= 6:
                candidate_name = ln.replace("NAME", "").strip(":- ")
                break

    # course: look for words like 'WEEK', 'COURSE', or lines in ALL CAPS that are not name and not cert id
    course = None
    for ln in lines[:20]:
        up = ln.upper()
        if any(k in up for k in ["WEEK","COURSE","SPEAKING","PROGRAM","PUBLIC","CERTIFICATE","MODULE"]) and len(ln.split())<=8:
            course = ln
            break
    if not course:
        # pick a long-ish uppercase line
        for ln in lines[:20]:
            if ln.isupper() and 2 <= len(ln.split()) <= 6 and ln != candidate_name:
                course = ln
                break

    # score: naive search for patterns like '66' or '22.25/25' or '43.5/75' - pick first numeric token > 0
    score = None
    m2 = re.search(r'(\d{1,3}(?:\.\d+)?/\d{1,3}(?:\.\d+)?)', text)
    if m2:
        score = m2.group(1)
    else:
        m3 = re.search(r'\bTotal[:\s]*([0-9]{1,3}(?:\.\d+)?)\b', text, re.IGNORECASE)
        if m3:
            score = m3.group(1)

    # term: look for month-year like Jul-Oct 2023
    term = None
    m4 = re.search(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s*[-–]?\s*(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)?\s*\d{4}', text, re.IGNORECASE)
    if m4:
        term = m4.group(0)

    return {"name": candidate_name or "", "course": course or "", "cert_id": cert_id or "", "score": score or "", "term": term or ""}

def aggregate_score(u_fields: dict, o_fields: dict, text_similarity_percent: float):
    """
    Weighted aggregation. Fields weights chosen for demo.
    Returns (final_score [0..1], details_dict)
    """
    # weights
    w_cert = 0.35
    w_name = 0.30
    w_course = 0.20
    w_text = 0.15

    # cert id exact match -> 1 else fuzzy on token ratio
    cert_score = 1.0 if (u_fields.get("cert_id") and o_fields.get("cert_id") and u_fields["cert_id"] == o_fields["cert_id"]) else (fuzz_token(u_fields.get("cert_id",""), o_fields.get("cert_id",""))/100.0)

    name_score = fuzz_token(u_fields.get("name",""), o_fields.get("name",""))/100.0
    course_score = fuzz_token(u_fields.get("course",""), o_fields.get("course",""))/100.0

    text_score = max(0.0, min(1.0, text_similarity_percent/100.0))

    final = (w_cert*cert_score + w_name*name_score + w_course*course_score + w_text*text_score)
    details = {
        "cert_score": cert_score,
        "name_score": name_score,
        "course_score": course_score,
        "text_score": text_score,
        "weights": {"cert": w_cert, "name": w_name, "course": w_course, "text": w_text}
    }
    return final, details

def fuzz_token(a: str, b: str):
    if not a and not b:
        return 100.0
    if not a or not b:
        return 0.0
    return fuzz.token_set_ratio(a, b)
