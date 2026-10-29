FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src ./src
COPY web ./web
COPY web_server.py ./web_server.py
COPY assets ./assets
COPY dados_sensores_vulcantech.csv ./dados_sensores_vulcantech.csv
RUN python src/pipeline.py && python src/treinar_modelo.py
EXPOSE 8000 5500
CMD ["uvicorn", "api:app", "--app-dir", "src", "--host", "0.0.0.0", "--port", "8000"]
