import asyncio
import os
import pytest
import pytest_asyncio # Import the decorator
from httpx import AsyncClient, ASGITransport # Import ASGITransport

# Ensure the FastAPI app instance is imported
# Adjust the import path if your app instance is elsewhere or named differently
from sass_legal.api.main import app
from sass_legal.core.config import settings # For checking app name in root response

# The event_loop fixture is typically not needed with modern pytest-asyncio,
# as it handles the loop automatically.

@pytest_asyncio.fixture(scope="function") # Decorate the async fixture
async def client() -> AsyncClient:
    """
    Provides an asynchronous HTTP client for testing the FastAPI application.
    The client is configured to talk to the application in-memory using ASGITransport.
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as ac:
        yield ac

@pytest.mark.asyncio
async def test_read_root(client: AsyncClient):
    """
    Test the root endpoint ('/') to ensure it returns a welcome message
    and reflects the configured application name.
    """
    response = await client.get("/")
    assert response.status_code == 200
    json_response = response.json()
    assert settings.APP_NAME in json_response["message"]
    assert "debug_mode" in json_response
    assert "api_prefix_configured" in json_response

# Correctly point to the existing test_files directory used by other tests.
# This directory should contain 'dummy.txt', 'dummy.pdf', 'dummy.docx'
# created by previous test setups (e.g., in test_document_converter.py's setup fixture or manually).
# Path is relative to the root of the project if tests are run from there,
# or relative to this file's parent's parent if tests are in a subdir.
# For /app/sass_legal/tests/test_api.py, to reach /app/sass_legal/tests/test_files:
TEST_FILES_DIR = os.path.join(os.path.dirname(__file__), "test_files")
# Ensure this path is correct based on how tests are discovered and run.
# If `test_document_converter.py` already ensures these files exist, no need to recreate.

@pytest.mark.asyncio
async def test_process_document_success_txt(client: AsyncClient):
    """Test successful processing of a TXT file."""
    dummy_txt_path = os.path.join(TEST_FILES_DIR, "dummy.txt")
    assert os.path.exists(dummy_txt_path), f"Dummy TXT file not found at {dummy_txt_path}. Ensure test_document_converter.py setup ran or files are present."

    with open(dummy_txt_path, "rb") as f:
        response = await client.post(
            "/process_document/",
            files={"file": (os.path.basename(dummy_txt_path), f, "text/plain")}
        )
    assert response.status_code == 200
    data = response.json()
    assert data["document"] == os.path.basename(dummy_txt_path)
    assert "extracts" in data
    assert len(data["extracts"]) > 0
    assert "text" in data["extracts"][0]
    # Further checks on content can be added if specific output is expected

@pytest.mark.asyncio
async def test_process_document_success_pdf(client: AsyncClient):
    """Test successful processing of a PDF file."""
    dummy_pdf_path = os.path.join(TEST_FILES_DIR, "dummy.pdf")
    assert os.path.exists(dummy_pdf_path), f"Dummy PDF file not found at {dummy_pdf_path}."

    with open(dummy_pdf_path, "rb") as f:
        response = await client.post(
            "/process_document/",
            files={"file": (os.path.basename(dummy_pdf_path), f, "application/pdf")}
        )
    assert response.status_code == 200
    data = response.json()
    assert data["document"] == os.path.basename(dummy_pdf_path)
    assert "extracts" in data
    assert len(data["extracts"]) > 0

@pytest.mark.asyncio
async def test_process_document_success_docx(client: AsyncClient):
    """Test successful processing of a DOCX file."""
    dummy_docx_path = os.path.join(TEST_FILES_DIR, "dummy.docx")
    assert os.path.exists(dummy_docx_path), f"Dummy DOCX file not found at {dummy_docx_path}."

    with open(dummy_docx_path, "rb") as f:
        response = await client.post(
            "/process_document/",
            files={"file": (os.path.basename(dummy_docx_path), f, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
        )
    assert response.status_code == 200
    data = response.json()
    assert data["document"] == os.path.basename(dummy_docx_path)
    assert "extracts" in data
    assert len(data["extracts"]) > 0


@pytest.mark.asyncio
async def test_process_document_unsupported_type(client: AsyncClient):
    """Test processing an unsupported file type."""
    # Create a dummy file with an unsupported extension (e.g., .png).
    # No need to save it, just pass bytes.
    response = await client.post(
        "/process_document/",
        files={"file": ("dummy.png", b"fake png content", "image/png")}
    )
    # The API checks extension first, before content type sometimes.
    # The check `if file_extension not in ALLOWED_EXTENSIONS:` in main.py raises HTTPException(400)
    assert response.status_code == 400
    json_response = response.json()
    assert "Invalid file type" in json_response["detail"]
    assert ".png" in json_response["detail"]

@pytest.mark.asyncio
async def test_process_document_too_large(client: AsyncClient):
    """Test processing a file that is too large."""
    MAX_FILE_SIZE = 5 * 1024 * 1024  # As defined in main.py
    # Create content that is slightly larger than MAX_FILE_SIZE
    # To reliably test the file.size check, we need to mock UploadFile.size or send a real large file.
    # Sending actual large content is inefficient for unit tests.
    # For now, this test assumes that if a file object with `size` attribute is passed, it's checked.
    # HTTpx's files parameter might not perfectly simulate Starlette's UploadFile.size attribute without more complex setup.
    # A more direct way to test this logic might be a unit test on the endpoint function itself with a mocked UploadFile.
    # However, let's try sending oversized content and see if the default test client behavior triggers it.

    # This test might be slow or consume memory if httpx actually tries to send all this data.
    # A better approach for unit testing this specific feature would be to mock the `UploadFile` object
    # and set its `size` attribute directly.
    # Given the tools, we will attempt a direct send.

    oversized_content = b"a" * (MAX_FILE_SIZE + 1)

    response = await client.post(
        "/process_document/",
        files={"file": ("large_file.txt", oversized_content, "text/plain")}
    )
    assert response.status_code == 413
    json_response = response.json()
    assert "File too large" in json_response["detail"]
