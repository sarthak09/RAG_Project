
FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*


WORKDIR /app

COPY Backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY Frontend/package*.json ./Frontend/
WORKDIR /app/Frontend
RUN npm install
COPY Frontend/ ./
RUN npm run build

WORKDIR /app
COPY Backend/ ./Backend/

EXPOSE 5000

CMD ["python", "Backend/backend.py"]