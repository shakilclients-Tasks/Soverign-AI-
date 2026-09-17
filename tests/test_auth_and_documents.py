import asyncio

import cv2
import numpy as np

from backend.api.dependencies import current_user
from backend.services.attachment_service import attachment_service
from backend.services.document_service import document_service, safe_filename


def test_trusted_local_context_requires_no_credentials() -> None:
    user = asyncio.run(current_user())
    assert user.id == "local-user"
    assert user.role == "local operator"


def test_text_attachment_extracts_and_reuses_document(isolated_storage) -> None:
    assert safe_filename("../unsafe/report?.txt") == "report_.txt"
    first = attachment_service.create(b"Private local document text", "report.txt", "text/plain")
    second = attachment_service.create(b"Private local document text", "report.txt", "text/plain")
    detail = document_service.get_document(first["document_id"])

    assert first["document_id"] == second["document_id"]
    assert detail is not None
    assert detail["full_text"] == "Private local document text"
    assert first["extraction_status"] == "completed"


def test_image_attachment_runs_local_ocr(isolated_storage) -> None:
    image = np.full((220, 1000, 3), 255, dtype=np.uint8)
    cv2.putText(
        image,
        "SOVEREIGN OCR 2026",
        (35, 135),
        cv2.FONT_HERSHEY_SIMPLEX,
        2.2,
        (0, 0, 0),
        5,
        cv2.LINE_AA,
    )
    encoded, payload = cv2.imencode(".png", image)
    assert encoded

    attachment = attachment_service.create(
        payload.tobytes(), "ocr-test.png", "image/png"
    )
    detail = document_service.get_document(attachment["document_id"])

    assert detail is not None
    assert attachment["extraction_status"] == "completed"
    assert "SOVEREIGN" in detail["full_text"].upper()
    assert "2026" in detail["full_text"]
