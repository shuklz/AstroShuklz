"""
WSGI entry point for PythonAnywhere.
Point your PythonAnywhere web app's WSGI config to this file.

In PythonAnywhere's WSGI configuration file
(/var/www/shuklz_pythonanywhere_com_wsgi.py), replace the contents with:

    import sys
    path = '/home/shuklz/AstroShuklz'
    if path not in sys.path:
        sys.path.insert(0, path)
    from wsgi import application
"""

from app import app as application
