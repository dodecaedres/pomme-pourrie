from pydantic import BaseModel, Field
from typing import List, Optional

class ProcessedExtractItem(BaseModel):
    """
    Represents a single processed extract from a document, including relevant laws and advice.
    """
    text: str = Field(..., description="The extracted text snippet from the document.")
    lois_citées: List[str] = Field(default_factory=list, description="List of law articles or legal texts cited in or relevant to the extract.")
    conseil: str = Field(..., description="Placeholder for legal advice related to the extract. Requires human validation.")

    class Config:
        json_schema_extra = {
            "example": {
                "text": "Mon employeur m'a menacé de licenciement...",
                "lois_citées": ["Article L1152-1 Code du travail"],
                "conseil": "Conservez tout écrit. Saisir Prud'hommes sous 2 ans."
            }
        }

class DocumentProcessResponse(BaseModel):
    """
    Response model for the document processing endpoint.
    Contains metadata and processed extracts from the uploaded document.
    """
    document: str = Field(..., description="The name of the processed document file.")
    tags: List[str] = Field(default_factory=list, description="A list of tags or keywords derived from the document's content (e.g., main legal themes, entities).")
    extracts: List[ProcessedExtractItem] = Field(..., description="A list of processed extracts from the document, each with text, cited laws, and advice.")

    class Config:
        json_schema_extra = {
            "example": {
                "document": "plainte_employeur.docx",
                "tags": ["Droit du travail", "Harcèlement moral"],
                "extracts": [
                    {
                        "text": "Mon employeur m'a menacé de licenciement pour avoir refusé des tâches non prévues à mon contrat.",
                        "lois_citées": ["Article L1222-1 Code du travail", "Article L1152-2 Code du travail"],
                        "conseil": "Documentez précisément les menaces et les refus. Consultez un représentant du personnel ou un avocat spécialisé."
                    }
                ]
            }
        }
