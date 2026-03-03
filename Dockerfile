FROM python:3.13

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN addgroup --system -uid 10000 app && adduser --system --group --home /app -uid 10000 app && chown -R app /app
USER 10000

EXPOSE 8000
CMD ["otree", "prodserver", "8000"]