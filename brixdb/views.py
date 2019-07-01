from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext as _
from django.views.generic.detail import DetailView
from django.views.decorators.http import require_POST

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from . import serializers
from .forms import SimpleIntegerForm
from .models import Colour, Element, Set, Part
from .service import bricklink, bricksnpieces


import q

class SetViewSet(viewsets.ReadOnlyModelViewSet):
    lookup_field = 'number'
    queryset = Set.objects.all()
    serializer_class = serializers.SetSerializer


class PartViewSet(viewsets.ReadOnlyModelViewSet):
    lookup_field = 'number'
    queryset = Part.objects.all().prefetch_related('elements', 'elements__colour')
    serializer_class = serializers.PartDetailSerializer


class ColourViewSet(viewsets.ReadOnlyModelViewSet):
    lookup_field = 'slug'
    queryset = Colour.objects.all()
    serializer_class = serializers.ColourSerializer


class ElementViewSet(viewsets.ReadOnlyModelViewSet):
    lookup_field = 'pk'
    queryset = Element.objects.all()
    serializer_class = serializers.ElementSerializer

    @action(methods=['get'], detail=False, permission_classes=[IsAuthenticated])
    def owned(self, request):
        elements = Element.objects.owned_by(request.user).select_related('part', 'colour')
        serializer = self.get_serializer(elements, many=True)
        return Response(serializer.data)

    # TODO: ensure we can get a pk from frontend and make this a detail action
    @action(methods=['get'], detail=False, permission_classes=[IsAuthenticated])
    def bricklink_prices(self, request):
        """
        Fetch cheapest price from Bricklink for the given Element.
        """
        element = get_object_or_404(self.queryset, lego_ids__contains=q(int(request.query_params.get('element', 0))))
        prices = bricklink.get_element_prices(element)
        # we only care about the cheapest for this check
        return Response(prices[0])

    # TODO: ensure we can get a pk from frontend and make this a detail action
    @action(methods=['get'], detail=False, permission_classes=[IsAuthenticated])
    def bricksnpieces_prices(self, request):
        """
        Fetch B&P price for the given Element
        """
        element = get_object_or_404(self.queryset, lego_ids__contains=q(int(request.query_params.get('element', 0))))
        price = bricksnpieces.get_element_prices(element)
        return Response(price)


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
