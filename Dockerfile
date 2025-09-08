FROM nikolaik/python-nodejs:python3.11-nodejs19

RUN useradd -m -u 10014 -s /bin/bash appuser

# RUN apt-get update && \
#     apt-get install -y ca-certificates && \
#     apt-get clean && \
#     rm -rf /var/lib/apt/lists/*

COPY --chown=appuser:appuser requirements.txt /app/
WORKDIR /app/

RUN python3 -m pip install --upgrade pip setuptools && \
    pip3 install --no-cache-dir --upgrade --requirement requirements.txt

COPY --chown=appuser:appuser . /app/

USER appuser

EXPOSE 8000

CMD python3 main.py
