from django.shortcuts import render, redirect
from django.contrib import messages
from django.views.generic.list import ListView
from forms import ConferenceForm, ConferenceFieldNamesForm
from .serializers import serialize_conference

from modularodm.exceptions import ModularOdmException

from website.conferences.model import Conference


def create_conference(request):
    if request.user.is_staff:
        conf_form = ConferenceForm(request.POST or None)
        conf_field_names_form = ConferenceFieldNamesForm(request.POST or None)
        if request.POST and conf_form.is_valid():
            conf = Conference(
                name=request.POST['name'],
                endpoint=request.POST['endpoint'],
                info_url=request.POST['info_url'],
                logo_url=request.POST['logo_url'],
                active=request.POST.get('active', True),
                public_projects=request.POST.get('public_projects', True),
                poster=request.POST.get('poster', True),
                talk=request.POST.get('talk', True),
            )
            # Todo: implement overriding default fieldnames
            # if (conf_field_names_form.has_changed):
            #   conf.field_names.update(custom_fields)
            try:
                conf.save()
            except ModularOdmException:
                print('failed')
            else:
                print('success')
                messages.success(request, 'success')
            return redirect('conferences:create_conference')
        else:
            context = {'conf_form': conf_form, 'conf_field_names_form': conf_field_names_form}
            return render(request, 'conferences/create_conference.html', context)
    else:
        messages.error(request, 'You do not have permission to access that page.')
        return redirect('auth:login')


class ConferenceList(ListView):
    template_name = 'conferences/conference_list.html'
    paginate_by = 10
    paginate_orphans = 1
    ordering = 'endpoint'
    context_object_name = 'conference'

    def get_queryset(self):
        return Conference.find().sort(self.ordering)

    def get_context_data(self, **kwargs):
        query_set = kwargs.pop('object_list', self.object_list)
        page_size = self.get_paginate_by(query_set)
        paginator, page, query_set, is_paginated = self.paginate_queryset(
            query_set, page_size)
        return {
            'conferences': map(serialize_conference, query_set),
            'page': page,
        }


def conference_update_view(request, endpoint):
    conference_instance = Conference.load(endpoint)
    conf_form = ConferenceForm(request.POST or None)
    conf_field_names_form = ConferenceFieldNamesForm(request.POST or None)
    if request.POST and conf_form.is_valid():
        # Todo: implement updating only edited fields
        # setattr(conference_instance, key, value)
        # try:
        #     conference_instance.save()
        # except ModularOdmException:
        #     print('failed')
        # else:
        #     print('success')
        return redirect('conferences:conference', endpoint=endpoint)
    context = {
        'conf_form': conf_form,
        'conf_field_names_form': conf_field_names_form,
        'endpoint': conference_instance.endpoint,
    }
    return render(request, 'conferences/conference_update_view.html', context)
