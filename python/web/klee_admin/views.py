from django.shortcuts import render
from decorators import group_required


@group_required("admin")
def home(request):
    return render(request, "klee_admin/index.html")
