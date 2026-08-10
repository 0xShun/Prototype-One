# PythonAnywhere Setup Guide (Prototype-One)

This project is prepared for deployment using environment variables and `collectstatic`.

## 1) Clone from GitHub on PythonAnywhere

```bash
git clone git@github.com:0xShun/Prototype-One.git
cd Prototype-One
```

## 2) Create and activate a virtualenv

Use a Python version that PythonAnywhere currently supports and matches your app choice on the Web tab.

This repo pins Django 5.2.x so it works with Python 3.10 on PythonAnywhere. Django 6.x requires Python 3.12+.

```bash
mkvirtualenv --python=/usr/bin/python3.10 prototypeone-venv
workon prototypeone-venv
pip install -r requirements.txt
```

## 3) Configure environment variables for production

In PythonAnywhere, set these in the Web app environment (or in the WSGI file if you prefer):

- `DJANGO_SECRET_KEY`: a strong secret value
- `DJANGO_DEBUG`: `false`
- `DJANGO_ALLOWED_HOSTS`: `yourusername.pythonanywhere.com`
- `DJANGO_CSRF_TRUSTED_ORIGINS`: `https://yourusername.pythonanywhere.com`

If you later add a custom domain, append it to both host/origin values.

## 4) Create the Web app (Manual config)

In the Web tab:

1. Create a new app with **Manual Configuration** (not the Django preset).
2. Pick the same Python version as the virtualenv.
3. Set your virtualenv path to `/home/yourusername/.virtualenvs/prototypeone-venv`.
4. Set source code/working directory to `/home/yourusername/Prototype-One`.

## 5) Configure the PythonAnywhere WSGI file

Important: PythonAnywhere uses `/var/www/yourusername_pythonanywhere_com_wsgi.py`, not this repo's `studentsense/wsgi.py`.

Set it up like:

```python
import os
import sys

path = '/home/yourusername/Prototype-One'
if path not in sys.path:
    sys.path.insert(0, path)

os.environ['DJANGO_SETTINGS_MODULE'] = 'studentsense.settings'

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

## 6) Run migrations and collect static files

```bash
cd /home/yourusername/Prototype-One
python manage.py migrate
python manage.py collectstatic --noinput
```

## 7) Static files mapping in Web tab

Add static mapping:

- URL: `/static/`
- Directory: `/home/yourusername/Prototype-One/staticfiles`

Then click **Reload** on the Web tab.

## 8) Optional sanity checks

```bash
python manage.py check --deploy
```

Address any warnings that matter for your launch stage.
