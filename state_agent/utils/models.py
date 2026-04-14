from pydantic import BaseModel, Field, ConfigDict
from typing import Dict, Optional, List

class DatasetEntry(BaseModel):
    """Individual dataset record metadata."""
    # Required fields
    iid: str = Field(description="Internal unique identifier for the dataset record.")
    url: str = Field(description="Dataset source URL.")
    potential_urls: str = Field(description="Other potential URLs for the dataset download.")
    # Optional fields (placeholders)
    title: Optional[str] = Field(default=None, description="Dataset title.")
    description: Optional[str] = Field(default=None, description="Dataset extensive description.")
    repository: Optional[str] = Field(default=None, description="Dataset repository or platform (kaggle, github, etc.).")
    authors: Optional[str] = Field(default=None, description="Dataset authors")
    email: Optional[str] = Field(default=None, description="Dataset potential point of contact for further explanation")
    task: Optional[str] = Field(default=None, description="Primary task the dataset is suited for (segmentation, classification, etc.).")
    annotation_type: Optional[str] = Field(default=None, description="Type of annotation provided.")
    number_images: Optional[int] = Field(default=0, description="Number of images in dataset.")
    dimensions: Optional[str] = Field(default=None, description="Image dimensions or resolution format.")

    # Optional fields using the Optional keyword
    source: Optional[str] = Field(default=None, description="Dataset source platform or origin.")
    
    # Using alias so LLM can provide 'license' and we map it to 'license_'
    license_: Optional[str] = Field(
        default=None, 
        alias="license", 
        description="Dataset license."
    )
    
    # Contact Information
    point_of_contact: Optional[str] = Field(default=None, description="Name of the person or organization to contact for this dataset.")
    contact_email: Optional[str] = Field(default=None, description="Email address for contact regarding this dataset.")

    # Download tracking
    download_status: Optional[str] = Field(default="pending", description="Status of the download (pending, success, failed, not_applicable)")
    downloader_type: Optional[str] = Field(default=None, description="The downloader used (kaggle, github, etc.)")
    downloader_id: Optional[str] = Field(default=None, description="The identifier used for the downloader")
    local_path: Optional[str] = Field(default=None, description="Local path to the downloaded data")
    confidence: Optional[float] = Field(default=0.0, description="Confidence score from classification (0 to 1)")
    rescrape_count: int = Field(default=0, description="Number of times this website has been rescraped")

    # This allows the model to be created using 'license' or 'license_'
    model_config = ConfigDict(populate_by_name=True)

class SourceClassification(BaseModel):
    """Classification of a source for programmatic download."""
    url: str = Field(description="The source URL.")
    potential_urls: str = Field(description="Other potential URLs for the dataset download.")
    source_type: str = Field(description="One of: kaggle, github, huggingface, direct_link, none")
    identifier: str = Field(description="The handle or URL needed for the downloader (e.g. 'user/dataset' for kaggle)")
    confidence: float = Field(description="Confidence score from 0 to 1.")
    reasoning: str = Field(description="Brief reasoning for this classification.")

class SourceClassificationOutput(BaseModel):
    """Batch of source classifications."""
    classifications: List[SourceClassification]

class DatasetDiscoveryOutput(BaseModel):
    """Batch of dataset metadata entries indexed by unique identifier."""
    entries: Dict[str, DatasetEntry] = Field(
        description="Dictionary of dataset records keyed by iid."
    )
