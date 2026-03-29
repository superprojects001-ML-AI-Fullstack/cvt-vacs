"""
ANPR Service: Automatic Number Plate Recognition
Implements YOLOv8 + OCR pipeline as per thesis specifications
Updated: Added vehicle color detection using OpenCV HSV color space
"""
import cv2
import numpy as np
from datetime import datetime
from typing import Optional, Dict, Any, Tuple
import base64
import io
from PIL import Image
import re

from app.config import get_settings

settings = get_settings()

# Lazy loading of ML models
_yolo_model = None
_ocr_reader = None


def get_yolo_model():
    """Lazy load YOLOv8 model"""
    global _yolo_model
    if _yolo_model is None:
        try:
            from ultralytics import YOLO
            # Use YOLOv8n (nano) for faster inference
            _yolo_model = YOLO('yolov8n.pt')
            print("✅ YOLOv8 model loaded")
        except Exception as e:
            print(f"⚠️ YOLO model loading failed: {e}")
            _yolo_model = None
    return _yolo_model


def get_ocr_reader():
    """Lazy load EasyOCR reader"""
    global _ocr_reader
    if _ocr_reader is None:
        try:
            import easyocr
            # Initialize for English
            _ocr_reader = easyocr.Reader(['en'], gpu=False)
            print("✅ EasyOCR reader loaded")
        except Exception as e:
            print(f"⚠️ EasyOCR loading failed: {e}")
            _ocr_reader = None
    return _ocr_reader


class ANPRService:
    """
    ANPR Service implementing Computer Vision pipeline
    Algorithm: Image → Preprocess → YOLO Detection → OCR → Color Detection → Plate Number
    """

    # Common license plate patterns
    PLATE_PATTERNS = [
        r'[A-Z]{3}[-\s]?\d{3}[A-Z]{2}',       # ABC-123-XY  (Nigerian standard)
        r'[A-Z]{2}[-\s]?\d{2}[-\s]?[A-Z]{3}',  # AB-12-ABC format
        r'[A-Z]{3}[-\s]?\d{4}',                 # ABC-1234 format
        r'\d{2}[-\s]?[A-Z]{2}[-\s]?\d{4}',     # 12-AB-1234 format
        r'[A-Z]\d{3}[A-Z]{3}',                  # A123ABC format
    ]

    # HSV color ranges for vehicle color detection
    # Format: color_name -> list of (lower_hsv, upper_hsv) tuples
    # Multiple ranges per color handle edge cases (e.g. red wraps around 180°)
    COLOR_RANGES = {
        "red":    [
            (np.array([0,   70,  50]),  np.array([10,  255, 255])),
            (np.array([170, 70,  50]),  np.array([180, 255, 255])),  # red wraps hue
        ],
        "blue":   [(np.array([100, 50,  50]),  np.array([130, 255, 255]))],
        "green":  [(np.array([40,  50,  50]),  np.array([80,  255, 255]))],
        "yellow": [(np.array([20,  50,  50]),  np.array([35,  255, 255]))],
        "orange": [(np.array([11,  50,  50]),  np.array([19,  255, 255]))],
        "white":  [(np.array([0,   0,   200]), np.array([180, 30,  255]))],
        "black":  [(np.array([0,   0,   0]),   np.array([180, 255, 50]))],
        "silver": [(np.array([0,   0,   150]), np.array([180, 30,  200]))],
        "grey":   [(np.array([0,   0,   80]),  np.array([180, 30,  149]))],
        "brown":  [(np.array([10,  50,  20]),  np.array([20,  255, 150]))],
        "purple": [(np.array([130, 50,  50]),  np.array([160, 255, 255]))],
    }

    @staticmethod
    def decode_base64_image(base64_string: str) -> Optional[np.ndarray]:
        """Decode base64 string to OpenCV image"""
        try:
            if ',' in base64_string:
                base64_string = base64_string.split(',')[1]
            img_data = base64.b64decode(base64_string)
            img = Image.open(io.BytesIO(img_data))
            img_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
            return img_cv
        except Exception as e:
            print(f"Image decode error: {e}")
            return None

    @staticmethod
    def encode_image_to_base64(image: np.ndarray) -> str:
        """Encode OpenCV image to base64"""
        _, buffer = cv2.imencode('.jpg', image)
        img_str = base64.b64encode(buffer).decode('utf-8')
        return f"data:image/jpeg;base64,{img_str}"

    @staticmethod
    def preprocess_image(image: np.ndarray, target_size: Tuple[int, int] = (640, 640)) -> np.ndarray:
        """
        Preprocess image for ANPR
        - Resize to 640x640 (YOLOv8 input)
        - Normalize pixel values
        - Enhance contrast
        """
        h, w = image.shape[:2]
        scale = min(target_size[0] / w, target_size[1] / h)
        new_w = int(w * scale)
        new_h = int(h * scale)

        resized = cv2.resize(image, (new_w, new_h))

        padded = np.full((target_size[1], target_size[0], 3), 128, dtype=np.uint8)
        y_offset = (target_size[1] - new_h) // 2
        x_offset = (target_size[0] - new_w) // 2
        padded[y_offset:y_offset + new_h, x_offset:x_offset + new_w] = resized

        return padded

    @staticmethod
    def detect_vehicle_color(image: np.ndarray) -> Dict[str, Any]:
        """
        Detect dominant vehicle color using HSV color space analysis.

        Strategy:
          1. Convert the full image to HSV.
          2. Crop out the bottom 20% (road) and top 10% (sky) to focus on
             the vehicle body.
          3. For each colour, sum all matching pixels across its HSV ranges.
          4. Pick the colour with the highest pixel count.
          5. If the winner is too close to 'unknown' territory (very low
             pixel count), return "unknown".

        Args:
            image: BGR OpenCV image (numpy ndarray)

        Returns:
            Dict with keys:
                color        (str)   - detected colour name
                color_confidence (float) - 0.0–1.0 ratio of matched pixels
                color_hex    (str)   - representative hex code for the UI
        """
        if image is None or image.size == 0:
            return {"color": "unknown", "color_confidence": 0.0, "color_hex": "#808080"}

        # ── 1. Crop to vehicle body region ──────────────────────────────────
        h, w = image.shape[:2]
        top_cut    = int(h * 0.10)   # remove sky
        bottom_cut = int(h * 0.20)   # remove road
        body = image[top_cut: h - bottom_cut, :]

        if body.size == 0:
            body = image  # fallback to full image

        # ── 2. Convert to HSV ───────────────────────────────────────────────
        hsv = cv2.cvtColor(body, cv2.COLOR_BGR2HSV)
        total_pixels = hsv.shape[0] * hsv.shape[1]

        # ── 3. Count pixels per colour ──────────────────────────────────────
        color_scores: Dict[str, int] = {}
        for color_name, ranges in ANPRService.COLOR_RANGES.items():
            count = 0
            for (lower, upper) in ranges:
                mask = cv2.inRange(hsv, lower, upper)
                count += int(cv2.countNonZero(mask))
            color_scores[color_name] = count

        # ── 4. Pick the winner ──────────────────────────────────────────────
        best_color = max(color_scores, key=lambda c: color_scores[c])
        best_count = color_scores[best_color]
        confidence = round(best_count / total_pixels, 4) if total_pixels > 0 else 0.0

        # ── 5. Low-confidence fallback ──────────────────────────────────────
        MIN_CONFIDENCE = 0.05          # less than 5 % of pixels matched → unknown
        if confidence < MIN_CONFIDENCE:
            best_color = "unknown"

        # ── 6. Map colour to a representative hex for the UI ────────────────
        COLOR_HEX_MAP = {
            "red":    "#FF0000",
            "blue":   "#0000FF",
            "green":  "#008000",
            "yellow": "#FFFF00",
            "orange": "#FF8C00",
            "white":  "#FFFFFF",
            "black":  "#1A1A1A",
            "silver": "#C0C0C0",
            "grey":   "#808080",
            "brown":  "#8B4513",
            "purple": "#800080",
            "unknown":"#808080",
        }

        return {
            "color":            best_color,
            "color_confidence": confidence,
            "color_hex":        COLOR_HEX_MAP.get(best_color, "#808080"),
        }

    @staticmethod
    def detect_plate_region(image: np.ndarray) -> Optional[Dict[str, Any]]:
        """
        Detect license plate region using YOLOv8
        Returns bounding box coordinates and confidence
        """
        model = get_yolo_model()
        if model is None:
            return None

        try:
            results = model(image, verbose=False)

            for result in results:
                boxes = result.boxes
                if boxes is None or len(boxes) == 0:
                    continue

                confidences = boxes.conf.cpu().numpy()
                best_idx = np.argmax(confidences)

                if confidences[best_idx] < settings.CONFIDENCE_THRESHOLD:
                    continue

                x1, y1, x2, y2 = boxes.xyxy[best_idx].cpu().numpy().astype(int)
                confidence = float(confidences[best_idx])
                plate_region = image[y1:y2, x1:x2]

                return {
                    "bbox":         {"x1": x1, "y1": y1, "x2": x2, "y2": y2},
                    "confidence":   confidence,
                    "plate_region": plate_region,
                }

            return None

        except Exception as e:
            print(f"Detection error: {e}")
            return None

    @staticmethod
    def recognize_plate_text(plate_region: np.ndarray) -> Optional[Dict[str, Any]]:
        """
        Recognize text from license plate region using EasyOCR
        """
        reader = get_ocr_reader()
        if reader is None:
            return None

        try:
            gray     = cv2.cvtColor(plate_region, cv2.COLOR_BGR2GRAY)
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            denoised = cv2.fastNlMeansDenoising(thresh, None, 10, 7, 21)

            results = reader.readtext(denoised)
            if not results:
                return None

            texts       = []
            confidences = []
            for (_, text, conf) in results:
                texts.append(text)
                confidences.append(conf)

            full_text = ' '.join(texts)
            full_text = re.sub(r'[^A-Z0-9\s\-]', '', full_text.upper())
            full_text = full_text.replace(' ', '-')

            avg_confidence = sum(confidences) / len(confidences) if confidences else 0

            return {"text": full_text, "confidence": avg_confidence}

        except Exception as e:
            print(f"OCR error: {e}")
            return None

    @staticmethod
    def validate_plate_format(plate_text: str) -> Tuple[bool, str]:
        """
        Validate and clean license plate format
        Returns (is_valid, cleaned_plate)
        """
        cleaned = re.sub(r'[^A-Z0-9]', '', plate_text.upper())

        if len(cleaned) < 5:
            return False, cleaned

        for pattern in ANPRService.PLATE_PATTERNS:
            if re.match(pattern, plate_text.upper()):
                return True, cleaned

        if 5 <= len(cleaned) <= 10:
            return True, cleaned

        return False, cleaned

    @staticmethod
    async def process_image(image_input: str) -> Dict[str, Any]:
        """
        Main ANPR processing pipeline
        Algorithm: Image → Preprocess → YOLO → OCR → Color Detection → Validate → Result

        Args:
            image_input: Base64 encoded image (with or without data URI prefix)
                         or absolute file path starting with '/'.

        Returns:
            Dict containing:
                success          (bool)
                plate_number     (str | None)
                confidence       (float | None)  - OCR confidence
                color            (str)           - detected vehicle colour
                color_confidence (float)
                color_hex        (str)           - hex code for UI badge
                vehicle_type     (str | None)    - reserved for future classifier
                bounding_box     (dict | None)
                processing_time_ms (float)
                message          (str)
        """
        start_time = datetime.utcnow()

        # ── Decode image ────────────────────────────────────────────────────
        if image_input.startswith('data:image'):
            image = ANPRService.decode_base64_image(image_input)
        elif image_input.startswith('/'):
            image = cv2.imread(image_input)
        else:
            image = ANPRService.decode_base64_image(image_input)

        if image is None:
            return {
                "success":           False,
                "plate_number":      None,
                "confidence":        None,
                "color":             "unknown",
                "color_confidence":  0.0,
                "color_hex":         "#808080",
                "vehicle_type":      None,
                "bounding_box":      None,
                "processing_time_ms": 0,
                "message":           "Failed to decode image",
            }

        # ── Detect vehicle colour (run on original, unscaled image) ─────────
        color_result = ANPRService.detect_vehicle_color(image)

        # ── Preprocess for YOLO ─────────────────────────────────────────────
        processed_image = ANPRService.preprocess_image(image)

        # ── Detect plate region ─────────────────────────────────────────────
        detection = ANPRService.detect_plate_region(processed_image)

        if detection is None:
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            return {
                "success":            False,
                "plate_number":       None,
                "confidence":         None,
                "color":              color_result["color"],
                "color_confidence":   color_result["color_confidence"],
                "color_hex":          color_result["color_hex"],
                "vehicle_type":       None,
                "bounding_box":       None,
                "processing_time_ms": processing_time,
                "message":            "No license plate detected",
            }

        # ── OCR ─────────────────────────────────────────────────────────────
        ocr_result = ANPRService.recognize_plate_text(detection["plate_region"])

        if ocr_result is None:
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            return {
                "success":            False,
                "plate_number":       None,
                "confidence":         detection["confidence"],
                "color":              color_result["color"],
                "color_confidence":   color_result["color_confidence"],
                "color_hex":          color_result["color_hex"],
                "vehicle_type":       None,
                "bounding_box":       detection["bbox"],
                "processing_time_ms": processing_time,
                "message":            "Failed to recognize plate text",
            }

        # ── Validate plate format ────────────────────────────────────────────
        is_valid, cleaned_plate = ANPRService.validate_plate_format(ocr_result["text"])
        processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000

        # ── Low-confidence OCR check ─────────────────────────────────────────
        if ocr_result["confidence"] < settings.PLATE_CONFIDENCE_THRESHOLD:
            return {
                "success":            False,
                "plate_number":       cleaned_plate,
                "confidence":         ocr_result["confidence"],
                "color":              color_result["color"],
                "color_confidence":   color_result["color_confidence"],
                "color_hex":          color_result["color_hex"],
                "vehicle_type":       None,
                "bounding_box":       detection["bbox"],
                "processing_time_ms": processing_time,
                "message":            f"Low OCR confidence: {ocr_result['confidence']:.2f}",
            }

        # ── Success ──────────────────────────────────────────────────────────
        return {
            "success":            True,
            "plate_number":       cleaned_plate,
            "confidence":         ocr_result["confidence"],
            "color":              color_result["color"],
            "color_confidence":   color_result["color_confidence"],
            "color_hex":          color_result["color_hex"],
            "vehicle_type":       None,   # reserved – extend with a classifier later
            "bounding_box":       detection["bbox"],
            "processing_time_ms": processing_time,
            "message":            "Plate recognized successfully",
        }

    @staticmethod
    async def process_frame(frame: np.ndarray) -> Dict[str, Any]:
        """
        Process a single video frame for real-time ANPR.
        Used by the camera-entry live feed.

        Args:
            frame: BGR OpenCV image (numpy ndarray)

        Returns:
            Same dict structure as process_image()
        """
        encoded = ANPRService.encode_image_to_base64(frame)
        return await ANPRService.process_image(encoded)