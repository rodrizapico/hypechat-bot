FROM python:3.6.5-slim

RUN mkdir -p /app
WORKDIR /app

EXPOSE 5000

COPY requirements.txt .
RUN pip install --upgrade pip --no-cache-dir -r requirements.txt
COPY . .

CMD ["python", "app.py"]