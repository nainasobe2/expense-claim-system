import os
import re
import shutil
from datetime import datetime, date
from typing import Dict, Any, Optional, Tuple
from PIL import Image, ImageEnhance, ImageOps

try:
    import pytesseract
    # Configure tesseract executable path if located in homebrew or local bin
    if shutil.which("tesseract"):
        pytesseract.pytesseract.tesseract_cmd = shutil.which("tesseract")
    elif os.path.exists("/opt/homebrew/bin/tesseract"):
        pytesseract.pytesseract.tesseract_cmd = "/opt/homebrew/bin/tesseract"
    elif os.path.exists("/usr/local/bin/tesseract"):
        pytesseract.pytesseract.tesseract_cmd = "/usr/local/bin/tesseract"
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False


def preprocess_image_for_ocr(img: Image.Image) -> Image.Image:
    """
    Preprocesses receipt images to significantly enhance Tesseract character recognition:
    - Upscales small images
    - Converts to grayscale
    - Enhances contrast
    """
    # Convert to RGB first
    if img.mode not in ("L", "RGB"):
        img = img.convert("RGB")
    
    # Upscale if image is smaller than standard readable resolution
    w, h = img.size
    if w < 1200:
        factor = 1200.0 / w
        img = img.resize((int(w * factor), int(h * factor)), Image.Resampling.LANCZOS)
    
    # Convert to Grayscale
    gray = img.convert("L")
    
    # Enhance contrast
    enhancer = ImageEnhance.Contrast(gray)
    contrasted = enhancer.enhance(1.8)
    
    return contrasted


def extract_receipt_data(image_path: str) -> Dict[str, Any]:
    """
    Uses pytesseract OCR to extract amount, date, and category from a receipt image.
    Calculates confidence scores and returns fallback indicator if confidence is low.
    """
    default_result = {
        "extracted": {
            "amount": None,
            "date": None,
            "category": None,
            "merchant": None,
            "raw_text": ""
        },
        "confidence": {
            "amount": 0.0,
            "date": 0.0,
            "category": 0.0,
            "overall": 0.0,
            "level": "LOW"
        },
        "low_confidence": True,
        "message": "Manual entry required."
    }

    if not os.path.exists(image_path):
        default_result["message"] = "Receipt image file not found on server."
        return default_result

    raw_text = ""
    try:
        with Image.open(image_path) as img:
            processed = preprocess_image_for_ocr(img)
            raw_text = pytesseract.image_to_string(processed)
    except Exception as err:
        default_result["message"] = f"OCR processing notice: {str(err)}. Please enter details manually."
        return default_result

    if not raw_text.strip():
        default_result["message"] = "No readable text detected from receipt. Please enter details manually."
        return default_result

    # Field Extractions
    extracted_amount, amount_conf = _extract_amount(raw_text)
    extracted_date, date_conf = _extract_date(raw_text)
    extracted_cat, extracted_merchant, cat_conf = _extract_category(raw_text)

    # Overall Confidence Calculation
    scores = [s for s in [amount_conf, date_conf, cat_conf] if s > 0]
    overall_conf = (sum(scores) / 3.0) if scores else 0.0
    overall_conf = round(overall_conf, 2)

    if overall_conf >= 0.70:
        conf_level = "HIGH"
        low_confidence = False
        message = "Receipt details successfully extracted! Please review the auto-filled fields below."
    elif overall_conf >= 0.35:
        conf_level = "MEDIUM"
        low_confidence = False
        message = "Some receipt details were recognized with moderate confidence. Please verify before submitting."
    else:
        conf_level = "LOW"
        low_confidence = True
        message = "Low confidence extraction. Please review or manually enter the fields."

    return {
        "extracted": {
            "amount": extracted_amount,
            "date": extracted_date,
            "category": extracted_cat,
            "merchant": extracted_merchant,
            "raw_text": raw_text.strip()[:600]
        },
        "confidence": {
            "amount": round(amount_conf, 2),
            "date": round(date_conf, 2),
            "category": round(cat_conf, 2),
            "overall": overall_conf,
            "level": conf_level
        },
        "low_confidence": low_confidence,
        "message": message
    }


def _extract_amount(text: str) -> Tuple[Optional[float], float]:
    """
    Finds monetary amount. Prioritizes lines containing 'TOTAL', 'AMOUNT', 'BALANCE', or 'USD'.
    """
    lines = text.splitlines()
    total_candidates = []

    # Matches numbers with 2 decimals, optional currency prefix/spacing
    # e.g., $16.20, $ 16.20, USD 45.00, 16.20
    amount_regex = re.compile(r'(?:[\$£€]|USD)?\s*([0-9]{1,4}(?:[.,][0-9]{2}))\b', re.IGNORECASE)

    # Pass 1: Look for explicit TOTAL / BALANCE DUE / AMOUNT PAID keywords
    for line in lines:
        upper = line.upper()
        if any(kw in upper for kw in ["TOTAL", "BALANCE DUE", "AMOUNT PAID", "GRAND TOTAL", "NET AMOUNT", "CHARGE", "PAID"]):
            matches = amount_regex.findall(line)
            for m in matches:
                try:
                    val = float(m.replace(",", "."))
                    if 0.50 <= val <= 25000:
                        total_candidates.append((val, 0.90))
                except ValueError:
                    pass

    # Pass 2: Fallback to all amounts found in document
    if not total_candidates:
        all_amounts = []
        for line in lines:
            matches = amount_regex.findall(line)
            for m in matches:
                try:
                    val = float(m.replace(",", "."))
                    if 1.00 <= val <= 10000:
                        all_amounts.append(val)
                except ValueError:
                    pass
        if all_amounts:
            return max(all_amounts), 0.55

    if total_candidates:
        best_val, best_conf = max(total_candidates, key=lambda x: x[0])
        return best_val, best_conf

    return None, 0.0


def _extract_date(text: str) -> Tuple[Optional[str], float]:
    """
    Extracts date string in YYYY-MM-DD format.
    """
    today = date.today()

    # Pattern 1: YYYY-MM-DD or YYYY/MM/DD
    m1 = re.search(r'\b(20[2-3][0-9])[-/.](0[1-9]|1[0-2])[-/.](0[1-9]|[12][0-9]|3[01])\b', text)
    if m1:
        try:
            d = date(int(m1.group(1)), int(m1.group(2)), int(m1.group(3)))
            if d <= today:
                return d.isoformat(), 0.90
        except ValueError:
            pass

    # Pattern 2: MM/DD/YYYY or DD/MM/YYYY
    m2 = re.findall(r'\b(0?[1-9]|1[0-2])[-/.](0?[1-9]|[12][0-9]|3[01])[-/.](20[2-3][0-9])\b', text)
    for m in m2:
        try:
            d = date(int(m[2]), int(m[0]), int(m[1]))
            if d <= today:
                return d.isoformat(), 0.85
        except ValueError:
            pass

    # Pattern 3: Month name (e.g., Oct 08, 2026 or 08 Oct 2026)
    month_names = {
        'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
        'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
    }
    m3 = re.search(r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+([0-9]{1,2}),?\s+(20[2-3][0-9])\b', text, re.IGNORECASE)
    if m3:
        try:
            mon_num = month_names[m3.group(1).lower()[:3]]
            d = date(int(m3.group(3)), mon_num, int(m3.group(2)))
            if d <= today:
                return d.isoformat(), 0.85
        except (ValueError, KeyError):
            pass

    return None, 0.0


def _extract_category(text: str) -> Tuple[Optional[str], Optional[str], float]:
    """
    Infers category and merchant name using keyword matching.
    """
    lower = text.lower()

    meals_keywords = ["restaurant", "cafe", "bistro", "coffee", "starbucks", "dinner", "lunch", "breakfast", "burger", "pizza", "grill", "bakery", "food", "kitchen", "bar", "sushi", "chipotle", "subway"]
    travel_keywords = ["airline", "flight", "delta", "united", "hotel", "inn", "suites", "uber", "lyft", "taxi", "amtrak", "parking", "marriott", "hilton", "hyatt", "airbnb", "airport", "car rental", "hertz"]
    equipment_keywords = ["hardware", "electronics", "apple", "dell", "best buy", "staples", "office depot", "laptop", "monitor", "keyboard", "mouse", "headset", "cable", "software", "amazon"]

    meals_matches = sum(1 for kw in meals_keywords if kw in lower)
    travel_matches = sum(1 for kw in travel_keywords if kw in lower)
    equip_matches = sum(1 for kw in equipment_keywords if kw in lower)

    scores = {
        "MEALS": meals_matches,
        "TRAVEL": travel_matches,
        "EQUIPMENT": equip_matches
    }

    best_cat, max_matches = max(scores.items(), key=lambda x: x[1])

    if max_matches >= 2:
        conf = 0.85
    elif max_matches == 1:
        conf = 0.60
    else:
        best_cat = None
        conf = 0.0

    lines = [l.strip() for l in text.splitlines() if l.strip() and len(l.strip()) > 2]
    merchant = lines[0] if lines else None

    return best_cat, merchant, conf

