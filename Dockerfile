# Usa Python slim para que pese menos
FROM python:3.11-slim

# Carpeta de trabajo
WORKDIR /app

# Copiar dependencias
COPY requirements.txt .

# Instalar dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Copiar todo tu código
COPY . .

# Puerto que usará tu app
EXPOSE 8080

# Comando para correr tu app
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:8080"]


