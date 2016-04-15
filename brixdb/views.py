from django.http import JsonResponse
from django.shortcuts import render
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext as _
from django.views.generic.detail import DetailView
from django.views.decorators.http import require_POST

from .forms import SimpleIntegerForm
from .models import Colour, Element, Set


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
            owned = self.kwargs.get('owned', True)
            context['owned_parts'] = Element.objects.by_colour(object).for_user(self.request.user, owned=owned
                                            ).select_related('part').order_by('part__name')
        return context


@require_POST
def add_set_owned(request, set_number):
    _set = get_object_or_404(Set, number=set_number)
    f = SimpleIntegerForm(request.POST)
    if not f.is_valid():
        return JsonResponse({'result': _('Invalid input data')}, status_code=400)
    return JsonResponse({'result': _('You now own %d of this set') % request.user.sets_owned.filter(owned_set=_set).count()})


class SetView(DetailView):
    model = Set
    template_name = 'brixdb/set_detail.html'
    context_object_name = 'set'
    slug_field = 'number'

    def get_context_data(self, object):
        context = super(SetView, self).get_context_data(object=object)
        context['inventory'] = object.inventory.select_related('element', 'element__part', 'element__colour')
        return context
