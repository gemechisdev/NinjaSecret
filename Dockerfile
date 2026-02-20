FROM nikolaik/python-nodejs:python3.11-nodejs19

# Create non-root user
RUN useradd -m -u 10014 -s /bin/bash appuser

# Remove problematic Yarn repo (prevents GPG error on old base image),
# switch old mirrors to archive.debian.org,
# comment out buster-updates if it causes 404s on archive,
# then install ffmpeg and clean up
RUN rm -f /etc/apt/sources.list.d/yarn.list \
    && sed -i 's/deb.debian.org/archive.debian.org/g' /etc/apt/sources.list \
    && sed -i 's|security.debian.org/debian-security|archive.debian.org/debian-security|g' /etc/apt/sources.list \
    && sed -i '/buster-updates/s/^/#/' /etc/apt/sources.list 2>/dev/null || true \
    && apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy app files with correct ownership
COPY --chown=appuser:appuser . /app/
WORKDIR /app/

# Upgrade pip/setuptools and install Python deps
RUN python3 -m pip install --upgrade pip setuptools && \
    pip3 install --no-cache-dir --upgrade --requirement requirements.txt

# Switch to non-root user
USER appuser

CMD ["python3", "main.py"]
