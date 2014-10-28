from django.shortcuts import render

from forms import SubmitJobForm

from worker.worker import submit_code


def index(request):
    if request.method == "POST":
        form = SubmitJobForm(request.POST, request.FILES)
        if form.is_valid():
            code = form.cleaned_data["code"]
            email = form.cleaned_data["email"]
            args = form.cleaned_data["args"]

            uploaded_file = request.FILES.get('file')
            if uploaded_file:
                code = uploaded_file.read()

            task = submit_code.delay(code, email, args)

            result = submit_code.AsyncResult(task.task_id).get(timeout=30.0)
            return render(request, "klee_web/result.html", {
                "result": result
            })
    else:
        form = SubmitJobForm()
    return render(request, "klee_web/index.html", {"form": form})
