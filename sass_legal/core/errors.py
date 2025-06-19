class SassLegalError(Exception):
    """Base class for custom exceptions in the Sass Legal application.

    Provides a common type for catching application-specific errors.
    """
    pass

class DocumentProcessingError(SassLegalError):
    """Raised when an error occurs during document handling or conversion.

    This could be due to issues with file parsing, content extraction, or
    transformation processes.
    """
    pass

class UnsupportedFileTypeError(DocumentProcessingError):
    """Raised when a file type is not supported for processing.

    Inherits from DocumentProcessingError, as it's a specific type of
    document processing failure.
    """
    pass

class MetadataExtractionError(SassLegalError):
    """Raised when an error occurs during the metadata extraction phase.

    This can include issues with Named Entity Recognition (NER), regex processing,
    or other steps involved in identifying relevant metadata from text.
    """
    pass

class ConfigurationError(SassLegalError):
    """Raised when there is an error related to application configuration.

    Examples include missing environment variables, invalid configuration values,
    or issues loading configuration files.
    """
    pass
