# base image
FROM python:3.13-alpine
# use uv image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
# working directory
WORKDIR /backend
# don't store bytecode and don't buffer output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# copy requirements and install dependencies (good for caching and speeding up builds)
COPY requirements.txt .

RUN uv pip install --system -r requirements.txt

# copy the rest of the code
COPY . . 

EXPOSE 8000

CMD ["uvicorn", "config.asgi:application", "--host", "0.0.0.0", "--port", "8000"]