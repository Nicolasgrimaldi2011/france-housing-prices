FROM python:3.12-slim 
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY dashboard.py .
CMD ["python", "-m", "streamlit", "run", "dashboard.py", "--server.address=0.0.0.0"]
