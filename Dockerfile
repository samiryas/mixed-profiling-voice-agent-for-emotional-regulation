# 3.11: the Python the pinned requirements were frozen against, so every pin has a
# prebuilt wheel. Newer bases break the build:
#   - 3.13 -> bleak==0.22.0 requires Python <3.13
#   - 3.12 -> pandas==2.0.0 / numpy==1.24.0 have no 3.12 wheels and fail to build from source
# (bleak/pandas/numpy/matplotlib are the HRV-pipeline pins; see the requirements-split follow-up.)
FROM python:3.11

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN addgroup --system -uid 10000 app && adduser --system --group --home /app -uid 10000 app && chown -R app /app
USER 10000

EXPOSE 8000
CMD ["otree", "prodserver", "8000"]