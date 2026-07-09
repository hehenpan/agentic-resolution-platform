from pydantic import BaseModel, Field

class FileDownloadRequest(BaseModel):
    file_id: int = Field(..., description="The ID of the file to download")
