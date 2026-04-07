# Studybuddy-backend

To get started:

Ensure you have Python (>=3.11), Git, pip + virtualenv, postgresql (or docker), uv (optional)


1. Clone the repo:
```bash
git clone https://github.com/studybuddyafrica/studybuddy-backend
```

2. cd to the repo and setup the environment + install dependecies
```bash
cd studybuddy-backend

virtualenv .venv # or using uv venv

source .venv/bin/activate

pip install -r requirements.txt

# copy local .env variables
cp .env.example .env
````

3. Run and test the code
```bash
# make database migrations
python manage.py makemigrations

python manage.py migrate

python manage.py run server
#or
gunicorn config.wsgi

#then on a new tab
curl -I http://127.0.0.1:8000/api/
```

Response:
```json
HTTP/1.1 200 OK
Date: Tue, 07 Apr 2026 11:16:25 GMT
Server: WSGIServer/0.2 CPython/3.14.3
Content-Type: application/json
Vary: Accept, origin
Allow: GET, HEAD, OPTIONS
X-Frame-Options: ALLOWALL
Content-Length: 109
X-Content-Type-Options: nosniff
Referrer-Policy: same-origin
Cross-Origin-Opener-Policy: same-origin
```