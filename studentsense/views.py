from pathlib import Path

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render


def offline_page(request):
    return render(request, 'offline.html')


def service_worker_js(request):
    service_worker_path = Path(settings.BASE_DIR) / 'static' / 'sw.js'
    content = service_worker_path.read_text(encoding='utf-8')
    return HttpResponse(content, content_type='application/javascript')
