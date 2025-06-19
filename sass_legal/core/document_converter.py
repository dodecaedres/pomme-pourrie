import os
from PyPDF2 import PdfReader
from PyPDF2.errors import PdfReadError # Import specific PyPDF2 error
import docx
from docx.opc.exceptions import PackageNotFoundError # Import specific python-docx error

# Logger setup
from sass_legal.core.logger import get_logger
# Custom Errors
from .errors import DocumentProcessingError, UnsupportedFileTypeError

converter_logger = get_logger(__name__)


def convert_to_markdown(file_path: str) -> str:
    """
    Converts a document file (PDF, DOCX, TXT) to Markdown plain text.

    This function identifies the file type based on its extension and routes it
    to the appropriate conversion helper (_convert_pdf_to_markdown,
    _convert_docx_to_markdown, or _convert_txt_to_markdown).

    Args:
        file_path: The absolute or relative path to the document file.

    Returns:
        A string containing the Markdown representation of the document.

    Raises:
        FileNotFoundError: If the `file_path` does not exist.
        UnsupportedFileTypeError: If the file extension is not .pdf, .docx, or .txt.
        DocumentProcessingError: If any error occurs during the conversion process
                                 that is not a FileNotFoundError or UnsupportedFileTypeError.
    """
    if not os.path.exists(file_path):
        converter_logger.error(f"File not found for conversion: {file_path}")
        # This is a FileNotFoundError, which is a system error, not a client error.
        # It might be better to let this propagate or wrap in a generic DocumentProcessingError
        # if it's an intermediate step that should have been guaranteed by the caller.
        raise FileNotFoundError(f"File not found: {file_path}")

    file_ext = os.path.splitext(file_path)[1].lower()
    filename = os.path.basename(file_path)

    converter_logger.info(f"Attempting to convert file: {filename} (type: {file_ext})")

    if file_ext == ".pdf":
        return _convert_pdf_to_markdown(file_path)
    elif file_ext == ".docx":
        return _convert_docx_to_markdown(file_path)
    elif file_ext == ".txt":
        return _convert_txt_to_markdown(file_path)
    else:
        converter_logger.warning(f"Unsupported file format for conversion: {file_ext} for file {filename}")
        raise UnsupportedFileTypeError(f"Unsupported file format: {file_ext}. Cannot process file '{filename}'.")

def _convert_pdf_to_markdown(file_path: str) -> str:
    """
    Converts a PDF file to Markdown text using PyPDF2.

    Extracts text from each page of the PDF and concatenates it.
    Page contents are separated by two newlines.

    Args:
        file_path: Path to the PDF file.

    Returns:
        Markdown string representation of the PDF content.

    Raises:
        DocumentProcessingError: If an error occurs during PDF parsing or text extraction.
    """
    try:
        converter_logger.debug(f"Converting PDF: {file_path}")
        reader = PdfReader(file_path)
        markdown_content = ""
        for page_num in range(len(reader.pages)):
            page = reader.pages[page_num]
            text = page.extract_text()
            if text:
                 markdown_content += text
                 markdown_content += "\n\n"
        converter_logger.info(f"Successfully converted PDF: {os.path.basename(file_path)}")
        return markdown_content
    except PdfReadError as e: # Catch specific PDF reading errors
        converter_logger.error(f"PyPDF2 PdfReadError for {os.path.basename(file_path)}: {str(e)}", exc_info=True)
        raise DocumentProcessingError(f"Invalid or corrupted PDF file: '{os.path.basename(file_path)}'. {str(e)}") from e
    except Exception as e: # Generic catch for other unexpected issues from PyPDF2 or elsewhere
        converter_logger.error(f"Unexpected error converting PDF {os.path.basename(file_path)}: {str(e)}", exc_info=True)
        raise DocumentProcessingError(f"Unexpected error converting PDF '{os.path.basename(file_path)}': {str(e)}") from e

def _convert_docx_to_markdown(file_path: str) -> str:
    """
    Converts a DOCX file to Markdown text using python-docx.

    Extracts text from each paragraph in the DOCX document and concatenates it.
    Paragraphs are separated by two newlines.

    Args:
        file_path: Path to the DOCX file.

    Returns:
        Markdown string representation of the DOCX content.

    Raises:
        DocumentProcessingError: If an error occurs during DOCX parsing or text extraction.
    """
    try:
        converter_logger.debug(f"Converting DOCX: {file_path}")
        doc = docx.Document(file_path)
        markdown_content = ""
        for para in doc.paragraphs:
            markdown_content += para.text
            markdown_content += "\n\n"
        converter_logger.info(f"Successfully converted DOCX: {os.path.basename(file_path)}")
        return markdown_content
    except PackageNotFoundError as e: # Catch if not a valid DOCX (zip) package
        converter_logger.error(f"python-docx PackageNotFoundError for {os.path.basename(file_path)}: {str(e)}", exc_info=True)
        raise DocumentProcessingError(f"File is not a valid DOCX format: '{os.path.basename(file_path)}'. {str(e)}") from e
    except Exception as e: # Generic catch for other unexpected issues from python-docx
        converter_logger.error(f"Unexpected error converting DOCX {os.path.basename(file_path)}: {str(e)}", exc_info=True)
        raise DocumentProcessingError(f"Unexpected error converting DOCX '{os.path.basename(file_path)}': {str(e)}") from e

def _convert_txt_to_markdown(file_path: str) -> str:
    """
    Converts a TXT file to Markdown text (essentially reads its content).

    Reads the content of the text file. Since TXT is already plain text,
    no structural conversion to Markdown is performed beyond returning the content.

    Args:
        file_path: Path to the TXT file.

    Returns:
        String content of the TXT file.

    Raises:
        DocumentProcessingError: If an error occurs during file reading.
    """
    try:
        converter_logger.debug(f"Converting TXT: {file_path}")
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        converter_logger.info(f"Successfully converted TXT: {os.path.basename(file_path)}")
        return content
    except Exception as e:
        converter_logger.error(f"Error converting TXT {os.path.basename(file_path)}: {str(e)}", exc_info=True)
        raise DocumentProcessingError(f"Error converting TXT '{os.path.basename(file_path)}': {str(e)}") from e
