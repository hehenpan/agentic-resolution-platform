from fastapi import APIRouter, status, Depends, HTTPException, UploadFile, File
from app.api.deps import get_current_user, get_file_service
from app.models.models import User
from app.services.file_service import FileService
from app.schemas.common import ResponseBase, BizCode
from utils.commons import get_bytes_md5

file_router = APIRouter()

@file_router.post("/files/upload", response_model=ResponseBase, status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    file_service: FileService = Depends(get_file_service)
):
    """
    Upload a file:
    1. Creates a database index with status=INVALID (0).
    2. Writes the file raw data to local disk.
    3. Activates the index by updating status to ACTIVE (1).
    """
    try:
        content = await file.read()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to read upload file: {str(e)}"
        )

    file_size = len(content)
    md5_hash = get_bytes_md5(content)

    # Step 1: Create file index (initially INVALID)
    try:
        file_info = file_service.create_file_index(
            tenant_id=current_user.tenant_id,
            owner_user_id=current_user.user_id,
            owner_email=current_user.email,
            filename=file.filename or "unnamed_file",
            file_size=file_size,
            file_md5_hash=md5_hash
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create file index: {str(e)}"
        )


    # Step 2 & 3: Store raw data and activate index
    try:
        # Write content to local storage
        file_service.store_file_content(
            file_info=file_info,
            content=content
        )


        # Activate file index (status=ACTIVE)
        file_info = file_service.activate_file_index(file_info.file_id)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file content or activate index: {str(e)}"
        )

    return ResponseBase(
        code=BizCode.SUCCESS,
        message="File uploaded successfully",
        data={
            "file_id": file_info.file_id,
            "file_name": file_info.file_name,
            "file_size": file_info.file_size
        }
    )
