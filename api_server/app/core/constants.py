

from app.core.config import settings

# Database Field Length Constraints
DB_CHAR_FIELD_SHORT_MAX_LEN = 64     
DB_CHAR_FIELD_MEDIUM_MAX_LEN = 1024    
DB_CHAR_FIELD_LONG_MAX_LEN = 1024*10     

# Session Configuration
SESSION_EXPIRE_SECONDS = settings.SESSION_EXPIRE_SECONDS
SESSION_COOKIE_KEY = "sessionid"
SESSION_COOKIE_SECURE = settings.SESSION_COOKIE_SECURE
SESSION_INFO_KEY = "sessioninfo"


