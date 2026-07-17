FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Fail the image build immediately when the migration graph or mandatory
# Sprint 8B API route package is incomplete.
RUN python scripts/verify_alembic_revision.py
RUN python scripts/verify_sprint_8b_routes.py
RUN chmod +x render-start.sh

EXPOSE 10000
CMD ["sh", "render-start.sh"]
