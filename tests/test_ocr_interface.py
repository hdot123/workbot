from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest

from app.models.ocr_interface import (
    BaiduOCRConfig,
    BaiduOCRProvider,
    LocalOCRProvider,
    OCRConfigurationError,
    OCRDocumentResult,
    OCRPageResult,
    OCRRequest,
    OCRService,
    OCRTextBlock,
    build_baidu_runner,
    build_local_provider,
    build_ocr_service_from_env,
)


def build_request(**overrides: object) -> OCRRequest:
    payload = {
        "provider": "local",
        "raw_input_ref": "RAW_SCAN_001",
        "source_file_ref": "/tmp/input.pdf",
        "trace_id": "TRACE_OCR_001",
        "document_type_hint": "homework_sheet",
    }
    payload.update(overrides)
    return OCRRequest(**payload)


def build_page(page_number: int, text: str, confidence: float) -> OCRPageResult:
    return OCRPageResult(
        page_number=page_number,
        blocks=(OCRTextBlock(text=text, confidence=confidence, page_number=page_number),),
    )


def test_local_provider_dispatches_success_result() -> None:
    def runner(request: OCRRequest) -> OCRDocumentResult:
        return OCRDocumentResult.from_pages(
            request=request,
            document_type="homework_sheet",
            pages=[build_page(1, "位移是矢量。", 0.92)],
        )

    service = OCRService({"local": LocalOCRProvider(runner=runner)})

    result = service.recognize(build_request())

    assert result.provider == "local"
    assert result.event_status == "success"
    assert result.review_needed is False
    assert result.extracted_text == "位移是矢量。"


def test_baidu_provider_low_confidence_requires_review() -> None:
    def runner(request: OCRRequest) -> OCRDocumentResult:
        return OCRDocumentResult.from_pages(
            request=request,
            document_type="exam_paper",
            pages=[build_page(1, "加速度方向", 0.69)],
        )

    service = OCRService({"baidu": BaiduOCRProvider(runner=runner)})

    result = service.recognize(build_request(provider="baidu", document_type_hint="exam_paper"))

    assert result.provider == "baidu"
    assert result.event_status == "review_needed"
    assert result.review_needed is True
    assert "low_confidence" in result.review_reasons


def test_unknown_document_type_requires_review_even_with_high_confidence() -> None:
    def runner(request: OCRRequest) -> OCRDocumentResult:
        return OCRDocumentResult.from_pages(
            request=request,
            document_type="unknown_document",
            pages=[build_page(1, "来源不明文本片段", 0.96)],
        )

    service = OCRService({"local": LocalOCRProvider(runner=runner)})

    result = service.recognize(build_request(document_type_hint="unknown_document"))

    assert result.event_status == "review_needed"
    assert "unknown_document_type" in result.review_reasons


def test_register_duplicate_provider_is_blocked() -> None:
    service = OCRService({"local": LocalOCRProvider(runner=lambda request: pytest.fail("not called"))})

    with pytest.raises(ValueError, match="provider already registered"):
        service.register(LocalOCRProvider(runner=lambda request: pytest.fail("not called")))


def test_request_provider_must_be_configured() -> None:
    service = OCRService()

    with pytest.raises(ValueError, match="provider not configured"):
        service.recognize(build_request())


def test_baidu_config_requires_api_key_and_secret_key() -> None:
    with pytest.raises(OCRConfigurationError, match="BAIDU_OCR_API_KEY"):
        BaiduOCRConfig.from_env({"BAIDU_OCR_API_KEY": "only-key"}, required=True)


def test_build_service_from_env_registers_baidu_when_credentials_exist() -> None:
    service = build_ocr_service_from_env(
        env={
            "LOCAL_OCR_PROVIDER": "ollama",
            "LOCAL_OCR_MODEL": "glm-ocr",
            "BAIDU_OCR_API_KEY": "key",
            "BAIDU_OCR_SECRET_KEY": "secret",
        },
        local_runner=lambda request: OCRDocumentResult.from_pages(
            request=request,
            document_type="homework_sheet",
            pages=[build_page(1, "本地 OCR", 0.95)],
        ),
        baidu_http_post=lambda url, body, headers: {"access_token": "token"}
        if "oauth/2.0/token" in url
        else {"words_result": [{"words": "百度 OCR", "probability": {"average": 0.88}}]},
    )

    assert service.available_providers == ("baidu", "local")


def test_baidu_runner_parses_words_result_with_probability(tmp_path: Path) -> None:
    image_path = tmp_path / "ocr.png"
    image_path.write_bytes(b"fake-image")

    responses = [
        {"access_token": "token"},
        {"words_result": [{"words": "百度 OCR 片段", "probability": {"average": 0.83}}]},
    ]

    def fake_http_post(url: str, body: bytes, headers: dict[str, str]) -> dict[str, object]:
        return responses.pop(0)

    runner = build_baidu_runner(
        BaiduOCRConfig(api_key="key", secret_key="secret"),
        http_post=fake_http_post,
    )

    result = runner(
        build_request(
            provider="baidu",
            source_file_ref=str(image_path),
            document_type_hint="homework_sheet",
        )
    )

    assert result.provider == "baidu"
    assert result.event_status == "success"
    assert result.extracted_text == "百度 OCR 片段"


def test_baidu_runner_access_token_failure_raises() -> None:
    def fake_http_post(url: str, body: bytes, headers: dict[str, str]) -> dict[str, object]:
        return {"error": "invalid_client", "error_description": "invalid credentials"}

    runner = build_baidu_runner(
        BaiduOCRConfig(api_key="key", secret_key="secret"),
        http_post=fake_http_post,
    )

    with pytest.raises(OCRConfigurationError, match="failed to fetch baidu OCR access token"):
        runner(build_request(provider="baidu", source_file_ref="/tmp/fake.png"))


def test_baidu_runner_empty_words_result_triggers_review(tmp_path: Path) -> None:
    image_path = tmp_path / "ocr.png"
    image_path.write_bytes(b"fake-image")

    responses = [
        {"access_token": "token"},
        {"words_result": []},
    ]

    def fake_http_post(url: str, body: bytes, headers: dict[str, str]) -> dict[str, object]:
        return responses.pop(0)

    runner = build_baidu_runner(
        BaiduOCRConfig(api_key="key", secret_key="secret"),
        http_post=fake_http_post,
    )

    result = runner(
        build_request(
            provider="baidu",
            source_file_ref=str(image_path),
            document_type_hint="homework_sheet",
        )
    )

    assert result.event_status == "review_needed"
    assert "empty_text" in result.review_reasons


def test_build_service_from_env_baidu_incomplete_credentials_raises() -> None:
    from app.models.ocr_interface import build_local_provider
    with pytest.raises(OCRConfigurationError, match="invalid baidu OCR env configuration"):
        build_ocr_service_from_env(
            env={"BAIDU_OCR_API_KEY": "only-key"},
            local_runner=lambda request: OCRDocumentResult.from_pages(
                request=request,
                document_type="homework_sheet",
                pages=[build_page(1, "ok", 0.9)],
            ),
        )


def test_build_local_provider_without_runner_raises() -> None:
    provider = build_local_provider(env={})
    with pytest.raises(OCRConfigurationError, match="local OCR runner is not wired yet"):
        provider.recognize(build_request(provider="local"))


def test_build_ocr_service_from_env_local_only() -> None:
    service = build_ocr_service_from_env(
        env={},
        local_runner=lambda request: OCRDocumentResult.from_pages(
            request=request,
            document_type="homework_sheet",
            pages=[build_page(1, "local only", 0.95)],
        ),
    )
    assert service.available_providers == ("local",)


def test_baidu_config_app_id_is_optional() -> None:
    config = BaiduOCRConfig.from_env(
        {"BAIDU_OCR_API_KEY": "k", "BAIDU_OCR_SECRET_KEY": "s"},
        required=True,
    )
    assert config.api_key == "k"
    assert config.secret_key == "s"
    assert config.app_id is None


def test_baidu_config_with_app_id() -> None:
    config = BaiduOCRConfig.from_env(
        {"BAIDU_OCR_API_KEY": "k", "BAIDU_OCR_SECRET_KEY": "s", "BAIDU_OCR_APP_ID": "appid123"},
        required=True,
    )
    assert config.app_id == "appid123"
