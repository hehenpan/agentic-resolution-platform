/** File Data Schemas aligned with api_server/app/schemas/files.py and common.py */

export interface FileItemResponse {
  file_id: number;
  file_name: string;
  file_size: number;
  file_type: string;
  file_md5_hash: string;
  owner_user_id: number;
  owner_email: string;
  create_ts: number;
  status: number;
  vector_db_sync_status: number;
}

export interface FileListResponseData {
  items: FileItemResponse[];
  last_cursor: string;
}

export interface FileListResponse {
  code: number;
  message: string;
  data: FileListResponseData;
}

export interface FileUploadResponseData {
  file_id: number;
  file_name: string;
  file_size: number;
}

export interface FileUploadResponse {
  code: number;
  message: string;
  data: FileUploadResponseData;
}
