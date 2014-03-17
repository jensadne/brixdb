import json

from django.http import HttpResponse
from django.shortcuts import render
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext as _
from django.views.generic.detail import DetailView
from django.views.decorators.http import require_POST

from .forms import SimpleIntegerForm
from .models import Colour, ItemElement, Set


def render_json(request, context):
    return HttpResponse(json.dumps(context))


def part_index(request, number):
    template, c = 'brixdb/part_index.html', {}
    return render(request, template, c)


class ColourDetail(DetailView):
    template_name = 'brixdb/colour_detail.html'
    model = Colour

    def get_context_data(self, object):
        context = super(ColourDetail, self).get_context_data()
        #context['colour'] = colour = get_object_or_404(Colour, slug=self.kwargs['slug'])
        if self.request.user.is_authenticated():
            context['owned_parts'] = ItemElement.objects.filter(element__colour=object,
                                            item__in=self.request.user.sets_owned.values_list('owned_set', flat=True)
                                            ).select_related('element', 'element__part', 'item'
                                            ).order_by('element__part__name')
        return context


@require_POST
def add_set_owned(request, set_number):
    _set = get_object_or_404(Set, number=set_number)
    f = SimpleIntegerForm(request.POST)
    if not f.is_valid():
        return render_json_error(request, {'result': _('Invalid input data')})

    return render_json(request, {'result': _('You now own %d of this set') % request.user.sets_owned.filter(owned_set=_set).count()})
