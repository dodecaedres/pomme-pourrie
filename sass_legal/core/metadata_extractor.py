import spacy
import re

# Logger setup
from sass_legal.core.logger import get_logger
# Custom Errors
from .errors import MetadataExtractionError, ConfigurationError

extractor_logger = get_logger(__name__)

# Load the French NLP model
nlp = None # Initialize nlp to None
try:
    nlp = spacy.load("fr_core_news_sm")
    extractor_logger.info("spaCy French model 'fr_core_news_sm' loaded successfully.")
except OSError as e:
    error_message = (
        "Failed to load spaCy model 'fr_core_news_sm'. "
        "Please ensure it is downloaded (e.g., python -m spacy download fr_core_news_sm). "
        f"Original error: {e}"
    )
    extractor_logger.critical(error_message) # Use critical for startup failures
    raise ConfigurationError(error_message) from e


def extract_metadata_from_text(text_content: str) -> dict:
    """
    Extracts structured metadata from a given text content.

    This function utilizes spaCy for Named Entity Recognition (NER) to identify
    persons and organizations. Date extraction via spaCy's 'fr_core_news_sm' model
    has proven unreliable and is currently very limited; this function will likely
    return an empty list for dates. Future improvements might involve custom date
    regex or a more robust date parsing library if precise date extraction is critical.

    It also employs custom regular expressions via the `_extract_law_articles`
    helper function to find references to law articles.

    The quality of NER for persons and organizations depends on the training data
    and capabilities of the `fr_core_news_sm` model and may not be exhaustive or
    perfectly accurate for all legal or domain-specific texts.

    If the spaCy model (`fr_core_news_sm`) is not loaded (e.g., due to download issues),
    this function returns a dictionary with empty lists for metadata fields and an
    error message.

    Args:
        text_content: The input string from which to extract metadata.

    Returns:
        A dictionary containing the extracted metadata:
        - "dates" (List[str]): Extracted date mentions. Currently limited by spaCy model performance.
        - "persons" (List[str]): Extracted person names.
        - "organizations" (List[str]): Extracted organization names.
        - "law_articles" (List[str]): Extracted law article references.
        - "error" (str, optional): An error message if the spaCy model failed to load.
    """
    if nlp is None:
        # This case should ideally be prevented by raising ConfigurationError at load time
        # if the model is absolutely critical.
        # However, if we reach here, it means nlp was not loaded successfully.
        extractor_logger.critical("CRITICAL: spaCy model 'fr_core_news_sm' is not available. Metadata extraction will be incomplete.")
        return {
            "dates": [],
            "persons": [],
            "organizations": [],
            "law_articles": [],
            "error": "spaCy model 'fr_core_news_sm' not available. Please check application logs and ensure model is downloaded."
        }

    text_snippet_for_log = text_content[:100] + "..." if len(text_content) > 100 else text_content
    extractor_logger.info(f"Starting metadata extraction from text snippet: '{text_snippet_for_log}'")

    doc = nlp(text_content)

    metadata = {
        "dates": [],
        "persons": [],
        "organizations": [],
        "law_articles": []
    }

    for ent in doc.ents:
        if ent.label_ == "DATE":
            metadata["dates"].append(ent.text)
        elif ent.label_ == "PER":
            metadata["persons"].append(ent.text)
        elif ent.label_ == "ORG":
            metadata["organizations"].append(ent.text)

    extractor_logger.debug(f"spaCy NER found: Dates: {len(metadata['dates'])}, Persons: {len(metadata['persons'])}, Orgs: {len(metadata['organizations'])}")

    # Extract law articles using regular expressions
    try:
        metadata["law_articles"] = _extract_law_articles(text_content)
        extractor_logger.debug(f"Regex extraction found {len(metadata['law_articles'])} law articles.")
    except Exception as e:
        extractor_logger.error("Error during regex extraction of law articles", exc_info=True)
        # Instead of returning empty list, wrap in custom error if it's critical
        # For now, keeping it as empty list + logged error is non-fatal for this part.
        # If this part were critical to proceed, we'd raise MetadataExtractionError(f"Failed to extract law articles: {e}")
        metadata["law_articles"] = []

    # Remove duplicates
    for key in metadata:
        metadata[key] = sorted(list(set(metadata[key])))

    return metadata

def _extract_law_articles(text_content):
    """
    Extracts law article references from text content using a series of regular expressions.

    The function iterates through predefined regex patterns designed to capture various
    formats of legal references (e.g., "article L. 123-45", "loi n° X", "articles 1 et 2").
    It processes matches to extract the core article identifiers and cleans them up.
    If multiple articles are cited in a single phrase (e.g., "articles 1 et 2"),
    it attempts to split them into individual references.

    Args:
        text_content: The text from which to extract law articles.

    Returns:
        A sorted list of unique strings, each representing a found law article reference.
        Returns an empty list if no references are found or if an error occurs during processing.

    Raises:
        Does not directly raise exceptions for regex processing errors but logs them
        and may return partial results. Consider raising MetadataExtractionError for critical failures.
    """
    # Regex patterns for extracting law articles.
    # Each pattern is designed to capture common ways laws/articles are cited in French legal texts.
    # (?:\b\w+\s+)? : Optional non-capturing group for leading words like "Voir", "Selon", "Les" etc.
    # [Ll]['’\s]article[s]? : Matches "l'article", "L'article", "article", "articles" (case variation handled by re.IGNORECASE).
    # \s+ : Matches one or more spaces.
    # ((?:[A-Z]\.\s*)?[\w\d]+(?:-[\w\d]+)*) : This is the main capture group for article numbers.
    #   (?:[A-Z]\.\s*)? : Optional non-capturing group for prefixes like "L. ", "R. ".
    #   [\w\d]+ : Matches the main article number (alphanumeric, e.g., "123", "L123", "4bis").
    #   (?:-[\w\d]+)* : Optional non-capturing group for suffixes like "-1", "-A".

    # Pattern for lists of articles, e.g., "articles 1, 2 et 3" or "Les articles L1 et L2"
    # (?i) flag makes this specific pattern case-insensitive.
    list_articles_pattern_str = r"(?i)(?:\b\w+\s+)?articles\s+([\w\d,\s]+(?:et\s+[\w\d]+)?)"

    patterns = [
        # Matches single articles like "l'article L.123-45", "article R123-1", "Article 42", "article 7bis"
        # It can be preceded by optional words (e.g., "voir l'article...").
        r"(?:\b\w+\s+)?[Ll]['’\s]article[s]?\s+((?:[A-Z]\.\s*)?[\w\d]+(?:-[\w\d]+)*)",
        # Same as above, but without the "l'" or "L'" prefix, for "article 123".
        r"(?:\b\w+\s+)?article[s]?\s+((?:[A-Z]\.\s*)?[\w\d]+(?:-[\w\d]+)*)",

        # Matches specific legal terms like "loi n° XXXX-YYYY"
        r"(loi\s+n°\s*[\d-]+)",
        # Matches "décret n° XXXX-YYYY"
        r"(décret\s+n°\s*[\d-]+)",

        # Dedicated pattern for handling lists like "articles 1 et 2", "articles L1, L2 et L3"
        list_articles_pattern_str,

        # Matches references to codes like "code de l'environnement" or "Code civil"
        # These are broader and might need refinement if too much noise is captured.
        r"(code\s+de\s+l['’\s][\w\s]+)",
        r"(Code\s+[\w\s]+)"
    ]

    found_articles_parts = []
    try:
        for pattern_str in patterns:
            # Apply re.IGNORECASE to all patterns for consistency, unless (?i) is in pattern_str itself
            flags = re.IGNORECASE if not pattern_str.startswith("(?i)") else 0
            for match in re.finditer(pattern_str, text_content, flags=flags):
                captured_text = None
                if len(match.groups()) > 0: # Ensure there's at least one capture group
                    captured_text = match.group(1).strip() # We assume relevant part is in group 1
                else: # Should not happen with current patterns as all have a capture group
                    # This case should ideally not be reached if patterns are well-defined
                    extractor_logger.warning(f"Pattern '{pattern_str}' matched but produced no capture groups for text segment.")
                    continue

                if not captured_text: # Should be redundant if previous continue is hit (already handled by previous continue)
                    continue

                # Special processing for the list_articles_pattern
                if pattern_str == list_articles_pattern_str:
                    # captured_text will be like "1, 2 et 3" or "10 et 11" or "L1, L2 et L3"
                    # Extract individual article numbers/codes
                    individual_articles = re.findall(r'[\w\d]+', captured_text) # Find all alphanumeric sequences
                    for art_num_candidate in individual_articles:
                        # Filter out common words that are not articles if they appear alone
                        if art_num_candidate.lower() not in ["et", "articles", "les", "l", "sont", "des", "est", "important", "importants"]:
                            found_articles_parts.append(art_num_candidate)
                else:
                    found_articles_parts.append(captured_text)
    except Exception as e:
        extractor_logger.error(f"Error during regex pattern processing in _extract_law_articles: {str(e)}", exc_info=True)
        # Depending on desired behavior, either return partially processed articles or raise.
        # For now, we'll return what we have and log the error. If it's critical, raise MetadataExtractionError.
        # raise MetadataExtractionError(f"Regex processing failed: {e}") from e

    # Remove duplicates and sort
    unique_articles = sorted(list(set(filter(None, found_articles_parts))))
    return unique_articles

if __name__ == '__main__':
    # This setup is for direct script execution testing.
    # It might be good to use a basic console logger here if settings/JSON logger isn't fully set up
    # or if this script is run before .env is processed by an app.
    # For now, the get_logger will use its defaults or .env if present.

    # Example Usage (optional - for testing)
    # Ensure LOG_LEVEL is set to DEBUG in .env or settings for verbose output here
    main_logger = get_logger("metadata_extractor_main_test")
    main_logger.info("Running metadata_extractor.py directly for testing...")

    sample_texts_for_testing = {
        "French Example": """
        Le présent document a été signé le 15 janvier 2023 par Jean Dupont de la société ACME Corp.
        Conformément à l'article L. 123-45 du Code du Travail et la loi n°2004-575.
        L'article R. 111-1 et l'article R. 111-2 sont aussi applicables.
        Voir aussi le décret n° 2000-123. Le Code de commerce est important. Et les articles 10 et 11.
        Signé par Marie Curie pour Générale Électrique. La date limite est le 31 décembre 2024.
        """,
        "No Law Example": "Ceci est un texte simple sans référence légale, signé par Personne Lambda le 1er avril 2025.",
        "Edge Case Law Articles": "L'article 1, l'article 2, et l'article L3. Article 4b et Article 5 C. Article L.123-1 du code de l'urbanisme. Article L. 123-4-5. l'article R*123-1 est invalide.",
        "Multiple Articles": "Voir articles 1 et 2 du code X, et aussi l'article L. 55-1 ainsi que les articles A100 à A102."
    }

    if nlp:
        for name, text in sample_texts_for_testing.items():
            main_logger.info(f"--- {name} ---")
            metadata = extract_metadata_from_text(text)
            main_logger.info(f"Texte: {text[:100]}...")
            main_logger.info(f"Métadonnées: {metadata}\n")
    else:
        main_logger.warning("spaCy nlp model not loaded, skipping direct execution tests.")

    # Test what happens if the model is not loaded (by setting nlp to None temporarily if needed for specific test)
    # current_nlp = nlp
    # nlp = None
    # metadata_error = extract_metadata_from_text("Some text")
    # main_logger.info(f"Error case (nlp=None): {metadata_error}")
    # nlp = current_nlp # Restore
