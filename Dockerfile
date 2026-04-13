# Usa uma imagem Python oficial levinha
FROM python:3.10-slim

# Cria um usuário não-root para rodar a aplicação (Security Best Practice)
RUN groupadd -r app_group && useradd -r -g app_group -u 1000 app_user

# Define o diretório de trabalho dentro do container
WORKDIR /app

# Instala dependências do sistema necessárias
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copia o arquivo de dependências e instala
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o restante do código para o container garantindo que o app_user seja o dono
COPY --chown=app_user:app_group . .

# Cria os diretórios de persistência se não existirem e garante permissões
RUN mkdir -p repositorio chroma_db && \
    chown -R app_user:app_group /app

# Switch to non-root user
USER app_user

# Expõe a porta que o FastAPI usa
EXPOSE 8000

# Comando para rodar a aplicação
CMD ["python", "server.py"]
