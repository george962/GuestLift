FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /service
COPY requirements.txt requirements.lock ./
RUN pip install --no-cache-dir -r requirements.lock
RUN useradd --system --uid 10001 --no-create-home appuser && chown appuser /service
COPY --chown=appuser:appuser . .
USER appuser
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
