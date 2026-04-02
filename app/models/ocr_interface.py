"""Minimal OCR interface supporting the Baidu OCR provider."""

from __future__ import annotations

import base64
from dataclasses import dataclass, field, replace
import json
import os
from pathlib import Path
import subprocess
from typing import Any, Callable, Protocol
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.models.constants import SCAN_OCR_REVIEW_THRESHOLD

ALLOWED_OCR_PROVIDERS = frozenset({"baidu"})
ALLOWED_DOCUMENT_TYPES = frozenset(
    {
        "homework_sheet",
        "exam_paper",
        "score_table",
        "teacher_feedback_sheet",
        "plan_notice",
        "student_profile_form",
        "textbook",
        "mixed_document",
        "unknown_document",
    }
)


class OCRConfigurationError(ValueError):
    """Raised when OCR provider configuration is incomplete or invalid."""


def _require_text(field_name: str, value: str) -> str:
    text = value.strip()
    if not text:
        raise ValueError(f"{field_name} must not be empty")
    return text


def _ensure_confidence(value: float, field_name: str) -> float:
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"{field_name} must be between 0 and 1")
    return value


def _default_document_type(document_type_hint: str | None) -> str:
    return document_type_hint or "unknown_document"


@dataclass(frozen=True)
class OCRBoundingBox:
    left: float
    top: float
    right: float
    bottom: float

    def __post_init__(self) -> None:
        if self.right < self.left or self.bottom < self.top:
            raise ValueError("invalid bounding box coordinates")


@dataclass(frozen=True)
class OCRTextBlock:
    text: str
    confidence: float
    page_number: int
    bbox: OCRBoundingBox | None = None
    region_ref: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "text", _require_text("text", self.text))
        object.__setattr__(self, "confidence", _ensure_confidence(self.confidence, "confidence"))
        if self.page_number <= 0:
            raise ValueError("page_number must be positive")


@dataclass(frozen=True)
class OCRPageResult:
    page_number: int
    blocks: tuple[OCRTextBlock, ...] = ()
    image_ref: str | None = None

    def __post_init__(self) -> None:
        if self.page_number <= 0:
            raise ValueError("page_number must be positive")
        for block in self.blocks:
            if block.page_number != self.page_number:
                raise ValueError("block page_number must match OCRPageResult.page_number")

    @property
    def page_confidence(self) -> float:
        if not self.blocks:
            return 0.0
        return sum(block.confidence for block in self.blocks) / len(self.blocks)


@dataclass(frozen=True)
class OCRRequest:
    provider: str
    raw_input_ref: str
    source_file_ref: str
    trace_id: str
    document_type_hint: str | None = None
    page_numbers: tuple[int, ...] = ()
    provider_options: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        provider = self.provider.strip().lower()
        if provider not in ALLOWED_OCR_PROVIDERS:
            allowed = ", ".join(sorted(ALLOWED_OCR_PROVIDERS))
            raise ValueError(f"unsupported OCR provider: {provider}. allowed: {allowed}")
        object.__setattr__(self, "provider", provider)
        object.__setattr__(self, "raw_input_ref", _require_text("raw_input_ref", self.raw_input_ref))
        object.__setattr__(self, "source_file_ref", _require_text("source_file_ref", self.source_file_ref))
        object.__setattr__(self, "trace_id", _require_text("trace_id", self.trace_id))
        if self.document_type_hint is not None:
            document_type_hint = self.document_type_hint.strip()
            if document_type_hint not in ALLOWED_DOCUMENT_TYPES:
                raise ValueError(f"unsupported document_type_hint: {document_type_hint}")
            object.__setattr__(self, "document_type_hint", document_type_hint)
        if any(page_number <= 0 for page_number in self.page_numbers):
            raise ValueError("page_numbers must all be positive")


@dataclass(frozen=True)
class OCRDocumentResult:
    provider: str
    raw_input_ref: str
    source_file_ref: str
    trace_id: str
    document_type: str
    pages: tuple[OCRPageResult, ...]
    overall_confidence: float
    event_status: str
    review_needed: bool
    extracted_text: str
    warnings: tuple[str, ...] = ()
    review_reasons: tuple[str, ...] = ()
    provider_payload: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        provider = self.provider.strip().lower()
        if provider not in ALLOWED_OCR_PROVIDERS:
            raise ValueError(f"unsupported OCR result provider: {provider}")
        object.__setattr__(self, "provider", provider)
        object.__setattr__(self, "raw_input_ref", _require_text("raw_input_ref", self.raw_input_ref))
        object.__setattr__(self, "source_file_ref", _require_text("source_file_ref", self.source_file_ref))
        object.__setattr__(self, "trace_id", _require_text("trace_id", self.trace_id))
        if self.document_type not in ALLOWED_DOCUMENT_TYPES:
            raise ValueError(f"unsupported document_type: {self.document_type}")
        object.__setattr__(
            self,
            "overall_confidence",
            _ensure_confidence(self.overall_confidence, "overall_confidence"),
        )
        if self.event_status not in {"success", "degraded", "review_needed"}:
            raise ValueError("event_status must be success, degraded, or review_needed")
        if self.review_needed != (self.event_status == "review_needed"):
            raise ValueError("review_needed must match event_status")

    @classmethod
    def from_pages(
        cls,
        *,
        request: OCRRequest,
        document_type: str,
        pages: list[OCRPageResult] | tuple[OCRPageResult, ...],
        overall_confidence: float | None = None,
        warnings: list[str] | tuple[str, ...] | None = None,
        provider_payload: dict[str, Any] | None = None,
    ) -> "OCRDocumentResult":
        if document_type not in ALLOWED_DOCUMENT_TYPES:
            raise ValueError(f"unsupported document_type: {document_type}")

        normalized_pages = tuple(sorted(pages, key=lambda page: page.page_number))
        extracted_text = "\n".join(
            block.text
            for page in normalized_pages
            for block in page.blocks
        ).strip()

        if overall_confidence is None:
            if normalized_pages:
                overall_confidence = sum(page.page_confidence for page in normalized_pages) / len(normalized_pages)
            else:
                overall_confidence = 0.0
        overall_confidence = _ensure_confidence(overall_confidence, "overall_confidence")

        review_reasons: list[str] = []
        if not extracted_text:
            review_reasons.append("empty_text")
        if overall_confidence < SCAN_OCR_REVIEW_THRESHOLD:
            review_reasons.append("low_confidence")
        if document_type == "unknown_document":
            review_reasons.append("unknown_document_type")

        normalized_warnings = tuple(warnings or ())
        if review_reasons:
            event_status = "review_needed"
        elif normalized_warnings:
            event_status = "degraded"
        else:
            event_status = "success"

        return cls(
            provider=request.provider,
            raw_input_ref=request.raw_input_ref,
            source_file_ref=request.source_file_ref,
            trace_id=request.trace_id,
            document_type=document_type,
            pages=normalized_pages,
            overall_confidence=overall_confidence,
            event_status=event_status,
            review_needed=bool(review_reasons),
            extracted_text=extracted_text,
            warnings=normalized_warnings,
            review_reasons=tuple(review_reasons),
            provider_payload=provider_payload or {},
        )


class OCRProvider(Protocol):
    name: str

    def recognize(self, request: OCRRequest) -> OCRDocumentResult:
        ...


OCRRunner = Callable[[OCRRequest], OCRDocumentResult]
HTTPPost = Callable[[str, bytes, dict[str, str]], dict[str, Any]]


@dataclass(frozen=True)
class BaiduOCRConfig:
    api_key: str
    secret_key: str
    app_id: str | None = None
    token_url: str = "https://aip.baidubce.com/oauth/2.0/token"
    ocr_url: str = "https://aip.baidubce.com/rest/2.0/ocr/v1/accurate_basic"

    @classmethod
    def from_env(
        cls,
        env: dict[str, str] | None = None,
        *,
        required: bool = True,
    ) -> "BaiduOCRConfig | None":
        source = os.environ if env is None else env
        api_key = source.get("BAIDU_OCR_API_KEY", "").strip()
        secret_key = source.get("BAIDU_OCR_SECRET_KEY", "").strip()
        app_id = source.get("BAIDU_OCR_APP_ID", "").strip() or None

        if not api_key and not secret_key and not app_id and not required:
            return None

        if not api_key or not secret_key:
            raise OCRConfigurationError(
                "BAIDU_OCR_API_KEY and BAIDU_OCR_SECRET_KEY must both be set for baidu OCR"
            )

        return cls(api_key=api_key, secret_key=secret_key, app_id=app_id)


def _default_http_post(url: str, body: bytes, headers: dict[str, str]) -> dict[str, Any]:
    request = Request(url, data=body, headers=headers, method="POST")
    with urlopen(request) as response:
        return json.loads(response.read().decode("utf-8"))


def _read_baidu_image_payload(source_file_ref: str) -> str:
    source_path = Path(source_file_ref)
    if not source_path.exists():
        raise FileNotFoundError(f"OCR source file not found: {source_file_ref}")

    return base64.b64encode(source_path.read_bytes()).decode("ascii")


def _pdf_to_images_base64(pdf_path: str, max_pages: int = 10) -> list[tuple[int, str]]:
    """Convert PDF pages to base64-encoded images.

    Args:
        pdf_path: Path to PDF file
        max_pages: Maximum number of pages to process

    Returns:
        List of (page_number, base64_image) tuples
    """
    try:
        import fitz  # PyMuPDF
    except ImportError:
        raise OCRConfigurationError("PyMuPDF (fitz) is required for PDF to image conversion")

    doc = fitz.open(pdf_path)
    images = []

    for page_num in range(min(len(doc), max_pages)):
        page = doc[page_num]
        # Render page to image (zoom=2 for better quality)
        mat = fitz.Matrix(2, 2)
        pix = page.get_pixmap(matrix=mat)

        # Convert to PNG bytes
        img_bytes = pix.tobytes("png")
        img_base64 = base64.b64encode(img_bytes).decode("ascii")
        images.append((page_num + 1, img_base64))

    doc.close()
    return images


def _read_baidu_page_payloads(request: OCRRequest, *, max_pdf_pages: int = 20) -> list[tuple[int, str]]:
    source_path = Path(request.source_file_ref)
    if not source_path.exists():
        raise FileNotFoundError(f"OCR source file not found: {request.source_file_ref}")

    suffix = source_path.suffix.lower()
    page_numbers = set(request.page_numbers)

    if suffix in {".png", ".jpg", ".jpeg", ".bmp"}:
        if page_numbers and page_numbers != {1}:
            raise OCRConfigurationError("image OCR requests may only reference page 1")
        return [(1, _read_baidu_image_payload(request.source_file_ref))]

    if suffix == ".pdf":
        pages = _pdf_to_images_base64(str(source_path), max_pages=max_pdf_pages)
        if page_numbers:
            pages = [(page_number, image) for page_number, image in pages if page_number in page_numbers]
        if not pages:
            raise OCRConfigurationError("no PDF pages available for baidu OCR request")
        return pages

    raise OCRConfigurationError(
        "baidu OCR runner currently supports png/jpg/jpeg/bmp images and PDF files"
    )


def build_baidu_runner(
    config: BaiduOCRConfig,
    *,
    http_post: HTTPPost | None = None,
) -> OCRRunner:
    post = _default_http_post if http_post is None else http_post

    def runner(request: OCRRequest) -> OCRDocumentResult:
        token_payload = urlencode(
            {
                "grant_type": "client_credentials",
                "client_id": config.api_key,
                "client_secret": config.secret_key,
            }
        ).encode("utf-8")
        token_response = post(
            config.token_url,
            token_payload,
            {"Content-Type": "application/x-www-form-urlencoded"},
        )
        access_token = str(token_response.get("access_token", "")).strip()
        if not access_token:
            raise OCRConfigurationError("failed to fetch baidu OCR access token")

        pages: list[OCRPageResult] = []
        response_pages: list[dict[str, Any]] = []
        for page_number, image_payload in _read_baidu_page_payloads(request):
            ocr_payload = urlencode({"image": image_payload, "probability": "true"}).encode("utf-8")
            ocr_response = post(
                f"{config.ocr_url}?access_token={access_token}",
                ocr_payload,
                {"Content-Type": "application/x-www-form-urlencoded"},
            )
            response_pages.append({"page_number": page_number, "response": ocr_response})

            blocks: list[OCRTextBlock] = []
            for index, item in enumerate(ocr_response.get("words_result", []), start=1):
                text = str(item.get("words", "")).strip()
                if not text:
                    continue
                probability = item.get("probability", {})
                confidence = probability.get("average")
                if confidence is None:
                    confidence = 1.0
                blocks.append(
                    OCRTextBlock(
                        text=text,
                        confidence=float(confidence),
                        page_number=page_number,
                        region_ref=f"baidu_block_{page_number}_{index}",
                    )
                )

            pages.append(
                OCRPageResult(
                    page_number=page_number,
                    blocks=tuple(blocks),
                    image_ref=request.source_file_ref,
                )
            )

        return OCRDocumentResult.from_pages(
            request=request,
            document_type=_default_document_type(request.document_type_hint),
            pages=pages,
            provider_payload={"pages": response_pages},
        )

    return runner


def build_baidu_provider(
    *,
    env: dict[str, str] | None = None,
    http_post: HTTPPost | None = None,
) -> "BaiduOCRProvider":
    config = BaiduOCRConfig.from_env(env, required=True)
    if config is None:
        raise OCRConfigurationError("baidu OCR config is missing")
    return BaiduOCRProvider(runner=build_baidu_runner(config, http_post=http_post))


def build_ocr_service_from_env(
    *,
    env: dict[str, str] | None = None,
    baidu_http_post: HTTPPost | None = None,
) -> "OCRService":
    """Build OCR service with baidu as the only official provider.

    Args:
        env: Environment variables (BAIDU_OCR_API_KEY, BAIDU_OCR_SECRET_KEY required)
        baidu_http_post: Optional HTTP post function for testing

    Returns:
        OCRService with baidu provider registered

    Raises:
        OCRConfigurationError: If baidu credentials are missing
    """
    service = OCRService()

    try:
        baidu_config = BaiduOCRConfig.from_env(env, required=True)
    except OCRConfigurationError as exc:
        raise OCRConfigurationError(
            f"baidu OCR is the only supported provider. "
            f"Configure BAIDU_OCR_API_KEY and BAIDU_OCR_SECRET_KEY. "
            f"Original error: {exc}"
        ) from exc

    service.register(BaiduOCRProvider(runner=build_baidu_runner(baidu_config, http_post=baidu_http_post)))

    return service


def _run_provider(provider_name: str, request: OCRRequest, runner: OCRRunner) -> OCRDocumentResult:
    if request.provider != provider_name:
        raise ValueError(f"request provider {request.provider} does not match {provider_name}")
    result = runner(request)
    return replace(
        result,
        provider=provider_name,
        raw_input_ref=request.raw_input_ref,
        source_file_ref=request.source_file_ref,
        trace_id=request.trace_id,
    )


@dataclass
class BaiduOCRProvider:
    runner: OCRRunner
    name: str = field(init=False, default="baidu")

    def recognize(self, request: OCRRequest) -> OCRDocumentResult:
        return _run_provider(self.name, request, self.runner)


@dataclass
class OCRService:
    providers: dict[str, OCRProvider] = field(default_factory=dict)

    def __post_init__(self) -> None:
        normalized: dict[str, OCRProvider] = {}
        for provider in self.providers.values():
            normalized[provider.name] = provider
        self.providers = normalized

    @property
    def available_providers(self) -> tuple[str, ...]:
        return tuple(sorted(self.providers))

    def register(self, provider: OCRProvider) -> None:
        if provider.name in self.providers:
            raise ValueError(f"provider already registered: {provider.name}")
        self.providers[provider.name] = provider

    def recognize(self, request: OCRRequest) -> OCRDocumentResult:
        provider = self.providers.get(request.provider)
        if provider is None:
            available = ", ".join(self.available_providers) or "none"
            raise ValueError(f"provider not configured: {request.provider}. available: {available}")
        return provider.recognize(request)
