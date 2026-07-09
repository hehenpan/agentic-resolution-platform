import os
from fastapi import status
from sqlmodel import Session
from app.models.models import FileInfo, FileStatus
from app.schemas.common import BizCode
from app.core.config import settings
from tests.conftest import TEST_TENANT_ADMIN_EMAIL, TEST_TENANT_ADMIN_PASSWORD, TEST_USER_EMAIL, TEST_USER_PASSWORD
from utils.commons import get_bytes_md5

TEST_FILE_NAME = "test_upload_file.txt"
TEST_FILE_CONTENT = b"This is a test upload file content."

def test_upload_download_file_success(client, db_session: Session):
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

    # Step 2: Upload file
    file_content = TEST_FILE_CONTENT
    files = {
        "file": (TEST_FILE_NAME, file_content, "text/plain")
    }
    response = client.post("https://testserver/api/v1/files/upload", files=files)

    # Step 3: Assert response
    assert response.status_code == status.HTTP_201_CREATED
    res_data = response.json()
    assert res_data["code"] == BizCode.SUCCESS
    assert res_data["message"] == "File uploaded successfully"

    file_id = res_data["data"]["file_id"]
    file_name = res_data["data"]["file_name"]
    file_size = res_data["data"]["file_size"]
    assert file_name == TEST_FILE_NAME
    assert file_size == len(file_content)

    # Step 4: Verify DB Index
    expected_md5 = get_bytes_md5(file_content)
    file_info = db_session.query(FileInfo).filter(FileInfo.file_id == file_id).first()
    assert file_info is not None
    assert file_info.file_name == TEST_FILE_NAME
    assert file_info.file_type == "txt"
    assert file_info.file_md5_hash == expected_md5
    assert file_info.status == FileStatus.ACTIVE
    assert file_info.file_size == len(file_content)

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

    # Step 7: Cleanup physical test file
    if os.path.exists(file_path):
        os.remove(file_path)




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
    files = {
        "file": ("test_unauthorized.txt", file_content, "text/plain")
    }
    response = client.post("https://testserver/api/v1/files/upload", files=files)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["detail"] == "Permission denied"

