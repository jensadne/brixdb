"""
Service functions for dealing with Bricklink. Much uglyness due to Bricklink
not exposing things sensibly.
"""
from datetime import date
import html
import os
import re

from django.conf import settings

import requests

from ..models import BricklinkCategory, CatalogItem, Category, Colour, Element, Part, Set


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
    # some of the cookies seem to only be set on the first visit, so for
    # simplicity we just fetch the colours list here. In the Future(tm) we'll
    # do this properly
    fetch_colours(session=session)
    return session


class ViewType:
    CATALOG = '0'
    CATEGORIES = '2'
    COLOURS = '3'
    INVENTORY = '4'


def fetch_catalog_file(view_type, file_path, item_number='', item_type='S', item_type_inv='S', session=None):
    """
    Common handling for all catalog downloads. Downloads tab separated file
    from Bricklink, then strips and splits into lines for further handling.
    """
    session = session if session is not None else create_session()
    url = 'https://www.bricklink.com/catalogDownload.asp?a=a'
    data = {'itemNo': item_number, 'itemType': item_type, 'viewType': view_type,
            'downloadType': 'T', 'itemTypeInv': item_type_inv}
    # all CATALOG fetches we also want the extra data for
    if view_type == ViewType.CATALOG:
        data.update({'selYear': 'Y', 'selWeight': 'Y', 'selDim': 'Y'})

    response = session.post(url, data=data, headers=fake_headers(url)).text
    # Bricklink's download page is somewhat stupid, so we can't check against
    # status_code here
    if '<!doctype html>' in response[:100]:
        return False

    # store the file locally
    os.makedirs(os.path.join(settings.MEDIA_ROOT, os.path.split(file_path)[0]), exist_ok=True)
    with open(os.path.join(settings.MEDIA_ROOT, file_path), 'wb') as f:
        f.write(response.encode('utf8'))

    # there's one row of headers so slice that off, and a varying number of
    # empty lines before the data starts so get rid of those too
    lines = [l.strip().split('\t') for l in response.split('\n') if l.strip()][1:]
    return lines


def fetch_categories(session=None):
    """
    Fetch the list of Bricklink categories. These rarely change.
    """
    return fetch_catalog_file(ViewType.CATEGORIES, os.path.join('base', 'categories.txt'), session=session)


def import_categories(data=None):
    """
    Import flat list of categories, without parents since BL don't provide us
    with that information. :-(
    """
    data = data if data else fetch_categories()
    # if Bricklink has decided to hate us again there's little we can do now
    if not data:
        return False

    categories = BricklinkCategory.objects.values_list('pk', 'bl_id', 'name')
    existing = {bl_id: {'pk': pk, 'name': name} for pk, bl_id, name in categories}
    for bl_id, name in data:
        bl_id = int(bl_id)
        # there might be html entities in the name because BL
        name = html.unescape(name)
        if bl_id in existing:
            if name == existing[bl_id]['name']:
                continue
            BricklinkCategory.objects.filter(pk=existing[bl_id]['pk']).update(name=name)
        else:
            BricklinkCategory.objects.create(bl_id=bl_id, name=name)


def fetch_colours(session=None):
    """
    Fetch Bricklink's colour list. It also doesn't change much.
    """
    return fetch_catalog_file(ViewType.COLOURS, os.path.join('base', 'colours.txt'), session=session)


def import_colours(data):
    """
    Imports a tab separated colours list downloaded from Bricklink

    Headers:
    Color ID	Color Name	RGB	Type	Parts	In Sets	Wanted	For Sale	Year From	Year To
    """
    for l in data:
        colour_id, colour_name = int(l[0]), l[1]
        colour, _ = Colour.objects.update_or_create(number=colour_id, defaults={'name': colour_name})


def fetch_sets(session=None):
    """
    Fetch Bricklink's set list. It changes quite often, but checking daily
    should be enough.
    """
    return fetch_catalog_file(ViewType.CATALOG, os.path.join('base', 'sets_{date}.txt').format(date=date.today()),
                              item_type='S', session=session)


def import_sets(data):
    """
    Imports a set list downloaded from Bricklink
    """
    if not BricklinkCategory.objects.exists():
        # TODO: proper exception class here
        raise Exception("Import Bricklink's categories first!")

    # another bonkers case, BL's category names in the set list are the
    # complete branch of the tree-that-isn't-a tree, so to get our _actual_
    # category we must construct the full dotted bl_id from the category names,
    # separated by /, then and use that to find the proper category, if
    # necessary creating the whole branch

    bl_categories = {}
    for bl_id, name in BricklinkCategory.objects.values_list('bl_id', 'name'):
        bl_categories[name] = bl_id
    categories = {}
    # XXX this is not optimal, we don't actually need the whole Category object here
    for category in Category.objects.all():
        categories[category.bl_id] = category

    # TODO: find a sensible way of handling getting here with a non-existant
    # category, Which admittedly is highly unlikely if we run this as part of a
    # daily celery task, but still

    # there are certain categories where the name actually contains a forward
    # slash, which breaks the split() trick below. So to compensate for THAT
    # TOO we do more uglyness here
    weird_categories = {c.name.split(' / ')[0]: c for c in BricklinkCategory.objects.filter(name__contains=' / ')}
    for l in data:
        category_id, category_name, set_number, set_name, year, weight, dimensions = l[:7]
        names = category_name.split(' / ')

        # see if this is a weird category name that should actually include the slash
        for i, name in enumerate(names):
            if name in weird_categories:
                names.pop(i+1)
                names[i] = weird_categories[name].name

        category_name = names[-1]
        bl_ids = [bl_categories[name] for name in names]
        for i, bl_id in enumerate(bl_ids[1:]):
            bl_ids[i+1] = '{}.{}'.format(bl_ids[i], bl_id)
        category_id = bl_ids[-1]
        # ensure this whole branch exists
        categories[bl_ids[0]], _ = Category.objects.get_or_create(bl_id=bl_ids[0], defaults={'name': names[0]})
        for i, bl_id in enumerate(bl_ids[1:]):
            kw = {'bl_id': bl_id, 'name': names[i+1]}
            categories[bl_id] = categories.get(bl_id, categories[bl_ids[i]].sub_categories.create(**kw))
        # this should definitely exist now
        category = categories[category_id]
        # the set's number is least likely to change, though that _can_ also
        # happen. because BL
        weight = weight if weight != '?' else None
        year = year if year.isdigit() else None
        _set, _ = Set.objects.update_or_create(number=set_number, defaults={'name': set_name, 'category': category,
                                                                            'year_released': year, 'weight': weight,
                                                                            'dimensions': dimensions})


def import_parts(data):
    """
    Imports a tab separated part list downloaded from Bricklink

    Headers:
    Category ID	Category Name	Number	Name
    """
    for l in data:
        category_id, category_name, part_number, part_name = l[:4]
        # TODO: weight, year, etc
        category, created = Category.objects.get_or_create(bl_id=category_id, name=category_name)
        if created:
            category.save()

        part, created = Part.objects.get_or_create(category=category, number=part_number, name=part_name)
        if created:
            part.save()


def fetch_inventory(item, session=None):
    session = session if session is not None else create_session()
    inv_types = {CatalogItem.TYPE.set: 'S', CatalogItem.TYPE.gear: 'G',
                 CatalogItem.TYPE.minifig: 'M', CatalogItem.TYPE.part: 'P'}
    item_type = inv_types[item.item_type]
    return fetch_catalog_file(ViewType.INVENTORY, os.path.join('inventories', '{num}.txt').format(num=item.number),
                              item_number=item.number, item_type=item_type, item_type_inv=item_type, session=session)


def import_inventory(_set, dat):
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
