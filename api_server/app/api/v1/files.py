from fastapi import APIRouter, status, Depends, HTTPException, UploadFile, File, Response
from pydantic import ValidationError
from app.api.deps import get_current_user, get_file_service, get_rbac_service
from app.models.models import User, UserType
from app.services.file_service import FileService
from app.services.rbac_service import RBACServiceBase, Permission
from app.schemas.common import ResponseBase, BizCode
from app.schemas.files import FileDownloadRequest
from utils.commons import get_bytes_md5

file_router = APIRouter()

@file_router.post("/files/upload", response_model=ResponseBase, status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    file_service: FileService = Depends(get_file_service),
    rbac_service: RBACServiceBase = Depends(get_rbac_service)
):
    """
    Upload a file:
    1. Enforces Permission.USER_MANAGE.
    2. Creates a database index with status=INVALID (0).
    3. Writes the file raw data to local disk.
    4. Activates the index by updating status to ACTIVE (1).
    """
    # Enforce RBAC permission check
    if not rbac_service.has_permission(
        user=current_user,
        permission=Permission.USER_MANAGE,
        resource_tenant_id=current_user.tenant_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied"
        )

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


@file_router.get("/files/{file_id}", response_class=Response)
async def download_file(
    file_id: int,
    current_user: User = Depends(get_current_user),
    file_service: FileService = Depends(get_file_service),
    rbac_service: RBACServiceBase = Depends(get_rbac_service)
):
    """
    Download a file:
    1. Validates file_id using FileDownloadRequest schema.
    2. Enforces Permission.USER_READ.
    3. Retrieves the file metadata.
    4. Enforces multi-tenant isolation.
    5. Loads file bytes from storage and returns them at once.
    """
    # Validate the parameter using the FileDownloadRequest schema
    try:
        FileDownloadRequest(file_id=file_id)
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=e.errors()
        )

    # Enforce RBAC permission check
    if not rbac_service.has_permission(
        user=current_user,
        permission=Permission.USER_READ,
        resource_tenant_id=current_user.tenant_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied"
        )

    # Retrieve file info
    file_info = file_service.get_file_info(file_id)
    if not file_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )

    # Multi-tenant isolation: standard tenant users must belong to the file's tenant
    if not rbac_service.has_permission(
        user=current_user,
        permission=Permission.USER_READ, 
        resource_tenant_id=file_info.tenant_id,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied"
        )

    # Load file content
    try:
        content = file_service.get_file_content(file_info)
    
       
    except Exception as e:
        logger.error(f"Failed to load file content: {e}", extra={
            "file_id": file_id,
            "file_info": file_info,
        })
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load file content: {str(e)}"
        )

    # Return raw file content with original filename
    headers = {
        "Content-Disposition": f'attachment; filename="{file_info.file_name}"'
    }
    return Response(content=content, media_type="application/octet-stream", headers=headers)

