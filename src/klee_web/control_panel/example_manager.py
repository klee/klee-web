from django.core.urlresolvers import reverse_lazy
from django.views.generic import ListView, UpdateView, CreateView, DeleteView
from frontend.models import Example


class ExampleListView(ListView):
    model = Example
    template_name = 'control_panel/example_manager/list.html'
    context_object_name = 'examples'


class ExampleCreateView(CreateView):
    model = Example
    template_name = 'control_panel/example_manager/create.html'
    success_url = reverse_lazy('control_panel:example_list')


class ExampleUpdateView(UpdateView):
    model = Example
    template_name = 'control_panel/example_manager/create.html'
    success_url = reverse_lazy('control_panel:example_list')


class ExampleDeleteView(DeleteView):
    model = Example
    template_name = 'control_panel/example_manager/delete.html'
    success_url = reverse_lazy('control_panel:example_list')
