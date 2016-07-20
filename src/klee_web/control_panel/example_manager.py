from django.core.urlresolvers import reverse_lazy, reverse
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.generic import ListView, CreateView, UpdateView, DeleteView

from control_panel.decorators import group_required
from frontend.models import File, Project


class AdminRequiredMixin(object):
    @method_decorator(group_required("admin"))
    def dispatch(self, request, *args, **kwargs):
        return super(AdminRequiredMixin, self).dispatch(request, *args,
                                                        **kwargs)


class ProjectListView(AdminRequiredMixin, ListView):
    model = Project
    template_name = 'control_panel/example_manager/project/list.html'
    context_object_name = 'examples'
    queryset = Project.objects.filter(example=True)


class ProjectCreateView(AdminRequiredMixin, CreateView):
    model = Project
    template_name = 'control_panel/example_manager/project/form.html'
    fields = ['name']
    success_url = reverse_lazy('control_panel:example_project_list')

    def form_valid(self, form):
        instance = form.save(commit=False)
        instance.example = True
        instance.save()
        return HttpResponseRedirect(self.success_url)


class ProjectUpdateView(AdminRequiredMixin, UpdateView):
    model = Project
    template_name = 'control_panel/example_manager/project/form.html'
    fields = ['name']
    success_url = reverse_lazy('control_panel:example_project_list')


class ProjectDeleteView(AdminRequiredMixin, DeleteView):
    model = Project
    template_name = 'control_panel/example_manager/delete.html'
    success_url = reverse_lazy('control_panel:example_project_list')


class FileCreateView(AdminRequiredMixin, CreateView):
    model = File
    template_name = 'control_panel/example_manager/file/form.html'
    fields = ['name', 'code', 'num_files', 'size_files', 'size_sym_in',
              'min_sym_args', 'max_sym_args', 'size_sym_args']

    def get_success_url(self):
        project_pk = self.kwargs['project_pk']
        return reverse('control_panel:example_project_update',
                       args=(project_pk,))

    def form_valid(self, form):
        instance = form.save(commit=False)
        instance.project_id = self.kwargs['project_pk']
        instance.save()
        return HttpResponseRedirect(self.get_success_url())


class FileUpdateView(AdminRequiredMixin, UpdateView):
    model = File
    template_name = 'control_panel/example_manager/file/form.html'
    fields = ['name', 'code', 'num_files', 'size_files', 'size_sym_in',
              'min_sym_args', 'max_sym_args', 'size_sym_args']

    def get_success_url(self):
        project_pk = self.kwargs['project_pk']
        return reverse('control_panel:example_project_update',
                       args=(project_pk,))


class FileDeleteView(AdminRequiredMixin, DeleteView):
    model = File
    template_name = 'control_panel/example_manager/delete.html'

    def get_success_url(self):
        project_pk = self.kwargs['project_pk']
        return reverse('control_panel:example_project_update',
                       args=(project_pk,))


def make_default_file(request, project_pk, pk):
    project = get_object_or_404(Project, pk=project_pk)
    file_obj = get_object_or_404(File, pk=pk)

    project.default_file = file_obj
    project.save()

    return HttpResponseRedirect(reverse('control_panel:example_project_update',
                                        args=(project_pk,)))
