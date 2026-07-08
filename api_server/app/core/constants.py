

# Database Field Length Constraints
DB_CHAR_FIELD_SHORT_MAX_LEN = 64     
DB_CHAR_FIELD_MEDIUM_MAX_LEN = 1024    
DB_CHAR_FIELD_LONG_MAX_LEN = 1024*10     

# Session Configuration
SESSION_EXPIRE_SECONDS = 60 * 60 * 24 * 30  # 30 days in seconds
SESSION_COOKIE_KEY = "sessionid"
SESSION_COOKIE_SECURE = True  # Set to True in HTTPS production environments
SESSION_INFO_KEY = "sessioninfo"

