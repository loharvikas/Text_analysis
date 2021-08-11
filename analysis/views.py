from django.shortcuts import render
from django.views.generic import View
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from .main.text_analysis import analyze_text



@csrf_exempt
def text_analysis(request):
    """
        API ENDPOINT: /api/analyze-text/
    """
    if request.method == "POST":
        print("RES:", request.POST)
        content = request.body
        content = content.decode()
        if content is list:
            content = content[0]

        data, metrics = analyze_text(content)
        response = {
            "data": data,
            "metrics": metrics
        }
        return JsonResponse(response, safe=False, status=200)
    return HttpResponse("Text only, please.", content_type="text/plain")
