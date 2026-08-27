import os


class BaseConfig:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-insecure-key")

    # The daily article-count file srwiki's long-running `brcl` Toolforge job
    # appends to (untouched by this app -- see docs/deployment-toolforge.md).
    # The webservice must be started with NFS mounted so this path resolves.
    BROJCLANAKA_PATH = os.environ.get(
        "BROJCLANAKA_PATH", "/data/project/srwiki/public_html/brojclanaka"
    )

    SRWIKI_DB_HOST = os.environ.get("SRWIKI_DB_HOST", "srwiki.analytics.db.svc.wikimedia.cloud")
    COMMONSWIKI_DB_HOST = os.environ.get(
        "COMMONSWIKI_DB_HOST", "commonswiki.analytics.db.svc.wikimedia.cloud"
    )


class DevelopmentConfig(BaseConfig):
    DEBUG = True


class TestingConfig(BaseConfig):
    TESTING = True


class ProductionConfig(BaseConfig):
    DEBUG = False


CONFIG_BY_NAME = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}
