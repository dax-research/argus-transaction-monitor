from django.shortcuts import render
from django.http import Http404
from django.template import TemplateDoesNotExist
from django.conf import settings
from pathlib import Path


# Create your views here.
def home(request):
    return render(request, 'index.html')


def serve_template(request, page: str):
    """Render a frontend template by name (development only).

    Example: GET /dashboard.html -> renders 'dashboard.html' from frontend/templates.
    This view validates the filename and returns 404 on missing templates.
    """
    if not page:
        page = 'index.html'

    # Basic safety checks
    if '..' in page or page.startswith('/') or page.startswith('\\'):
        raise Http404()

    templates_dir = settings.BASE_DIR.parent / 'frontend' / 'templates'
    candidate = (templates_dir / page).resolve()

    try:
        templates_root = templates_dir.resolve()
    except Exception:
        raise Http404()

    # Ensure candidate is inside the templates directory
    if templates_root not in candidate.parents and candidate != templates_root:
        raise Http404()

    if not candidate.exists():
        raise Http404()

    try:
        return render(request, page)
    except TemplateDoesNotExist:
        raise Http404()
