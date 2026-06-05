# Gunakan Python versi 3.9 (sesuaikan jika di requirements.txt beda)
FROM python:3.9-slim

# Set direktori kerja di dalam container
WORKDIR /app

# Copy file requirements agar install dependencies lebih cepat 
COPY requirements.txt .

# Install dependencies Python
RUN pip install --no-cache-dir -r requirements.txt

# Copy semua file backend (termasuk folder models/) ke dalam container
COPY . .

# Buka port 8000 (default FastAPI/Uvicorn)
EXPOSE 8000

# Jalankan aplikasi saat container dimulai
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
