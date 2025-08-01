
FROM python:3.11-slim


WORKDIR /app


COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt


COPY . .


EXPOSE 8080


ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8080", "--server.enableCORS=false"]