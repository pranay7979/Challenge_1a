FROM --platform=linux/amd64 python:3.10-slim

WORKDIR /app

# Copy app files
COPY app /app

# Install dependencies
RUN pip install --no-cache-dir pdfminer.six

# Entrypoint
CMD ["python3", "main.py"]
