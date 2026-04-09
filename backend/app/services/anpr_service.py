"""
ANPR Service: Automatic Number Plate Recognition
Implements YOLOv8 + OCR pipeline as per thesis specifications
Updated: Memory-optimized for Render 512MB limit
"""
import cv2
import numpy as np
from datetime import datetime
from typing import Optional, Dict, Any, Tuple
import base64
import io
from PIL import Image
import re
import gc  # ✅ Added for memory cleanup

from app.config import get_settings

settings = get_settings()

# Configure garbage collection for memory-constrained environment
gc.set_threshold(700, 10, 10)

# Lazy loading of ML models
_yolo_model = None
_ocr_reader = None


def get_yolo_model():
    """Lazy load YOLOv8 model"""
    global _yolo_model
    if _yolo_model is None:
        try:
            from ultralytics import YOLO
            # Use YOLOv8n (nano) for faster inference - smallest model
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
            # Initialize for English only - minimal memory
            _ocr_reader = easyocr.Reader(['en'], gpu=False, verbose=False)
            print("✅ EasyOCR reader loaded")
        except Exception as e:
            print(f"⚠️ EasyOCR loading failed: {e}")
            _ocr_reader = None
    return _ocr_reader


class ANPRService:
    """
    ANPR Service implementing Computer Vision pipeline
    Algorithm: Image → Preprocess → YOLO Detection → OCR → Color Detection → Plate Number
    MEMORY OPTIMIZED for Render 512MB free tier
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
    COLOR_RANGES = {
        "red":    [
            (np.array([0,   70,  50]),  np.array([10,  255, 255])),
            (np.array([170, 70,  50]),  np.array([180, 255, 255])),
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
            
            # ✅ MEMORY FIX: Use smaller max size
            img = Image.open(io.BytesIO(img_data))
            
            # Resize if too large before converting to numpy
            max_dim = 800  # Max dimension to prevent memory overload
            w, h = img.size
            if max(w, h) > max_dim:
                scale = max_dim / max(w, h)
                new_size = (int(w * scale), int(h * scale))
                img = img.resize(new_size, Image.Resampling.LANCZOS)
            
            img_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
            return img_cv
        except Exception as e:
            print(f"Image decode error: {e}")
            return None

    @staticmethod
    def encode_image_to_base64(image: np.ndarray) -> str:
        """Encode OpenCV image to base64"""
        # ✅ MEMORY FIX: Lower quality to reduce size
        encode_params = [cv2.IMWRITE_JPEG_QUALITY, 85]
        _, buffer = cv2.imencode('.jpg', image, encode_params)
        img_str = base64.b64encode(buffer).decode('utf-8')
        return f"data:image/jpeg;base64,{img_str}"

    @staticmethod
    def preprocess_image(image: np.ndarray, target_size: Tuple[int, int] = (320, 320)) -> np.ndarray:
        """
        Preprocess image for ANPR - REDUCED from 640x640 to 320x320 for memory
        """
        h, w = image.shape[:2]
        scale = min(target_size[0] / w, target_size[1] / h)
        new_w = int(w * scale)
        new_h = int(h * scale)

        # ✅ MEMORY FIX: Use INTER_AREA for downsampling (better quality, less memory)
        resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)

        # Use uint8 (default) - most memory efficient
        padded = np.full((target_size[1], target_size[0], 3), 128, dtype=np.uint8)
        y_offset = (target_size[1] - new_h) // 2
        x_offset = (target_size[0] - new_w) // 2
        padded[y_offset:y_offset + new_h, x_offset:x_offset + new_w] = resized

        return padded

    @staticmethod
    def detect_vehicle_color(image: np.ndarray) -> Dict[str, Any]:
        """
        Detect dominant vehicle color - MEMORY OPTIMIZED
        """
        if image is None or image.size == 0:
            return {"color": "unknown", "color_confidence": 0.0, "color_hex": "#808080"}

        # ✅ MEMORY FIX: Resize image immediately to reduce memory footprint
        h, w = image.shape[:2]
        max_dim = 400  # Reduced from full size
        if max(h, w) > max_dim:
            scale = max_dim / max(h, w)
            new_w, new_h = int(w * scale), int(h * scale)
            image = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
            h, w = new_h, new_w

        # ── 1. Crop to vehicle body region ──────────────────────────────────
        top_cut = int(h * 0.10)
        bottom_cut = int(h * 0.20)
        body = image[top_cut: h - bottom_cut, :]

        if body.size == 0:
            body = image

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
                del mask  # ✅ Free mask memory immediately
            color_scores[color_name] = count

        # ── 4. Pick the winner ──────────────────────────────────────────────
        best_color = max(color_scores, key=lambda c: color_scores[c])
        best_count = color_scores[best_color]
        confidence = round(best_count / total_pixels, 4) if total_pixels > 0 else 0.0

        # ── 5. Low-confidence fallback ──────────────────────────────────────
        MIN_CONFIDENCE = 0.05
        if confidence < MIN_CONFIDENCE:
            best_color = "unknown"

        # ── 6. Map colour to hex ────────────────────────────────────────────
        COLOR_HEX_MAP = {
            "red": "#FF0000", "blue": "#0000FF", "green": "#008000",
            "yellow": "#FFFF00", "orange": "#FF8C00", "white": "#FFFFFF",
            "black": "#1A1A1A", "silver": "#C0C0C0", "grey": "#808080",
            "brown": "#8B4513", "purple": "#800080", "unknown": "#808080",
        }

        # ✅ Clean up large arrays
        del hsv, body, image
        gc.collect()

        return {
            "color": best_color,
            "color_confidence": confidence,
            "color_hex": COLOR_HEX_MAP.get(best_color, "#808080"),
        }

    @staticmethod
    def detect_plate_region(image: np.ndarray) -> Optional[Dict[str, Any]]:
        """
        Detect license plate region using YOLOv8
        """
        model = get_yolo_model()
        if model is None:
            return None

        try:
            # ✅ MEMORY FIX: Run with lower confidence, no verbose
            results = model(image, verbose=False, conf=0.3)

            for result in results:
                boxes = result.boxes
                if boxes is None or len(boxes) == 0:
                    continue

                confidences = boxes.conf.cpu().numpy()
                best_idx = np.argmax(confidences)

                if confidences[best_idx] < settings.CONFIDENCE_THRESHOLD:
                    continue

                # ✅ FIXED: Convert numpy types to native Python types
                x1, y1, x2, y2 = map(int, boxes.xyxy[best_idx].cpu().numpy())
                confidence = float(confidences[best_idx])
                
                # Ensure valid coordinates
                h, w = image.shape[:2]
                x1, y1 = max(0, x1), max(0, y1)
                x2, y2 = min(w, x2), min(h, y2)
                
                if x2 <= x1 or y2 <= y1:
                    continue
                    
                plate_region = image[y1:y2, x1:x2]

                return {
                    "bbox": {
                        "x1": int(x1),
                        "y1": int(y1),
                        "x2": int(x2),
                        "y2": int(y2)
                    },
                    "confidence": float(confidence),
                    "plate_region": plate_region,
                }

            return None

        except Exception as e:
            print(f"Detection error: {e}")
            return None

    @staticmethod
    def recognize_plate_text(plate_region: np.ndarray) -> Optional[Dict[str, Any]]:
        """
        Recognize text from license plate region - MEMORY OPTIMIZED
        """
        reader = get_ocr_reader()
        if reader is None:
            return None

        try:
            # ✅ MEMORY FIX: Resize plate region if too large
            h, w = plate_region.shape[:2]
            max_plate_width = 280  # Reduced from 300
            if w > max_plate_width:
                scale = max_plate_width / w
                new_w, new_h = int(w * scale), int(h * scale)
                plate_region = cv2.resize(plate_region, (new_w, new_h), interpolation=cv2.INTER_AREA)

            # Simplified preprocessing - skip heavy denoising
            gray = cv2.cvtColor(plate_region, cv2.COLOR_BGR2GRAY)
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

            # ✅ MEMORY FIX: Skip fastNlMeansDenoising - too memory intensive on Render
            # Run OCR directly on thresholded image
            results = reader.readtext(thresh)

            if not results:
                return None

            texts = []
            confidences = []
            for (_, text, conf) in results:
                texts.append(text)
                confidences.append(conf)

            # Clean text - remove spaces, keep only valid chars
            full_text = ''.join(texts)
            full_text = re.sub(r'[^A-Z0-9]', '', full_text.upper())

            avg_confidence = sum(confidences) / len(confidences) if confidences else 0

            # ✅ Clean up
            del gray, thresh, plate_region
            gc.collect()

            return {"text": full_text, "confidence": avg_confidence}

        except Exception as e:
            print(f"OCR error: {e}")
            return None

    @staticmethod
    def validate_plate_format(plate_text: str) -> Tuple[bool, str]:
        """
        Validate and clean license plate format
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
        Main ANPR processing pipeline - MEMORY OPTIMIZED
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
                "success": False,
                "plate_number": None,
                "confidence": None,
                "color": "unknown",
                "color_confidence": 0.0,
                "color_hex": "#808080",
                "vehicle_type": None,
                "bounding_box": None,
                "processing_time_ms": 0,
                "message": "Failed to decode image",
            }

        # ── Detect vehicle colour ───────────────────────────────────────────
        color_result = ANPRService.detect_vehicle_color(image)

        # ── Preprocess for YOLO ─────────────────────────────────────────────
        processed_image = ANPRService.preprocess_image(image)
        
        # ✅ Free original image memory
        del image
        gc.collect()

        # ── Detect plate region ─────────────────────────────────────────────
        detection = ANPRService.detect_plate_region(processed_image)

        if detection is None:
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            return {
                "success": False,
                "plate_number": None,
                "confidence": None,
                "color": color_result["color"],
                "color_confidence": color_result["color_confidence"],
                "color_hex": color_result["color_hex"],
                "vehicle_type": None,
                "bounding_box": None,
                "processing_time_ms": processing_time,
                "message": "No license plate detected",
            }

        # ── OCR ─────────────────────────────────────────────────────────────
        ocr_result = ANPRService.recognize_plate_text(detection["plate_region"])

        if ocr_result is None:
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            return {
                "success": False,
                "plate_number": None,
                "confidence": detection["confidence"],
                "color": color_result["color"],
                "color_confidence": color_result["color_confidence"],
                "color_hex": color_result["color_hex"],
                "vehicle_type": None,
                "bounding_box": detection["bbox"],
                "processing_time_ms": processing_time,
                "message": "Failed to recognize plate text",
            }

        # ── Validate plate format ────────────────────────────────────────────
        is_valid, cleaned_plate = ANPRService.validate_plate_format(ocr_result["text"])
        processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000

        # ── Low-confidence OCR check ─────────────────────────────────────────
        if ocr_result["confidence"] < settings.PLATE_CONFIDENCE_THRESHOLD:
            return {
                "success": False,
                "plate_number": cleaned_plate,
                "confidence": ocr_result["confidence"],
                "color": color_result["color"],
                "color_confidence": color_result["color_confidence"],
                "color_hex": color_result["color_hex"],
                "vehicle_type": None,
                "bounding_box": detection["bbox"],
                "processing_time_ms": processing_time,
                "message": f"Low OCR confidence: {ocr_result['confidence']:.2f}",
            }

        # ── Success ──────────────────────────────────────────────────────────
        result = {
            "success": True,
            "plate_number": cleaned_plate,
            "confidence": ocr_result["confidence"],
            "color": color_result["color"],
            "color_confidence": color_result["color_confidence"],
            "color_hex": color_result["color_hex"],
            "vehicle_type": None,
            "bounding_box": detection["bbox"],
            "processing_time_ms": processing_time,
            "message": "Plate recognized successfully",
        }
        
        # ✅ Final memory cleanup
        del processed_image, detection, ocr_result
        gc.collect()
        
        return result

    @staticmethod
    async def process_frame(frame: np.ndarray) -> Dict[str, Any]:
        """
        Process a single video frame - MEMORY OPTIMIZED
        """
        # Resize frame immediately to save memory
        h, w = frame.shape[:2]
        max_dim = 640
        if max(h, w) > max_dim:
            scale = max_dim / max(h, w)
            frame = cv2.resize(frame, (int(w*scale), int(h*scale)), interpolation=cv2.INTER_AREA)
        
        encoded = ANPRService.encode_image_to_base64(frame)
        
        # ✅ Clean up frame before processing
        del frame
        gc.collect()
        
        return await ANPRService.process_image(encoded)