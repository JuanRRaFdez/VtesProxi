import argparse
import json
import os
import sys
from pathlib import Path


def _ensure_project_root_on_path():
    project_root = Path(__file__).resolve().parent.parent
    project_root_str = str(project_root)
    if project_root_str not in sys.path:
        sys.path.insert(0, project_root_str)
    return project_root


def bootstrap_local_user(username, password):
    if not username or not username.strip():
        raise ValueError('username is required')
    if not password:
        raise ValueError('password is required')

    from django.contrib.auth import get_user_model

    normalized_username = username.strip()
    user_model = get_user_model()
    user = user_model.objects.filter(username=normalized_username).first()
    if user:
        return {'created': False, 'username': user.username}

    user = user_model.objects.create_user(username=normalized_username, password=password)
    return {'created': True, 'username': user.username}


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description='Create the first local normal user if missing.')
    parser.add_argument('--username', required=True)
    parser.add_argument('--password', required=True)
    parser.add_argument('--portable-dir', default='')
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    _ensure_project_root_on_path()
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'webvtes.settings_desktop')
    if args.portable_dir:
        os.environ['WEBVTES_PORTABLE_DIR'] = args.portable_dir

    import django

    django.setup()
    result = bootstrap_local_user(args.username, args.password)
    print(json.dumps(result))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
