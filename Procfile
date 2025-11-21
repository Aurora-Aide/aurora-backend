release: cd aurora_backend && python manage.py migrate --noinput
web: cd aurora_backend && gunicorn aurora_backend.wsgi:application --bind 0.0.0.0:$PORT

