from pathlib import Path
import os
import certifi
import ssl

#import dj_database_url


from dotenv import load_dotenv
load_dotenv()


BASE_DIR = Path(__file__).resolve().parent.parent

#open ai settings
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise RuntimeError("❌ OPENAI_API_KEY is not set")


# =========================
# SECURITY
# =========================
#SECRET_KEY = "django-insecure-change-me"


SECRET_KEY = os.getenv("DJANGO_SECRET_KEY")


DEBUG = True

ALLOWED_HOSTS = []




# =========================
# APPLICATIONS
# =========================
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",

    "accounts",
    "documents",
    "rag",
    "core",
]


# =========================
# MIDDLEWARE
# =========================
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",

    # ✅ Role permission middleware
    "accounts.middleware.RolePermissionMiddleware",

    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


ROOT_URLCONF = "rag_project.urls"

# =========================
# TEMPLATES
# =========================
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",

                # 👇 YOURS
                "accounts.context_processors.user_profile",
                "accounts.context_processors.permissions_context",
            ],
        },
    },
]


WSGI_APPLICATION = "rag_project.wsgi.application"

# =========================
# DATABASE (SQLite for now)
# =========================
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}



# =========================
# AUTH
# =========================
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


AUTHENTICATION_BACKENDS = [
    "accounts.auth_backends.EmailAuthBackend",
    "django.contrib.auth.backends.ModelBackend",
]



LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "document_list"
LOGOUT_REDIRECT_URL = "/accounts/login/"



# =========================
# I18N
# =========================
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# =========================
# STATIC & MEDIA
# =========================
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
#STATIC_ROOT = BASE_DIR / "staticfiles"
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# =========================
# DEFAULTS
# =========================
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# =========================
# OPENAI
# =========================
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# =========================
# RAG SETTINGS
# =========================
FAISS_INDEX_DIR = BASE_DIR / "faiss_indexes"
EMBEDDING_MODEL = "text-embedding-3-small"
CHAT_MODEL = "gpt-4o-mini"

FAISS_INDEX_DIR = BASE_DIR / "faiss_indexes"
EMBEDDING_DIM = 1536  # OpenAI embedding size


# =========================
# UPLOAD SETTINGS (FINAL)
# =========================
DATA_UPLOAD_MAX_MEMORY_SIZE = 524288000     # 500MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 524288000     # 500MB

FILE_UPLOAD_HANDLERS = [
    "django.core.files.uploadhandler.TemporaryFileUploadHandler",
]


#EMAIL SETTINGS (BREVO SMTP)
# -------------------------------------------------------------------

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

EMAIL_HOST = os.getenv("EMAIL_HOST")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", 587))
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS") == "True"

EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")

DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL")

EMAIL_TIMEOUT = 30



#DATABASES = {
    #"default": dj_database_url.config(
      #  default=os.environ.get("DATABASE_URL"),
      #  conn_max_age=600,
      #  ssl_require=True,
   # )
#}








