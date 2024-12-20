# Usa una imagen base oficial de Python
FROM python:3.12.2-slim

# Establece el directorio de trabajo dentro del contenedor
WORKDIR /bot

# Instala las dependencias necesarias para Poetry
RUN apt-get update && \
    apt-get install -y build-essential curl && \
    curl -sSL https://install.python-poetry.org | python3 - && \
    ln -s /root/.local/bin/poetry /usr/local/bin/poetry && \
    apt-get clean

# Instala el comando ping
RUN apt-get update && apt-get install -y iputils-ping && rm -rf /var/lib/apt/lists/*

# Copia el archivo pyproject.toml y poetry.lock para instalar las dependencias
COPY pyproject.toml poetry.lock /bot/

# Instala las dependencias con Poetry
RUN poetry install --no-interaction --no-ansi

# Copia todo el código de la aplicación al contenedor
COPY . /bot/

# Actualiza las dependencias (si hay cambios en pyproject.toml o poetry.lock)
RUN poetry update

ENV PYTHONPATH=/bot/app

# Define el comando que se ejecutará al iniciar el contenedor
CMD ["/bin/bash", "app/bootstrap.sh"]
