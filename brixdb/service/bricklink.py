"""
Service functions for dealing with Bricklink. Much uglyness due to Bricklink
not exposing things sensibly.
"""
from datetime import date
import os
import re

from django.conf import settings

import requests

from ..models import Part, Category, Element, Set, Colour, CatalogItem


def fake_headers(url):
    """
    Bricklink is stupid and thinks referrer and user-agent checks are
    worthwhile in this day and age..
    """
    return {'referrer': url, 'User-agent': 'Mozilla/5.0'}


def create_session():
    """
    Since downloading Bricklink's catalog now requires a valid user session we
    must create one.
    """
    url = 'https://www.bricklink.com/ajax/renovate/loginandout.ajax'
    session = requests.Session()
    data = {'userid': settings.BRICKLINK_USERNAME, 'password': settings.BRICKLINK_PASSWORD, 
            'keepme_loggedin': False, 'mid': '168ceb4f73700000-a25f3a8ad3ebeb5f',
            'pageid': 'MAIN'}
    session.post(url, data, headers=fake_headers(url))
    return session


def fetch_categories(session=None):
    """
    Fetch the list of Bricklink categories. These rarely change.
    """
    session = session if session is not None else create_session()

    url = 'https://www.bricklink.com/catalogDownload.asp?a=a'

    # viewType 2 == categories
    data = {'itemNo': '', 'itemType': 'S', 'viewType': '2', 'downloadType': 'T', 'itemTypeInv': 'S'}
    response = session.post(url, data=data, headers=fake_headers(url)).text
    # Bricklink's download page is somewhat stupid, so we can't check against
    # status_code here
    if '<!doctype html>' in response[:100]:
        return False
    os.mkdirs(os.path.join(settings.MEDIA_ROOT, 'base'))
    with open(os.path.join(settings.MEDIA_ROOT, 'base', 'categories.txt'), 'wb') as f:
        f.write(response.encode('utf8'))
    return response


def import_categories(data=None):
    """
    Import flat list of categories, without parents since BL don't provide us
    with that information. :-(
    """
    data = data if data else fetch_categories()
    # if Bricklink has decided to hate us again there's little we can do now
    if not data:
        return False
    # there's one row of headers so slice that off
    lines = [l.strip().split('\t') for l in data.split('\n') if l.strip()][1:]
    categories = Category.objects.values_list('pk', 'bl_id', 'name')
    existing = {bl_id: {'pk': pk, 'name': name} for pk, bl_id, name in categories}
    for bl_id, name in lines:
        bl_id = int(bl_id)
        if bl_id in existing:
            if name == existing[bl_id]['name']:
                continue
            Category.objects.filter(pk=existing[bl_id]['pk']).update(name=name)
        else:
            Category.objects.create(bl_id=bl_id, name=name)


def fetch_bricklink_inventory(item, session=None):
    session = session if session is not None else create_session()
    inv_types = {CatalogItem.TYPE.Set: 'S', CatalogItem.TYPE.gear: 'G',
                 CatalogItem.TYPE.minifig: 'M', CatalogItem.TYPE.part: 'P'}
    url = 'https://www.bricklink.com/catalogDownload.asp?a=a'
    dat = requests.post(url, data={'itemNo': item.number, 'viewType': '4', 'downloadType': 'T', 
                                   'itemTypeInv': inv_types[item.item_type]},
                        headers={'referrer': url, 'User-agent': 'Mozilla/5.0'}).text
    # Bricklink's download page is somewhat stupid, so we can't check against
    # status_code here
    if '<!doctype html>' in dat[:100]:
        return False
    os.mkdirs(os.path.join(settings.MEDIA_ROOT, 'inventories'))
    with open(os.path.join(settings.MEDIA_ROOT, 'inventories', '{}.txt'.format(item.number)), 'wb') as f:
        f.write(dat.encode('utf8'))
    return dat


def import_bricklink_inventory(_set, dat):
    """ 
    Parses an inventory downloaded from Bricklink and stores it locally
    """
    #_models = {'P': Part, 'S': Set, 'G': Set, 'M': Minifig}

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
                print('NOT FOUND', part_name)
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
