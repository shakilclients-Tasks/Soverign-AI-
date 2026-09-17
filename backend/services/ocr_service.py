"""Local OCR with an embedded ONNX engine and optional Tesseract fallback."""

import os
import shutil
import threading
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import pytesseract
from PIL import Image

from backend.core.logging import get_logger

try:
    from rapidocr import RapidOCR
except ImportError:  # pragma: no cover - exercised only on incomplete installs
    RapidOCR = None  # type: ignore[assignment]


logger = get_logger("sovereign.ocr")


class OCRService:
    def __init__(self) -> None:
        self._rapid_engine: Any = None
        self._engine_lock = threading.Lock()
        self._tesseract_cmd = self._find_tesseract()

    @staticmethod
    def _find_tesseract() -> str | None:
        local_app_data = Path(os.environ.get("LOCALAPPDATA", ""))
        candidates = [
            os.environ.get("TESSERACT_CMD"),
            shutil.which("tesseract"),
            str(local_app_data / "Programs" / "Tesseract-OCR" / "tesseract.exe"),
            r"C:Program FilesTesseract-OCR	esseract.exe",
            r"C:Program Files (x86)Tesseract-OCR	esseract.exe",
            r"C:	ools	esseract	esseract.exe",
        ]
        for candidate in candidates:
            if candidate and Path(candidate).is_file():
                pytesseract.pytesseract.tesseract_cmd = candidate
                return candidate
        return None

    def available(self) -> bool:
        return RapidOCR is not None or self._tesseract_cmd is not None

    def backend_name(self) -> str | None:
        if RapidOCR is not None:
            return "RapidOCR (ONNX)"
        if self._tesseract_cmd:
            return "Tesseract"
        return None

    def _rapid(self) -> Any:
        if RapidOCR is None:
            return None
        if self._rapid_engine is None:
            with self._engine_lock:
                if self._rapid_engine is None:
                    self._rapid_engine = RapidOCR()
        return self._rapid_engine

    @staticmethod
    def _rapid_text(result: Any) -> str:
        texts = [str(item).strip() for item in (getattr(result, "txts", None) or ())]
        if not texts:
            return ""
        boxes = getattr(result, "boxes", None)
        if boxes is None or len(boxes) != len(texts):
            return chr(10).join(item for item in texts if item)

        entries: list[dict[str, float | str]] = []
        for text, box in zip(texts, boxes):
            if not text:
                continue
            points = np.asarray(box, dtype=float)
            entries.append(
                {
                    "text": text,
                    "x": float(points[:, 0].min()),
                    "y": float(points[:, 1].mean()),
                    "height": max(1.0, float(points[:, 1].max() - points[:, 1].min())),
                }
            )
        entries.sort(key=lambda item: (float(item["y"]), float(item["x"])))

        lines: list[list[dict[str, float | str]]] = []
        for entry in entries:
            if not lines:
                lines.append([entry])
                continue
            current = lines[-1]
            line_y = sum(float(item["y"]) for item in current) / len(current)
            line_height = max(float(item["height"]) for item in current)
            tolerance = max(12.0, min(line_height, float(entry["height"])) * 0.65)
            if abs(float(entry["y"]) - line_y) <= tolerance:
                current.append(entry)
            else:
                lines.append([entry])
        return chr(10).join(
            " ".join(str(item["text"]) for item in sorted(line, key=lambda item: float(item["x"])))
            for line in lines
        ).strip()

    def _extract_tesseract(self, image: np.ndarray, language: str) -> str:
        if not self._tesseract_cmd:
            return ""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        if gray.shape[1] < 1400:
            scale = min(3.0, 1400 / max(1, gray.shape[1]))
            gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        normalized = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray)
        threshold = cv2.threshold(
            normalized, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
        )[1]
        candidates = [
            pytesseract.image_to_string(
                Image.fromarray(threshold), lang=language, config="--oem 3 --psm 6"
            ).strip(),
            pytesseract.image_to_string(
                Image.fromarray(normalized), lang=language, config="--oem 3 --psm 3"
            ).strip(),
        ]
        return max(candidates, key=len, default="")

    def extract_image(self, image_bytes: bytes, language: str = "eng") -> str:
        array = np.frombuffer(image_bytes, dtype=np.uint8)
        image = cv2.imdecode(array, cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError("The image could not be decoded.")
        errors: list[str] = []

        engine = self._rapid()
        if engine is not None:
            try:
                with self._engine_lock:
                    text = self._rapid_text(engine(image))
                if text:
                    return text
            except Exception as exc:
                logger.warning("RapidOCR extraction failed: %s", exc)
                errors.append(f"RapidOCR: {exc}")

        if self._tesseract_cmd:
            try:
                return self._extract_tesseract(image, language)
            except Exception as exc:
                logger.warning("Tesseract extraction failed: %s", exc)
                errors.append(f"Tesseract: {exc}")

        if errors:
            raise RuntimeError("OCR extraction failed. " + " | ".join(errors))
        if not self.available():
            raise RuntimeError(
                "No OCR engine is installed. Install project requirements to enable RapidOCR."
            )
        return ""


ocr_service = OCRService()
