FROM python:3.12-slim

WORKDIR /app
RUN apt-get update && \
    apt-get install -y git && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY . .

RUN python3 -m pip install -e .

CMD ["python3", "-m", "cypher_shell"]
