from typing import List

from pydantic import BaseModel, Field

from app.schemas.common import ResponseBase


class FileDownloadRequest(BaseModel):
    file_id: int = Field(..., description="The ID of the file to download")


class FileItemResponse(BaseModel):
    file_id: int = Field(description="Unique file ID.")
    file_name: str = Field(description="Original uploaded file name.")
    file_size: int = Field(description="File size in bytes.")
    file_type: str = Field(description="Detected or declared file type.")
    file_md5_hash: str = Field(description="MD5 hash of the uploaded file content.")
    owner_user_id: int = Field(description="User ID of the file owner.")
    owner_email: str = Field(description="Email address of the file owner.")
    create_ts: int = Field(description="Unix timestamp when the file was created.")
    status: int = Field(description="File lifecycle status code.")
    vector_db_sync_status: int = Field(
        description="Vector database synchronization status code."
    )


class FileListResponseData(BaseModel):
    items: List[FileItemResponse] = Field(
        description="Files returned for the current page."
    )
    last_cursor: str = Field(
        ...,
        description=(
            "Cursor for fetching the next page, formatted as "
            "{last_create_ts}_{last_file_id}. Empty if no more items."
        ),
    )


class FileListResponse(ResponseBase):
    data: FileListResponseData = Field(
        description="Paginated file list response payload."
    )
