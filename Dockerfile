FROM nikolaik/python-nodejs:python3.11-nodejs19

RUN useradd -m -u 10014 -s /bin/bash appuser

RUN sed -i 's/deb.debian.org/archive.debian.org/g' /etc/apt/sources.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY --chown=appuser:appuser . /app/
WORKDIR /app/

RUN python3 -m pip install --upgrade pip setuptools && \
    pip3 install --no-cache-dir --upgrade --requirement requirements.txt

USER appuser

CMD python3 -m ScorpiTune
