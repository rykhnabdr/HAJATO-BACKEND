# 1. Pakai base image Python yang lengkap dengan tools compiler C++
FROM python:3.10-slim

# 2. Install dependencies sistem OS yang dibutuhin InsightFace & OpenCV
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    libgl1-mesa-glx \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 3. Set folder kerja di dalam container
WORKDIR /app

# 4. Copy file requirements dulu biar proses build cache-nya cepet
COPY requirements.txt .

# 5. Install semua library python
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir gunicorn

# 6. Copy seluruh sisa file project backend lo ke container
COPY . .

# 7. Expose port 5000 sesuai setelan Flask
EXPOSE 5000

# 8. Jalankan Flask pake Gunicorn di port 5000 dengan timeout panjang (karena load model AI berat)
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--timeout", "120", "app:app"]