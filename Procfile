release: python manage.py migrate && python manage.py collectstatic --noinput
web: gunicorn rag_project.wsgi:application
