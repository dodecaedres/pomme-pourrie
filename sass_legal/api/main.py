import os
import tempfile
from fastapi import FastAPI, File, UploadFile, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from typing import List, Set

# Rate Limiting
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Core services
from sass_legal.core.document_converter import convert_to_markdown
from sass_legal.core.metadata_extractor import extract_metadata_from_text
# Pydantic Models
from sass_legal.core.models import DocumentProcessResponse, ProcessedExtractItem
# Configuration
from sass_legal.core.config import settings
# Logger
from sass_legal.core.logger import get_logger
# Custom Errors
from sass_legal.core.errors import SassLegalError, DocumentProcessingError, UnsupportedFileTypeError, MetadataExtractionError

api_logger = get_logger(__name__) # or get_logger("sass_legal.api")

# Rate Limiter setup
limiter = Limiter(key_func=get_remote_address, default_limits=["1000/minute"]) # Default for non-decorated routes
app = FastAPI(title=settings.APP_NAME, debug=settings.DEBUG)
app.state.limiter = limiter # Make limiter accessible to endpoint decorators
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler) # Handle RateLimitExceeded globally


# Security Headers Middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next: callable) -> Response:
    """
    Middleware to add common security headers to all HTTP responses.
    These headers help protect against some common web vulnerabilities.
    """
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    # Content-Security-Policy is powerful but requires careful configuration based on specific needs.
    # Example: response.headers["Content-Security-Policy"] = "default-src 'self'; img-src *; media-src media1.com media2.com; script-src userscripts.example.com"
    return response


# Exception Handlers
@app.exception_handler(SassLegalError)
async def sass_legal_exception_handler(request: Request, exc: SassLegalError) -> JSONResponse:
    """
    Global exception handler for custom `SassLegalError` types.
    Maps custom exceptions to appropriate HTTP status codes and formats
    the error response as JSON.
    """
    error_code = exc.__class__.__name__
    status_code = 400 # Default for SassLegalError

    if isinstance(exc, UnsupportedFileTypeError):
        status_code = 415 # Unsupported Media Type for incorrect file types
    elif isinstance(exc, DocumentProcessingError):
        status_code = 422 # Unprocessable Entity, e.g., if a DOCX is corrupt
    elif isinstance(exc, MetadataExtractionError):
        status_code = 422 # Unprocessable Entity, e.g., if text is unparsable for metadata

    api_logger.error(
        f"SassLegalError caught: {error_code} - {str(exc)} for request {request.method} {request.url.path}",
        exc_info=False # Set to True if stack trace is desired here, though core modules might have logged it already
    )
    return JSONResponse(
        status_code=status_code,
        content={"error_code": error_code, "detail": str(exc)},
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Global exception handler for any unhandled exceptions.
    Logs critical errors and returns a generic 500 Internal Server Error response.
    """
    api_logger.critical(
        f"Unhandled generic exception: {str(exc)} for request {request.method} {request.url.path}",
        exc_info=True # Always include stack trace for unexpected errors
    )
    return JSONResponse(
        status_code=500,
        content={"error_code": "INTERNAL_SERVER_ERROR", "detail": "An unexpected internal server error occurred."},
    )

# Example usage: uvicorn sass_legal.api.main:app --reload
# Note: API_PREFIX from settings would typically be used with an APIRouter:
# router = APIRouter(prefix=settings.API_PREFIX)
# And then app.include_router(router)
# For simplicity here, we are not using APIRouter for the root and one endpoint.

@app.get("/", summary="Root Endpoint", description="Returns a welcome message for the Sass Legal API, including application name and debug status.")
async def root():
    """
    Root endpoint for the Sass Legal API.
    Provides a welcome message and basic application status.
    """
    api_logger.info("Root endpoint accessed.")
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "debug_mode": settings.DEBUG,
        "api_prefix_configured": settings.API_PREFIX # Just showing it's available
    }

@limiter.limit("10/minute")
@app.post(
    "/process_document/",
    response_model=DocumentProcessResponse,
    summary="Process a Legal Document",
    description="Upload a document (PDF, DOCX, or TXT) to convert it to Markdown, extract metadata (like cited laws, persons, organizations), and receive a structured JSON response with a text snippet, extracted laws, and a placeholder for legal advice. Max file size: 5MB."
)
async def process_document(
    request: Request,
    file: UploadFile = File(..., description="The document file to process (PDF, DOCX, TXT). Max 5MB.")
):
    """
    Processes an uploaded legal document:
    - Validates file type (PDF, DOCX, TXT) and size (max 5MB).
    - Converts the document content to Markdown.
    - Extracts metadata: persons, organizations, and cited law articles.
    - Returns a structured response including a text snippet, extracted laws, and a placeholder for advice.
    """
    filename = file.filename
    api_logger.info(f"Processing document upload request for: {filename} (Content-Type: {file.content_type})")

    # File Upload Restrictions
    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
    ALLOWED_EXTENSIONS: Set[str] = {".txt", ".pdf", ".docx"}

    file_extension = os.path.splitext(filename)[1].lower()
    if file_extension not in ALLOWED_EXTENSIONS:
        api_logger.warning(f"Upload attempt with invalid file type: {filename} (type: {file_extension})")
        # This HTTPException will be caught by FastAPI's default handler for it,
        # or could be a custom error if preferred for consistent JSON from our handlers
        raise HTTPException(status_code=400, detail=f"Invalid file type: {file_extension}. Allowed types are {ALLOWED_EXTENSIONS}.")

    # Check file size using file.size (provided by Starlette's UploadFile)
    # This check happens before reading the entire file into memory for processing.
    if file.size > MAX_FILE_SIZE:
        api_logger.warning(f"Upload attempt with too large file: {filename} (size: {file.size} bytes)")
        raise HTTPException(status_code=413, detail=f"File too large. Max size is {MAX_FILE_SIZE // (1024*1024)}MB.")

    tmp_file_path = None
    try:
        # Save UploadFile to a temporary file to pass its path to converters
        # Content has been implicitly checked for size by Starlette if file.size was accurate,
        # or by the explicit check above. Now we read it for saving.
        file_content = await file.read()

        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as tmp_file:
            tmp_file.write(file_content)
            tmp_file_path = tmp_file.name

        api_logger.debug(f"Temporary file created for {filename} at {tmp_file_path}")

        # Document conversion can raise DocumentProcessingError (incl. UnsupportedFileTypeError) or FileNotFoundError
        markdown_text = convert_to_markdown(tmp_file_path)

        # Metadata extraction can raise MetadataExtractionError (though currently it logs and returns partial)
        metadata = extract_metadata_from_text(markdown_text)

        tags = list(set(metadata.get("persons", []) + metadata.get("organizations", [])))[:5]
        text_snippet = markdown_text[:200] + "..." if len(markdown_text) > 200 else markdown_text

        extract_item = ProcessedExtractItem(
            text=text_snippet,
            lois_citées=metadata.get("law_articles", []),
            conseil="Placeholder conseil - Ce conseil est généré automatiquement et nécessite une validation humaine."
        )

        response_data = DocumentProcessResponse(
            document=filename,
            tags=tags,
            extracts=[extract_item]
        )

        api_logger.info(f"Successfully processed document: {filename}")
        return response_data

    # Custom SassLegalErrors will be caught by sass_legal_exception_handler.
    # Built-in errors like FileNotFoundError or any other unexpected Exception
    # will be caught by generic_exception_handler.
    # The main purpose of this try block now is for the 'finally' cleanup.
    # No need to catch HTTPException here as we are not raising them directly from this block anymore.

    finally:
        # Final cleanup attempt for the temporary file
        if tmp_file_path and os.path.exists(tmp_file_path):
            api_logger.debug(f"Cleaning up temporary file: {tmp_file_path}")
            os.unlink(tmp_file_path)


if __name__ == "__main__":
    # This block is for local debugging if you run `python main.py`
    # However, FastAPI apps are typically run with Uvicorn as per the comment above.
    # The logger configured via get_logger() will output JSON to console.
    # To see DEBUG logs from this file or others, set LOG_LEVEL=DEBUG in .env
    import uvicorn
    api_logger.info("Starting FastAPI app with Uvicorn for local debugging via __main__.")
    # No need for print() here as logger will show messages if level is appropriate
    uvicorn.run(app, host="127.0.0.1", port=8000)
