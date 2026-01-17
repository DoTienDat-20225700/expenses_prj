release: cd expenses && python manage.py migrate
web: cd expenses && gunicorn config.wsgi --bind 0.0.0.0:$PORT
