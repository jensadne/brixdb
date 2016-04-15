import re

from django.conf import settings

#from bricklink import ApiClient
import requests

from .models import Part, Category, Element, Set, Colour#, CatalogItem


def fetch_bricklink_inventory(_set):
    inv_types = {1: 'S', 4: 'G'}
    url = 'http://www.bricklink.com/catalogDownload.asp?a=a'
    dat = requests.post(url, data={'itemNo': _set.number, 'viewType': '4', 'downloadType': 'T', 
                                   'itemTypeInv': inv_types[_set.item_type]}, headers={'referrer': url}).text
    orgfil = open('%sset_inventories/%s.txt' % (settings.MEDIA_ROOT, _set.number), 'wb')
    orgfil.write(dat.encode('utf8'))
    orgfil.close()
    return dat 


def import_bricklink_inventory(_set, dat):
    """ 
    Parses an inventory downloaded from Bricklink and stores it locally
    """
    #_models = {'P': Part, 'S': Set, 'G': Set}

    _colours, _parts, _elements = {}, {}, {}
    for c in Colour.objects.all():
        _colours[c.number] = c
    for p in Part.objects.all():
        _parts[p.number] = p
    for e in Element.objects.all().select_related('part', 'colour'):
        _elements[e.lookup_key] = e

    _set.inventory.all().delete()

    # headers:
    # Type	Item No	Item Name	Qty	Color ID	Extra?	Alternate?	Match ID	Counterpart?
    lines = [l.strip().split('\t') for l in dat.split('\n')][2:]
    for l in lines:
        if not l or not l[0] or len(l) == 1:
            continue
        item_type, item_number, item_name, amount, colour, extra, alternate, match, counter = l
        if item_type == 'P':
            if not item_number in _parts:
               _parts[item_number] = Part.objects.create(name=item_name, number=item_number)
            p = _parts[item_number]

            colour = int(colour)
            if not colour in _colours:
                _colours[colour] = Colour.objects.create(name='Unknown colour %d' % colour, number=colour)

            elem_key = '%s_%d' % (item_number, colour)
            if not elem_key in _elements:
                _elements[elem_key] = Element.objects.create(part=p, colour=_colours[colour])
            element = _elements[elem_key]
            _set.inventory.create(element=element, amount=int(amount), is_extra=(extra == 'Y'),
                                  is_alternate=(alternate == 'Y'), is_counterpart=(counter == 'Y'),
                                  match_id=int(match))


def import_bricklink_setlist(dat):
    """
    Imports a set list downloaded from Bricklink
    """
    lines = [l.strip().split('\t') for l in dat.split('\n')][3:]
    for l in lines:
        if not l or not l[0]:
            continue
        category_id, category_name, set_number, set_name = l[:4]
        #if len(l) > 4:
        #    TODO: weight, dimensions, year released
        category, created = Category.objects.get_or_create(bl_id=category_id, name=category_name)
        if created:
            category.save()
            
        _set, created = Set.objects.get_or_create(category=category, number=set_number, name=set_name) 
        if created:
            _set.save()


def import_bricklink_partslist(dat):
    """
    Imports a tab separated part list downloaded from Bricklink

    Headers:
    Category ID	Category Name	Number	Name
    """
    lines = [l.strip().split('\t') for l in dat.split('\n')][3:]
    for l in lines:
        if not l or not l[0]:
            continue
        category_id, category_name, part_number, part_name = l[:4]
        # TODO: weight, year, etc
        category, created = Category.objects.get_or_create(bl_id=category_id, name=category_name)
        if created:
            category.save()

        part, created = Part.objects.get_or_create(category=category, number=part_number, name=part_name)
        if created:
            part.save()


def import_bricklink_colours(dat):
    """
    Imports a tab separated colours list downloaded from Bricklink

    Headers:
    Color ID	Color Name	RGB	Type	Parts	In Sets	Wanted	For Sale	Year From	Year To
    """

    lines = [l.strip().split('\t') for l in dat.split('\n')][2:]
    for l in lines:
        colour_id, colour_name = l[0], l[1]
        colour, created = Colour.objects.get_or_create(number=colour_id, name=colour_name)
        if created:
            colour.save()


order_number_re = re.compile(r'^Subject:( )*Bricklink Order #(\d+)', re.IGNORECASE)
part_content_re = re.compile(r'^\[(?P<state>New|Used)\] (?P<part_name>.*)  \(x(?P<quantity>\d+)\)')
set_content_re = re.compile(r'^\[(?P<state>New|Used) (?P<state2>Sealed|Complete|Incomplete)\] (?P<set_number>\d+)  \(x(?P<quantity>\d+)\)')  # noqa

def is_set(line):
    return set_content_re.match(line)


def is_part(line):
    return part_content_re.match(line)


def parse_bricklink_order(dat):
    """
    Parses an order confirmation email from Bricklink.
    """
    lines = dat.split('\n')
    # find order number
    order_number = None
    for line in lines:
        line_match = order_number_re.match(line)
        if line_match:
            order_number = int(line_match.groups()[1])
            break
    if not order_number:
            return False, 'invalid data, no order number'

    sets, parts = [], []

    # find start and end of order contents
    content_start, content_end = None, None
    for i, line in enumerate(lines):
        if line.startswith('Items in Order:'):
            content_start = i + 2
        if line.startswith('Buyer Information:'):
            content_end = i - 2

    if content_start is None or content_end is None:
        return False, 'invalid data, content not found'

    colours = {}
    for colour in Colour.objects.all():
        colours[colour.name] = colour

    # see what the order actually contains
    for line in lines[content_start:content_end]:
        content_match = part_content_re.match(line)
        if content_match:
            groups = content_match.groupdict()
            state, part_info, quantity = groups['state'], groups['part_info'], int(groups['quantity']) 
            colour, part_name = find_colour_part(part_info)
            try:
                part = Part.objects.get(name=part_name)
            except Part.DoesNotExist:
                print 'NOT FOUND', part_name
                continue
            #print colour, part
            elem, created = Element.objects.get_or_create(part=part, colour=colour)
            if created:
                elem.save()
            parts.append(elem)


    return {'number': number, 'parts': parts, 'sets': sets}


def import_bricklink_order(owner, dat):
    """
    Parses an order confirmation email from Bricklink and imports it as a "Set"
    owned by "owner"
    """
    cat, created = Category.objects.get_or_create(name='__Bricklink order', bl_id=9999)
    if created:
        cat.save()

    set_ = Set.objects.create(name='Bricklink order #%d' % order_number, category=cat,
                              number='__blorder%d' % order_number)
    owner.sets_owned.create(owned_set=set_)
    # XXX: store price of order?

    set_.inventory.create(element=elem, amount=quantity)

    return True, set_
