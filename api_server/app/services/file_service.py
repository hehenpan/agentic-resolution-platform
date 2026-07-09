import os
from sqlmodel import Session
from app.models.models import FileInfo, FileStatus, FileSyncStatus, FileStorageType
from utils.commons import generate_uuid_hex, get_current_ts
from app.core.config import settings
from loguru import logger



class FileRawDataStorageBase(object):
    def __init__(self):
        pass

    def save(self, fileinfo: FileInfo, content):
        raise Exception("Not Implemented")
        
    def delete(self, fileinfo: FileInfo):
        raise Exception("Not Implemented")

    def load(self, fileinfo: FileInfo):
        raise Exception("Not Implemented")


class LocalFileRawDataStorage(FileRawDataStorageBase):
    def __init__(self):
        super().__init__()

    def save(self, fileinfo: FileInfo, content: bytes):
        """Save file bytes to local disk storage."""
        os.makedirs(settings.STORAGE_DIR, exist_ok=True)
        file_path = os.path.join(settings.STORAGE_DIR, fileinfo.file_storage_location)
        try:
            with open(file_path, "wb") as f:
                f.write(content)
            logger.info(f"File raw data successfully saved locally to: {file_path}")
        except Exception as e:
            logger.error(f"Failed to save file data locally to: {file_path}. Error: {e}")
            raise e
        
    def delete(self, fileinfo: FileInfo):
        """Delete local file from disk storage."""
        file_path = os.path.join(settings.STORAGE_DIR, fileinfo.file_storage_location)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"File raw data successfully deleted locally from: {file_path}")
            except Exception as e:
                logger.error(f"Failed to delete file data locally from: {file_path}. Error: {e}")
                raise e

    def load(self, fileinfo: FileInfo) -> bytes:
        """Read and return file bytes from local disk storage."""
        file_path = os.path.join(settings.STORAGE_DIR, fileinfo.file_storage_location)
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File raw data not found at: {file_path}")
        try:
            with open(file_path, "rb") as f:
                content = f.read()
            return content
        except Exception as e:
            logger.error(f"Failed to read file data locally from: {file_path}. Error: {e}")
            raise e


class S3FileRawDataStorage(FileRawDataStorageBase):
    def __init__(self):
        super().__init__()

    def save(self, fileinfo: FileInfo, content: bytes):
        """Save file bytes to S3."""
        raise Exception("Not Implemented")
        

    def delete(self, fileinfo: FileInfo):
        """Delete file from S3."""
        raise Exception("Not Implemented")

    def load(self, fileinfo: FileInfo) -> bytes:
        """Read file bytes from S3."""
        raise Exception("Not Implemented")

def create_file_raw_data_storage(storage_type: FileStorageType=None) -> FileRawDataStorageBase:
    if storage_type is None:
        storage_type_str = settings.FILE_STORAGE_TYPE
        if storage_type_str == "s3":
            storage_type = FileStorageType.S3
        elif storage_type_str == "local":
            storage_type = FileStorageType.LOCAL
        else:
            raise ValueError(f"Unsupported storage type in settings: {storage_type_str}")

        
    if storage_type == FileStorageType.LOCAL:
        return LocalFileRawDataStorage()
    elif storage_type == FileStorageType.S3:
        return S3FileRawDataStorage()
    else:
        raise ValueError(f"Unsupported storage type: {storage_type}")


class FileService(object):
    """
    Service class managing file indexing metadata and physical data storage.
    """
    def __init__(self, dbsession: Session):
        self.dbsession = dbsession
        self.storage = create_file_raw_data_storage()

    def create_file_index(self, tenant_id: int, owner_user_id: int, owner_email: str, filename: str, file_size: int, file_md5_hash: str) -> FileInfo:
        """
        Step 1: Create a file index record in the database with status = INVALID (0).
        """
        ext = os.path.splitext(filename)[1].lower()
        random_filename = f"{generate_uuid_hex()}{ext}"
        file_type = ext.lstrip(".") if ext else "unknown"

        file_info = FileInfo(
            tenant_id=tenant_id,
            owner_user_id=owner_user_id,
            owner_email=owner_email,
            file_name=filename,
            file_type=file_type,
            file_md5_hash=file_md5_hash,
            file_storage_location=random_filename,
            file_storage_type=FileStorageType.LOCAL,
            file_size=file_size,

            create_ts=get_current_ts(),
            status=FileStatus.INVALID,
            vector_db_sync_status=FileSyncStatus.PENDING
        )

        self.dbsession.add(file_info)
        self.dbsession.commit()
        self.dbsession.refresh(file_info)
        logger.info(f"File index created in INVALID status for file_id={file_info.file_id}, file_name={filename}")
        return file_info

    def store_file_content(self, file_info: FileInfo, content: bytes) -> None:
        """
        Step 2: Save the file raw data to local disk.
        """
        
        self.storage.save(file_info, content)


    def activate_file_index(self, file_id: int) -> FileInfo:
        """
        Step 3: Update the file status to ACTIVE (1) in the database.
        """
        file_info = self.dbsession.query(FileInfo).filter(FileInfo.file_id == file_id).first()
        if not file_info:
            raise ValueError(f"FileInfo record not found for file_id={file_id}")

        file_info.status = FileStatus.ACTIVE
        self.dbsession.add(file_info)
        self.dbsession.commit()
        self.dbsession.refresh(file_info)
        logger.info(f"File index activated (status=ACTIVE) for file_id={file_id}")
        return file_info
