FROM python:3.12-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
COPY requirements-api.txt /app/requirements-api.txt
RUN pip install --no-cache-dir -r /app/requirements-api.txt
COPY . /app
EXPOSE 8000
CMD ["python","-m","uvicorn","main:app","--host","0.0.0.0","--port","8000"]
