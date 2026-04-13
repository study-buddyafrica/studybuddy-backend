FROM python:3.14-alpine

WORKDIR /backend

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apk add curl 
#build-base libpq-dev python3-dev

COPY requirements.txt .

RUN curl -LsSf https://astral.sh/uv/install.sh | sh

RUN source $HOME/.local/bin/env 

ENV PATH="/root/.local/bin:$PATH"

RUN uv pip install --system -r requirements.txt

COPY . . 

EXPOSE 8000

CMD ["uvicorn", "config.asgi:application", "--host", "0.0.0.0", "--port", "8000"]