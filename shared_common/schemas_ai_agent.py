from pydantic import BaseModel, Field
from typing import Dict, Any, Optional

class RAGFileImportPayload(BaseModel):
    file_id: int = Field(..., description="Unique file ID")
    file_name: str = Field(..., description="Name of the file")
    file_size: int = Field(..., description="Size of the file in bytes")
    file_owner_id: int = Field(..., description="file owner user id")
    file_tenant_id: int = Field(..., description="file tenant id")
    file_content: bytes = Field(..., description="File content")
    extra_meta: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata context")
    extra_context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="context data")


