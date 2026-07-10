# 1. Pakai base image Python 3.10 resmi
FROM python:3.10-slim

# 2. Install dependencies Linux (Pakai libgl1 yang disupport penuh oleh Debian Trixie)
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 3. Set folder kerja di dalam server cloud
WORKDIR /app

# 4. Copy file requirements biar proses cache cepet
COPY requirements.txt .

# 5. Install semua library python bawaan proyek lo
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir gunicorn

# 6. Copy seluruh sisa file project backend lo ke container
COPY . .

# 7. Jalankan port 5000 sesuai setelan Flask
EXPOSE 5000

# 8. Jalankan Flask pake Gunicorn dengan timeout panjang biar aman pas load AI
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--timeout", "120", "app:app"]