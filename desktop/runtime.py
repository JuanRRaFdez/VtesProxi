import shutil
import sys
from pathlib import Path


def project_root():
    return Path(__file__).resolve().parent.parent


def app_base_dir():
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).resolve().parent
    return project_root()


def default_portable_dir():
    return app_base_dir() / 'portable_data'


def default_seed_dir():
    base_dir = app_base_dir()
    if getattr(sys, 'frozen', False):
        return base_dir / 'seed'
    return base_dir / 'desktop' / 'seed'


def ensure_seeded_runtime(portable_dir, seed_dir):
    portable_dir = Path(portable_dir)
    seed_dir = Path(seed_dir)
    portable_dir.mkdir(parents=True, exist_ok=True)

    database_path = portable_dir / 'db.sqlite3'
    seed_database_path = seed_dir / 'db.sqlite3'
    if not database_path.exists() and seed_database_path.exists():
        shutil.copy2(seed_database_path, database_path)

    media_path = portable_dir / 'media'
    seed_media_path = seed_dir / 'media'
    if not media_path.exists():
        if seed_media_path.exists():
            shutil.copytree(seed_media_path, media_path)
        else:
            media_path.mkdir(parents=True, exist_ok=True)

    return {
        'portable_dir': portable_dir,
        'database_path': database_path,
        'media_path': media_path,
    }
