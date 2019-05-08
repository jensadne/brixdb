from django.db import transaction

from ..models import Category, Colour, Element, Part


@transaction.atomic
def import_lugbulk_order(owner, period, data):
    """
    Imports a Lugbulk order from tab separated data from Brikkelauget's Lugbulk
    system's label export.
    """
    cat = Category.objects.get_or_create(slug='lugbulk-order', defaults={'name': 'Lugbulk order', 'bl_id': '9999'})[0]
    order = owner.lugbulk_orders.create(period=period, category=cat, item_type='lugbulk_order',
                                        number='__lugbulk_order_{}_{}'.format(owner.pk, period))

    for username, partname, colour, number, quantity in data:
        colour = Colour.objects.get(name=colour)
        part = Part.objects.get(number=number)
        order.inventory.create(element=Element.objects.get_or_create(part=part, colour=colour)[0], quantity=quantity)
    owner.owned_items.create(item=order, quantity=1)
    return order
