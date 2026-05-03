# Studybuddy-backend

To get started: (the readme assumes you are running on a Linux/MacOs system)

Ensure you have Python (>=3.11), Git, pip + virtualenv, postgresql (or docker), uv (optional)

1. Clone the repo:

```bash
git clone https://github.com/studybuddyafrica/studybuddy-backend
```

1. cd to the repo and setup the environment + install dependecies

```bash
cd studybuddy-backend

virtualenv .venv # or using uv venv

source .venv/bin/activate

pip install -r requirements.txt

# copy local .env variables
cp .env.example .env
````

1. Run and test the code

```bash

#optional (start the docker postgresql service)
# ensure to stop any other postgresql running on port 5432 -> failed to bind host port 0.0.0.0:5432/tcp: address already in use
sudo systemctl stop postgresql

sudo systemctl stop redis

# will start postgresql and redis in docker (make sure you have docker installed and running)
docker compose up # add -d to detach it or open a new tab

# make database migrations
python manage.py makemigrations

python manage.py migrate

python manage.py run server
# or
gunicorn config.wsgi
# or
uvicorn config.asgi:application --reload

#then on a new tab
curl -I http://127.0.0.1:8000/api/health/

# seed the database
source .venv/bin/activate && python manage.py seed_demo_data --limit 5
```

Response:

```json
HTTP/2.0 200 OK
Allow: GET, HEAD, OPTIONS
Content-Length: 28
Content-Type: application/json
Cross-Origin-Opener-Policy: same-origin
Date: Tue, 07 Apr 2026 18:34:30 GMT
Referrer-Policy: same-origin
Server: uvicorn
Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
Vary: origin
X-Content-Type-Options: nosniff
X-Frame-Options: SAMEORIGIN

{
  db_ms: 21.6
  status: "ok"
}
```

Swagger UI: <http://127.0.0.1:8000/api/swagger/>

Environment keys used by the payment, media, and live-session features:

```bash
PAYSTACK_SECRET_KEY=
WITHDRAWAL_PLATFORM_FEE_PERCENT=30
PAYSTACK_TRANSFER_FEE_PERCENT=0
PAYSTACK_FX_FEE_PERCENT=0
FFMPEG_BINARY=ffmpeg
HLS_STORAGE_ROOT=
HLS_URL_TTL_SECONDS=900
HLS_ENABLE_ENCRYPTION=true
ZOOM_SDK_KEY=
ZOOM_SDK_SECRET=
ZOOM_SDK_TOKEN_TTL_SECONDS=120
PEER_SESSION_BASE_URL=
PEER_SESSION_TOKEN_TTL_SECONDS=900
```

`INTASEND_*` values are still read by legacy compatibility paths until those are fully removed.

To check for outdated packages:

```bash
pip-audit

pip-review --auto # to update outdated packages
```

Known issues:

```
'default': connection to server at "localhost" (127.0.0.1), port 5432 failed: Connection refused
 Is the server running on that host and accepting TCP/IP connections?
```

Staging: <https://api-staging.studybuddy.africa/>

<https://studybuddy-frotend-staging.vercel.app/>
