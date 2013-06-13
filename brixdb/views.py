import json

from django.http import HttpResponse
from django.shortcuts import render
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext as _
from django.views.decorators.http import require_POST

from brixdb.forms import SimpleIntegerForm


def render_json(request, context):
    return HttpResponse(json.dumps(context))


def part_index(request, number):
    template, c = 'brixdb/part_index.html', {}
    return render(request, template, c)


def colour_detail(request, colour_number):
	pass


@require_POST
def add_set_owned(request, set_number):
    _set = get_object_or_404(Set, number=set_number)
    f = SimpleIntegerForm(request.POST)
    if not f.is_valid():
        return render_json_error(request, {'result': _('Invalid input data')})

    return render_json(request, {'result': _('You now own %d of this set') % request.user.sets_owned.filter(owned_set=_set).count()})
