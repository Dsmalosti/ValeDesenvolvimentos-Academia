release: flask --app main db upgrade
web: gunicorn main:app --workers 3 --bind 0.0.0.0:$PORT --access-logfile -
