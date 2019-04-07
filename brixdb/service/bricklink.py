"""
Service functions for dealing with Bricklink. Much uglyness due to Bricklink
not exposing things sensibly.
"""
from datetime import date
import html
import os
import re

from django.conf import settings
from django.db.models import F

import requests

from ..models import (BricklinkCategory, CatalogItem, Category, Colour, Element, Part, Set, Minifig,
                      ItemInventory)


def fake_headers(url):
    """
    Bricklink is stupid and thinks referrer and user-agent checks are
    worthwhile in this day and age..
    """
    return {'referrer': url, 'User-agent': 'Mozilla/5.0'}


class ViewType:
    """
    These are the various ViewTypes Bricklink's catalog download page expects.
    """
    CATALOG = '0'
    CATEGORIES = '2'
    COLOURS = '3'
    INVENTORY = '4'
    ELEMENTS = '5'


class ItemType:
    BOOK = 'B'
    GEAR = 'G'
    MINIFIG = 'M'
    PART = 'P'
    SET = 'S'


class BricklinkCatalogClient(object):
    """
    """
    session = None
    bl_categories = None
    categories = None
    weird_categories = None
    elements = None
    colours = None
    items = None

    def __init__(self):
        self.session = self.create_session()

    def create_session(self):
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
        # do this properly (maybe)
        self.session = session
        self.fetch_colours()
        return session

    def fetch_catalog_file(self, view_type, file_path, item_number='', item_type='S', item_type_inv='S'):
        """
        Common handling for all catalog downloads. Downloads tab separated file
        from Bricklink, then strips and splits into lines for further handling.
        """
        session = self.session if self.session is not None else self.create_session()
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

    def fetch_categories(self):
        """
        Fetch the list of Bricklink categories. These rarely change.
        """
        return self.fetch_catalog_file(ViewType.CATEGORIES, os.path.join('base', 'categories.txt'))

    def import_categories(self, data):
        """
        Import flat list of categories, without parents since BL don't provide us
        with that information. :-(
        """
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

    def get_category(self, category_name):
        """
        In several cases we need to do massive amounts of trickery to get the
        actual, proper Category a CatalogItem is to be placed in. This method
        is thus a bit on the ugly side.
        """
        # another bonkers case, BL's category names in several lists (at least
        # sets and minifigs) are the complete branch of the tree-that-isn't-a
        # tree, so to get our _actual_ category we must construct the full
        # dotted bl_id from the category names, separated by /, then and use
        # that to find the proper category, if necessary creating the whole
        # branch
        if self.bl_categories is None:
            self.bl_categories = {}
            for bl_id, name in BricklinkCategory.objects.values_list('bl_id', 'name'):
                self.bl_categories[name] = bl_id
            self.categories = {}
            # XXX this is not optimal, we don't actually need the whole Category object here
            for category in Category.objects.all():
                self.categories[category.bl_id] = category

            # TODO: find a sensible way of handling getting here with a
            #       non-existant category, Which admittedly is highly unlikely
            #       if we run all of import_sets, import_parts and
            #       import_minifigs as part of a daily celery task, but still

            # there are certain categories where the name actually contains a forward
            # slash, which breaks the split() trick below. So to compensate for THAT
            # TOO we do more uglyness here
            weird_cats = BricklinkCategory.objects.filter(name__contains=' / ')
            self.weird_categories = {c.name.split(' / ')[0]: c for c in weird_cats}

        # start actually doing something useful
        names = category_name.split(' / ')

        # see if this is a weird category name that should actually include the slash
        for i, name in enumerate(names):
            if name in self.weird_categories:
                names.pop(i+1)
                names[i] = self.weird_categories[name].name

        # the final word is the actual category name
        category_name = names[-1]

        # construct full dotted paths so linking to Bricklink is easier
        bl_ids = [self.bl_categories[name] for name in names]
        for i, bl_id in enumerate(bl_ids[1:]):
            bl_ids[i+1] = '{}.{}'.format(bl_ids[i], bl_id)

        # find the _actual_ category_id
        category_id = bl_ids[-1]

        # ensure this whole branch exists
        if not bl_ids[0] in self.categories:
            self.categories[bl_ids[0]] = Category.objects.create(bl_id=bl_ids[0], name=names[0])

        for i, bl_id in enumerate(bl_ids[1:]):
            kw = {'bl_id': bl_id, 'name': names[i+1]}
            if bl_id not in self.categories:
                self.categories[bl_id] = self.categories[bl_ids[i]].sub_categories.create(**kw)
            elif self.categories[bl_id].name != kw['name']:
                # TODO: here we should also handle cases of categories that now have
                #       a different parent
                Category.objects.filter(bl_id=bl_id).update(name=kw['name'])

        # this should definitely exist now
        return self.categories[category_id]

    def fetch_colours(self):
        """
        Fetch Bricklink's colour list. It also doesn't change much.
        """
        return self.fetch_catalog_file(ViewType.COLOURS, os.path.join('base', 'colours.txt'))

    def import_colours(self, data):
        """
        Imports Bricklink's list of colours

        Headers:
        Color ID	Color Name	RGB	Type	Parts	In Sets	Wanted	For Sale	Year From	Year To
        """
        for l in data:
            colour_id, colour_name = int(l[0]), l[1]
            colour, _ = Colour.objects.update_or_create(number=colour_id, defaults={'name': colour_name})

    def fetch_sets(self):
        """
        Fetch Bricklink's set list. It changes quite often, but checking daily
        should be enough.
        """
        file_name = os.path.join('base', 'sets_{date}.txt').format(date=date.today())
        return self.fetch_catalog_file(ViewType.CATALOG, file_name, item_type=ItemType.SET)

    def import_sets(self, data, item_type=Set.TYPE.set):
        """
        Imports a list of sets, gear or books downloaded from Bricklink.
        """
        if not BricklinkCategory.objects.exists():
            # TODO: proper exception class here
            raise Exception("Import Bricklink's categories first!")

        for l in data:
            category_id, category_name, set_number, set_name, year, weight, dimensions = l[:7]
            category = self.get_category(category_name)
            # the set's number is least likely to change, though that _can_ also
            # happen. because BL
            weight = weight if weight != '?' else None
            year = year if year.isdigit() else None
            _set, _ = Set.objects.update_or_create(number=set_number,
                                                   defaults={'name': set_name, 'category': category,
                                                             'weight': weight, 'year_released': year,
                                                             'dimensions': dimensions, 'item_type': item_type})

    def fetch_boooks(self):
        """
        Fetch Bricklink's book list. Like we do for gear we just treat them as
        Sets for simplicity.
        """
        file_name = os.path.join('base', 'books_{date}.txt').format(date=date.today())
        return self.fetch_catalog_file(ViewType.CATALOG, file_name, item_type=ItemType.BOOK)

    def import_books(self, data):
        """
        Books are treated as sets.
        """
        self.import_sets(data, item_type=Set.TYPE.book)

    def fetch_gear(self):
        """
        Fetch Bricklink's gear list. We'll just import them as Sets because we're lazy though
        """
        file_name = os.path.join('base', 'gear_{date}.txt').format(date=date.today())
        return self.fetch_catalog_file(ViewType.CATALOG, file_name, item_type=ItemType.GEAR)

    def import_gear(self, data):
        """
        Imports a gear list downloaded from Bricklink
        """
        self.import_sets(data, item_type=Set.TYPE.gear)

    def fetch_parts(self):
        file_name = os.path.join('base', 'parts_{date}.txt').format(date=date.today())
        return self.fetch_catalog_file(ViewType.CATALOG, file_name, item_type=ItemType.PART)

    def import_parts(self, data):
        """
        Imports a tab separated part list downloaded from Bricklink

        Headers:
        Category ID	Category Name	Number	Name    Weight  Dimensions
        """
        for category_id, category_name, number, name, weight, dimensions in data:
            weight = weight if weight != '?' else None
            defaults = {'name': name, 'category': self.get_category(category_name),
                        'weight': weight, 'dimensions': dimensions}
            part, _ = Part.objects.update_or_create(number=number, defaults=defaults)

    def fetch_minifigs(self):
        """
        Fetches the current list of minifigs from Bricklink
        """
        file_name = os.path.join('base', 'minifigs_{date}.txt').format(date=date.today())
        return self.fetch_catalog_file(ViewType.CATALOG, file_name, item_type='M')

    def import_minifigs(self, data):
        """
        Imports a list of minifigs downloaded from Bricklink

        Headers:
        Category ID	Category Name	Number	Name
        """
        for category_id, category_name, number, name, year, weight in data:
            category = self.get_category(category_name)
            # the minifig's number is least likely to change, though that _can_
            # also happen. because BL. Case in point: Star Wars figs growing an
            # extra 0 in the number when they reached 1000 figs
            weight = weight if weight != '?' else None
            year = year if year.isdigit() else None
            _mf, _ = Minifig.objects.update_or_create(number=number,
                                                      defaults={'name': name, 'category': category,
                                                                'year_released': year, 'weight': weight})

    def fetch_elements(self):
        """
        Fetches the current list of part+colour combinations from Bricklink
        """
        file_name = os.path.join('base', 'elements_{date}.txt').format(date=date.today())
        return self.fetch_catalog_file(ViewType.ELEMENTS, file_name, item_type=ItemType.SET)

    def import_elements(self, data):
        """
        Import Bricklink's list of part+colour combinations and create Elements
        for them. This needs to handle cases of multiple element-ids from TLG
        for the same part+colour combination since Bricklink doesn't consider
        those separate, and neither do we.
        """
        pass

    def fetch_inventory(self, item):
        """
        Fetches the inventory for the given CatalogItem so it can be imported
        with import_inventory().
        """
        inv_types = {CatalogItem.TYPE.set: 'S', CatalogItem.TYPE.gear: 'G',
                     CatalogItem.TYPE.minifig: 'M', CatalogItem.TYPE.part: 'P'}
        item_type = inv_types[item.item_type]
        file_name = os.path.join('inventories', '{num}.txt').format(num=item.number)
        return self.fetch_catalog_file(ViewType.INVENTORY, file_name, item_number=item.number, item_type=item_type,
                                       item_type_inv=item_type)

    def get_colour(self, number):
        """
        Not 100% if we need this, but might as well have it. Since getting an
        unknown colour out of the blue is highly unlikely we don't bother with
        clever error handling here.
        """
        if not self.colours:
            self.colours = {colour.number: colour for colour in Colour.objects.all()}
        return self.colours[int(number)]

    def get_element_key(self, number, colour):
        """
        The lookup key for elements
        """
        return '{}_{}'.format(number, colour)

    def get_element(self, number, colour):
        """
        When the item type in the inventory is ItemType.PART we actually want
        to map to an Element
        """
        if not self.elements:
            self.elements = {}
            for element in Element.objects.select_related('part', 'colour'):
                elem_key = self.get_element_key(element.part.number, element.colour.number)
                self.elements[elem_key] = element

        colour = self.get_colour(colour)
        elem_key = '{}_{}'.format(number, colour.number)
        # this on the other hand can probably happen, so we have to handle it
        element = self.elements.get(elem_key)
        if element == None:
            part = self.get_item(number, item_type=CatalogItem.TYPE.part)
            self.elements[elem_key] = element = Element.objects.get_or_create(part=part, colour=colour)[0]
        return element

    def get_item(self, number, name=None, item_type=None):
        """
        Whenever we're not adding an Element to the Item's inventory we use
        this method. Later we intend to extend this to handle lookups by name
        too, for importing Bricklink orders
        """
        if self.items is None:
            self.items = {item.number: item for item in CatalogItem.objects.all()}
        # later we might want to do this in a more sensible way..
        if item_type:
            item = self.items.get(number, None)
            if not item or item.item_type != item_type:
                fmt_kwargs = {'type': item_type, 'item': number, 'real_type': (item.item_type if item else None)}
                raise ValueError("Invalid item_type {type}! {item} is type {real_type}!".format(**fmt_kwargs))
        # this might not be good enough, but meh
        return self.items[number]

    def import_inventory(self, item, data):
        """
        Parses an inventory downloaded from Bricklink and stores it locally

        Headers:
        Type	Item No	Item Name	Qty	Color ID	Extra?	Alternate?	Match ID	Counterpart?
        """
        def make_inventory_key(item_number, colour):
            """
            This is a special case that works for all sorts of Items
            """
            return '{}_{}'.format(item_number, colour)

        item.inventory.all().delete()
        inventory = {}
        for item_type, item_number, item_name, quantity, colour, extra, alternate, match, counter in data:
            # we really don't care about the weird crap, except extras which
            # are handled below
            if counter == 'Y' or alternate == 'Y':
                continue

            quantity = int(quantity)
            inv_key = make_inventory_key(item_number, colour)
            # if this a line for an extra part we'll just add it to the one
            # we've already made since we really don't care about extras being
            # extras
            if inv_key in inventory:
                ItemInventory.objects.filter(pk=inventory[inv_key].pk).update(quantity=F('quantity')+quantity)
                continue

            kwargs = {'quantity': quantity}
            if item_type == ItemType.PART:
                kwargs['element'] = self.get_element(item_number, colour)
            else:
                kwargs['item'] = self.get_item(item_number)

            inventory[inv_key] = item.inventory.create(**kwargs)

    def parse_bricklink_order(dat):
        """
        Parses an order confirmation email from Bricklink.
        """
        order_number_re = re.compile(r'^Subject:( )*Bricklink Order #(\d+)', re.IGNORECASE)
        part_content_re = re.compile(r'^\[(?P<state>New|Used)\] (?P<part_name>.*)  \(x(?P<quantity>\d+)\)')
        set_content_re = re.compile(r'^\[(?P<state>New|Used) (?P<state2>Sealed|Complete|Incomplete)\] (?P<set_number>\d+)  \(x(?P<quantity>\d+)\)')  # noqa

        def is_set(line):
            return set_content_re.match(line)

        def is_part(line):
            return part_content_re.match(line)

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
