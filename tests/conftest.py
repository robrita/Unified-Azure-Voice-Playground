"""
Pytest configuration and shared fixtures for document extraction tests.

This module provides common fixtures and configuration for all test modules,
including mock services, sample files, and environment setup.
"""

import os
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from PIL import Image

# Test data directory
TEST_DATA_DIR = Path(__file__).parent / "data"


@pytest.fixture
def test_data_dir():
    """Provide path to test data directory."""
    return TEST_DATA_DIR


@pytest.fixture
def sample_image_file():
    """Provide a sample image file from test data."""
    image_path = TEST_DATA_DIR / "bir2303-true-10.png"
    if not image_path.exists():
        pytest.skip(f"Test image not found: {image_path}")

    with open(image_path, "rb") as f:
        file_bytes = f.read()

    # Create a mock uploaded file object (mimics Streamlit's UploadedFile)
    mock_file = MagicMock()
    mock_file.name = image_path.name
    mock_file.type = "image/png"
    mock_file.getvalue.return_value = file_bytes
    mock_file.read.return_value = file_bytes

    return mock_file


@pytest.fixture
def all_sample_images():
    """Provide all sample image files from test data."""
    image_files = list(TEST_DATA_DIR.glob("*.png"))

    if not image_files:
        pytest.skip(f"No test images found in {TEST_DATA_DIR}")

    mock_files = []
    for image_path in image_files:
        with open(image_path, "rb") as f:
            file_bytes = f.read()

        mock_file = MagicMock()
        mock_file.name = image_path.name
        mock_file.type = "image/png"
        mock_file.getvalue.return_value = file_bytes
        mock_file.read.return_value = file_bytes

        mock_files.append(mock_file)

    return mock_files


@pytest.fixture
def mock_pdf_file():
    """Create a mock PDF file for testing PDF handling."""
    # Create a simple PDF-like byte content
    # Note: This is a minimal PDF structure for testing purposes
    pdf_content = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n%%EOF"

    mock_file = MagicMock()
    mock_file.name = "test_document.pdf"
    mock_file.type = "application/pdf"
    mock_file.getvalue.return_value = pdf_content
    mock_file.read.return_value = pdf_content

    return mock_file


@pytest.fixture
def mock_invalid_file():
    """Create a mock invalid file for testing error handling."""
    invalid_content = b"This is not a valid image or PDF"

    mock_file = MagicMock()
    mock_file.name = "invalid_file.txt"
    mock_file.type = "text/plain"
    mock_file.getvalue.return_value = invalid_content
    mock_file.read.return_value = invalid_content

    return mock_file


@pytest.fixture
def mock_empty_file():
    """Create a mock empty file for testing edge cases."""
    mock_file = MagicMock()
    mock_file.name = "empty_file.png"
    mock_file.type = "image/png"
    mock_file.getvalue.return_value = b""
    mock_file.read.return_value = b""

    return mock_file


@pytest.fixture
def temp_output_dir(tmp_path):
    """Create a temporary directory for test outputs."""
    output_dir = tmp_path / "outputs"
    output_dir.mkdir()
    return output_dir


@pytest.fixture
def mock_extraction_result():
    """Provide a mock extraction result structure."""
    return {
        "service": "ADI-Template",
        "file_info": {
            "name": "test_file.png",
            "type": "image/png",
            "size": 1024,
        },
        "model_info": {
            "model_id": "test-model-v1",
            "api_version": "2024-01-01",
        },
        "documents": [
            {
                "document_number": 1,
                "doc_type": "BIR Tax Document",
                "confidence": 0.95,
                "fields": {
                    "tin": {
                        "type": "string",
                        "content": "123-456-789-00000",
                        "confidence": 0.98,
                    },
                    "taxpayerName": {
                        "type": "string",
                        "content": "Sample Corporation",
                        "confidence": 0.96,
                    },
                    "registeredDate": {
                        "type": "date",
                        "content": "01/15/2024",
                        "confidence": 0.94,
                    },
                },
            }
        ],
        "processing_info": {
            "pages_processed": 1,
            "documents_found": 1,
            "processing_time_seconds": 2.5,
        },
    }


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Mock environment variables for unit testing (no real Azure calls)."""
    env_vars = {
        "AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT": "https://test-endpoint.cognitiveservices.azure.com/",
        "AZURE_DOCUMENT_INTELLIGENCE_KEY": "test_key_12345",
        "AZURE_DOCUMENT_INTELLIGENCE_TEMPLATE_MODEL": "prebuilt-document",
        "AZURE_DOCUMENT_INTELLIGENCE_NEURAL_MODEL": "prebuilt-layout",
        "AZURE_DOCUMENT_INTELLIGENCE_CLASSIFICATION_MODEL": "bir2303-classifier",
        "AZURE_OPENAI_ENDPOINT": "https://test-openai.openai.azure.com/",
        "AZURE_OPENAI_API_KEY": "test_openai_key",
        "AZURE_OPENAI_DEPLOYMENT_GPT4-1": "gpt-4-vision",
        "AZURE_OPENAI_DEPLOYMENT_GPT5": "gpt-5-vision",
        "AZURE_MISTRAL_DOCUMENT_AI_ENDPOINT": "https://test-mistral.azure.com/",
        "AZURE_MISTRAL_DOCUMENT_AI_KEY": "test_mistral_key",
        "AZURE_CONTENT_UNDERSTANDING_ENDPOINT": "https://test-content.azure.com/",
        "AZURE_CONTENT_UNDERSTANDING_SUBSCRIPTION_KEY": "test_content_key",
        "AZURE_CONTENT_UNDERSTANDING_ANALYZER_ID": "test_analyzer",
        "AZURE_CONTENT_UNDERSTANDING_API_VERSION": "2025-05-01-preview",
    }

    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)

    return env_vars


@pytest.fixture
def real_env_vars():
    """Load actual environment variables from .env file for integration tests.

    This fixture loads real Azure credentials for integration testing.
    Use this fixture for tests marked with @pytest.mark.integration.
    """
    from dotenv import load_dotenv

    # Load .env file from project root
    env_path = Path(__file__).parent.parent / ".env"

    if not env_path.exists():
        pytest.skip(
            f".env file not found at {env_path}. Integration tests require real credentials."
        )

    # Load environment variables from .env
    load_dotenv(env_path, override=True)

    # Return the loaded environment variables
    env_vars = {
        "AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT": os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT"),
        "AZURE_DOCUMENT_INTELLIGENCE_KEY": os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY"),
        "AZURE_DOCUMENT_INTELLIGENCE_TEMPLATE_MODEL": os.getenv(
            "AZURE_DOCUMENT_INTELLIGENCE_TEMPLATE_MODEL"
        ),
        "AZURE_DOCUMENT_INTELLIGENCE_NEURAL_MODEL": os.getenv(
            "AZURE_DOCUMENT_INTELLIGENCE_NEURAL_MODEL"
        ),
        "AZURE_DOCUMENT_INTELLIGENCE_CLASSIFICATION_MODEL": os.getenv(
            "AZURE_DOCUMENT_INTELLIGENCE_CLASSIFICATION_MODEL"
        ),
        "AZURE_OPENAI_ENDPOINT": os.getenv("AZURE_OPENAI_ENDPOINT"),
        "AZURE_OPENAI_API_KEY": os.getenv("AZURE_OPENAI_API_KEY"),
        "AZURE_OPENAI_DEPLOYMENT_GPT4-1": os.getenv("AZURE_OPENAI_DEPLOYMENT_GPT4-1"),
        "AZURE_OPENAI_DEPLOYMENT_GPT5": os.getenv("AZURE_OPENAI_DEPLOYMENT_GPT5"),
        "AZURE_MISTRAL_DOCUMENT_AI_ENDPOINT": os.getenv("AZURE_MISTRAL_DOCUMENT_AI_ENDPOINT"),
        "AZURE_MISTRAL_DOCUMENT_AI_KEY": os.getenv("AZURE_MISTRAL_DOCUMENT_AI_KEY"),
        "AZURE_CONTENT_UNDERSTANDING_ENDPOINT": os.getenv("AZURE_CONTENT_UNDERSTANDING_ENDPOINT"),
        "AZURE_CONTENT_UNDERSTANDING_SUBSCRIPTION_KEY": os.getenv(
            "AZURE_CONTENT_UNDERSTANDING_SUBSCRIPTION_KEY"
        ),
        "AZURE_CONTENT_UNDERSTANDING_ANALYZER_ID": os.getenv(
            "AZURE_CONTENT_UNDERSTANDING_ANALYZER_ID"
        ),
        "AZURE_CONTENT_UNDERSTANDING_API_VERSION": os.getenv(
            "AZURE_CONTENT_UNDERSTANDING_API_VERSION"
        ),
    }

    # Verify at least some credentials are loaded
    if not any(env_vars.values()):
        pytest.skip(
            "No Azure credentials found in .env file. Integration tests require valid credentials."
        )

    return env_vars


@pytest.fixture
def mock_missing_env_vars(monkeypatch):
    """Mock missing environment variables for testing error cases."""
    # Clear all Azure-related env vars
    azure_keys = [
        "AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT",
        "AZURE_DOCUMENT_INTELLIGENCE_KEY",
        "AZURE_DOCUMENT_INTELLIGENCE_CLASSIFICATION_MODEL",
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_API_KEY",
        "AZURE_MISTRAL_DOCUMENT_AI_ENDPOINT",
        "AZURE_MISTRAL_DOCUMENT_AI_KEY",
        "AZURE_CONTENT_UNDERSTANDING_ENDPOINT",
        "AZURE_CONTENT_UNDERSTANDING_SUBSCRIPTION_KEY",
        "AZURE_CONTENT_UNDERSTANDING_ANALYZER_ID",
    ]

    for key in azure_keys:
        monkeypatch.delenv(key, raising=False)


@pytest.fixture
def mock_content_understanding_env(monkeypatch):
    """Mock Content Understanding environment variables."""
    env_vars = {
        "AZURE_CONTENT_UNDERSTANDING_ENDPOINT": "https://test-cu-endpoint.cognitiveservices.azure.com/",
        "AZURE_CONTENT_UNDERSTANDING_SUBSCRIPTION_KEY": "test_cu_key_12345",
        "AZURE_CONTENT_UNDERSTANDING_ANALYZER_ID": "test-analyzer-id",
        "AZURE_CONTENT_UNDERSTANDING_API_VERSION": "2025-05-01-preview",
    }
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)
    return env_vars


@pytest.fixture
def mock_mistral_env(monkeypatch):
    """Mock Mistral Document AI environment variables."""
    env_vars = {
        "AZURE_MISTRAL_DOCUMENT_AI_ENDPOINT": "https://test-mistral-endpoint.inference.ai.azure.com/v1/chat/completions",
        "AZURE_MISTRAL_DOCUMENT_AI_KEY": "test_mistral_key_12345",
    }
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)
    return env_vars


@pytest.fixture
def sample_json_results():
    """Provide sample JSON results structure."""
    return {
        "results": [
            {
                "file_name": "test_file_1.png",
                "service_name": "Test Service 1",
                "pages_count": 1,
                "document_confidence": 0.95,
                "processing_time": 2.5,
                "fields": [
                    {"name": "tin", "value": "123-456-789-00000", "confidence": 0.98},
                    {"name": "taxpayerName", "value": "Sample Corp", "confidence": 0.96},
                ],
            },
            {
                "file_name": "test_file_2.png",
                "service_name": "Test Service 2",
                "pages_count": 1,
                "document_confidence": 0.92,
                "processing_time": 3.1,
                "fields": [
                    {"name": "tin", "value": "987-654-321-00000", "confidence": 0.94},
                    {"name": "taxpayerName", "value": "Another Corp", "confidence": 0.91},
                ],
            },
        ]
    }


@pytest.fixture(autouse=True)
def reset_streamlit_session():
    """Reset Streamlit session state between tests."""
    # Import here to avoid issues when streamlit is not available
    try:
        import streamlit as st

        # Clear session state
        if hasattr(st, "session_state"):
            st.session_state.clear()
    except (ImportError, AttributeError):
        # Streamlit not available or session_state not initialized
        pass


@pytest.fixture
def mock_pil_image():
    """Create a mock PIL Image for testing."""
    # Create a simple 100x100 RGB image
    image = Image.new("RGB", (100, 100), color="white")
    return image


def pytest_configure(config):
    """Pytest configuration hook."""
    # Register custom markers
    config.addinivalue_line(
        "markers", "integration: mark test as integration test (requires Azure services)"
    )
    config.addinivalue_line("markers", "unit: mark test as unit test (no external dependencies)")
    config.addinivalue_line("markers", "slow: mark test as slow running test")
