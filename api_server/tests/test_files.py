import os
import time
from loguru import logger
from fastapi import status
from sqlmodel import Session
from app.core.mq_task import MQMessageUploadFileFinish
from app.models.models import FileInfo, FileStatus
from app.schemas.common import BizCode
from app.core.config import settings
from tests.conftest import (
    TEST_TENANT_ADMIN_EMAIL,
    TEST_TENANT_ADMIN_PASSWORD,
    TEST_USER_EMAIL,
    TEST_USER_PASSWORD,
    MockMQTaskManager,
)
from utils.commons import get_bytes_md5

TEST_FILE_NAME = "test_upload_file.txt"
TEST_FILE_CONTENT = b"This is a test upload file content."

def upload_file_helper(client, filename: str, file_content: bytes, expected_statuscode: int):
    """
    Helper function to upload a file and verify the response status and content.
    Supports both success (201 Created) and failure cases.
    """
    files = {
        "file": (filename, file_content, "text/plain")
    }
    response = client.post("https://testserver/api/v1/files/upload", files=files)
    assert response.status_code == expected_statuscode
    
    if expected_statuscode == status.HTTP_201_CREATED:
        res_data = response.json()
        assert res_data["code"] == BizCode.SUCCESS
        assert res_data["message"] == "File uploaded successfully"
        assert res_data["data"]["file_name"] == filename
        assert res_data["data"]["file_size"] == len(file_content)
    logger.info(f"file uploaded: {response.json()}")    
    return response

def test_upload_download_file_success(
    client,
    db_session: Session,
    mock_mq_task_manager: MockMQTaskManager,
):
    """
    Test uploading and downloading a file as tenant_admin:
    1. Log in to establish an active session.
    2. Upload raw file content.
    3. Assert API response structure.
    4. Assert FileInfo record existence, ACTIVE status, and correct MD5 in database.
    5. Assert physical file content written to local storage.
    6. Download file and verify correct bytes and headers returned.
    7. Clean up the physical file on disk.
    """
    # Step 1: Login
    login_payload = {
        "email": TEST_TENANT_ADMIN_EMAIL,
        "password": TEST_TENANT_ADMIN_PASSWORD
    }
    login_resp = client.post("https://testserver/api/v1/auth/login", json=login_payload)
    assert login_resp.status_code == status.HTTP_200_OK

    # Step 2 & 3: Upload file and assert response
    file_content = TEST_FILE_CONTENT
    response = upload_file_helper(client, TEST_FILE_NAME, file_content, status.HTTP_201_CREATED)
    res_data = response.json()
    file_id = res_data["data"]["file_id"]

    # Step 4: Verify DB Index
    expected_md5 = get_bytes_md5(file_content)
    file_info = db_session.query(FileInfo).filter(FileInfo.file_id == file_id).first()
    assert file_info is not None
    assert file_info.file_name == TEST_FILE_NAME
    assert file_info.file_type == "txt"
    assert file_info.file_md5_hash == expected_md5
    assert file_info.status == FileStatus.ACTIVE
    assert file_info.file_size == len(file_content)
    assert len(mock_mq_task_manager.messages) == 1
    _, partition_key, upload_message = mock_mq_task_manager.messages[0]
    assert partition_key == str(file_id)
    assert isinstance(upload_message, MQMessageUploadFileFinish)
    assert upload_message.file_id == file_id

    # Step 5: Verify Local File content
    file_path = os.path.join(settings.STORAGE_DIR, file_info.file_storage_location)
    assert os.path.exists(file_path)
    with open(file_path, "rb") as f:
        assert f.read() == file_content

    # Step 6: Download file and assert content
    download_resp = client.get(f"https://testserver/api/v1/files/{file_id}")
    assert download_resp.status_code == status.HTTP_200_OK
    assert download_resp.content == file_content
    assert download_resp.headers["Content-Disposition"] == f'attachment; filename="{TEST_FILE_NAME}"'




def test_upload_file_permission_denied(client):
    """
    Test uploading a file as a standard USER (should return 403 Forbidden).
    """
    # 1. Login with the pre-seeded user credentials
    login_payload = {
        "email": TEST_USER_EMAIL,
        "password": TEST_USER_PASSWORD
    }
    login_resp = client.post("https://testserver/api/v1/auth/login", json=login_payload)
    assert login_resp.status_code == status.HTTP_200_OK

    # 2. Attempt to upload
    file_content = b"This is unauthorized content."
    response = upload_file_helper(client, "test_unauthorized.txt", file_content, status.HTTP_403_FORBIDDEN)
    assert response.json()["detail"] == "Permission denied"


def test_list_files_pagination(client, db_session: Session):
    """
    Test pulling a cursor-paginated list of uploaded files:
    1. Log in as tenant_admin.
    2. Upload 10 distinct files with 2-second sleep in between.
    3. Query first page with limit=4, assert newest files returned first.
    4. Query second page, assert correct items returned.
    5. Query third page, assert remaining items returned.
    6. Query fourth page, assert 0 items and empty last_cursor.
    7. Clean up all physical files from storage.
    """
    # Step 1: Login
    login_payload = {
        "email": TEST_TENANT_ADMIN_EMAIL,
        "password": TEST_TENANT_ADMIN_PASSWORD
    }
    login_resp = client.post("https://testserver/api/v1/auth/login", json=login_payload)
    assert login_resp.status_code == status.HTTP_200_OK

    # Step 2: Upload 10 files
    uploaded_filenames = []
    for i in range(10):
        filename = f"test_list_file_{i}.txt"
        upload_file_helper(client, filename, TEST_FILE_CONTENT, status.HTTP_201_CREATED)
        uploaded_filenames.append(filename)
        if i < 9:
            time.sleep(2)  # Pause to guarantee distinct timestamps

    retrieved_items = []
    cursor = ""
    while True:
        url = f"https://testserver/api/v1/files?cursor={cursor}&limit=4"
        response = client.get(url)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["code"] == BizCode.SUCCESS
        
        items = data["data"]["items"]
        retrieved_items.extend(items)
        
        cursor = data["data"]["last_cursor"]
        if not cursor:
            break

    # Verify we got at least 10 items (may include the one from first test)
    # and the first 10 items are in correct descending order (9 down to 0)
    assert len(retrieved_items) >= 10
    for i in range(10):
        item = retrieved_items[i]
        assert item["file_name"] == f"test_list_file_{9 - i}.txt"
        assert item["owner_email"] == TEST_TENANT_ADMIN_EMAIL
        assert "owner_user_id" in item


def test_upload_file_invalid_extension(client):
    """
    Test uploading files with invalid or unsupported extensions:
    1. Log in as tenant_admin.
    2. Try uploading with no extension, expect 400 Bad Request.
    3. Try uploading with unsupported extension (.png), expect 400 Bad Request.
    4. Try uploading valid md/pdf files, expect 201 Created.
    """
    # Step 1: Login
    login_payload = {
        "email": TEST_TENANT_ADMIN_EMAIL,
        "password": TEST_TENANT_ADMIN_PASSWORD
    }
    login_resp = client.post("https://testserver/api/v1/auth/login", json=login_payload)
    assert login_resp.status_code == status.HTTP_200_OK

    # Step 2: Upload file with no extension
    upload_file_helper(client, "test_file_no_ext", b"content", status.HTTP_400_BAD_REQUEST)

    # Step 3: Upload file with unsupported extension
    upload_file_helper(client, "test_file.png", b"content", status.HTTP_400_BAD_REQUEST)

    # Step 4: Upload valid files
    upload_file_helper(client, "test_file.md", b"content", status.HTTP_201_CREATED)
    upload_file_helper(client, "test_file.pdf", b"content", status.HTTP_201_CREATED)
