from pydantic import BaseModel, Field
from typing import List
from app.schemas.common import ResponseBase

class FileDownloadRequest(BaseModel):
    file_id: int = Field(..., description="The ID of the file to download")

class FileItemResponse(BaseModel):
    file_id: int
    file_name: str
    file_size: int
    file_type: str
    file_md5_hash: str
    owner_user_id: int
    owner_email: str
    create_ts: int
    status: int
    vector_db_sync_status: int

class FileListResponseData(BaseModel):
    items: List[FileItemResponse]
    last_cursor: str = Field(..., description="The cursor for fetching the next page, formatted as {last_create_ts}_{last_file_id}. Empty if no more items.")

class FileListResponse(ResponseBase):
    data: FileListResponseData

