FROM python:3.12.3-slim

# Actualiza la lista de paquetes e instala dependencias necesarias
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    ca-certificates \
    curl \
    libgl1-mesa-glx \
    libglib2.0-0 \
    software-properties-common && \
    rm -rf /var/lib/apt/lists/*

# Agregar el repositorio de NVIDIA para Debian 11 (Bookworm)
RUN wget https://developer.download.nvidia.com/compute/cuda/repos/debian11/x86_64/cuda-keyring_1.0-1_all.deb && \
    dpkg -i cuda-keyring_1.0-1_all.deb && \
    apt-get update

# Instalar CUDA
RUN apt-get install -y cuda-toolkit-12-6 && \
    rm -rf /var/lib/apt/lists/*

# Agregar CUDA al PATH y LD_LIBRARY_PATH
ENV PATH="/usr/local/cuda/bin:${PATH}"
ENV LD_LIBRARY_PATH="/usr/local/cuda/lib64:${LD_LIBRARY_PATH}"

# Establece el directorio de trabajo
WORKDIR /app

# Copia los archivos del proyecto al contenedor
COPY . .

# Instala las dependencias de Python desde requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Comando para ejecutar el archivo principal del contenedor
CMD ["python", "-u","worker_cpu_gpu_custom.py"]
