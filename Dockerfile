FROM tiangolo/uwsgi-nginx-flask:python3.12
WORKDIR /var/www/app/
ENV STATIC_URL=/static
ENV STATIC_PATH=/var/www/app/static
RUN --mount=type=bind,source=requirements.txt,target=/requirements.txt pip install -r /requirements.txt
COPY manifest.json manifest.json
COPY sw.js sw.js
COPY static static
COPY templates templates
COPY main.py main.py
