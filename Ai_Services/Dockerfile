# استخدام صورة بايثون خفيفة
FROM python:3.10-slim

# ضبط مجلد العمل
WORKDIR /app

# نسخ ملف المتطلبات وتثبيتها أولاً (لتسريع عملية البناء لاحقاً)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# نسخ باقي ملفات المشروع
COPY . .

# فتح بورت 8000 للسيرفر
EXPOSE 8000

# تشغيل سيرفر FastAPI
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]