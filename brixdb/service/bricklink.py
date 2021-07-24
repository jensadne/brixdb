"""
Service functions for dealing with Bricklink. Much uglyness due to Bricklink
not exposing things sensibly.
"""
import email
import html
import imaplib
import os
import re
from datetime import date

from django.conf import settings
from django.db.models import F, Q
from django.template.defaultfilters import slugify

import requests

from ..models import (BricklinkCategory, CatalogItem, Category, Colour, Element, Part, Set, Minifig,
                      ItemInventory)

# Bricklink have at some point changed the syntax for the order
# confirmation subject, so we must look for both variations to get the
# order id from the subject
order_number_old_re = re.compile(r'^BrickLink Order #(\d+) - ', re.IGNORECASE)
order_number_new_re = re.compile(r'^Order Confirmed: .*\((\d+)\)', re.IGNORECASE)


def fake_headers(url):
    """
    Bricklink does referrer and user-agent checks so we need to fake those.
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


item_type_mapper = {ItemType.BOOK: CatalogItem.TYPE.book, ItemType.GEAR: CatalogItem.TYPE.gear,
                    ItemType.MINIFIG: CatalogItem.TYPE.minifig, ItemType.PART: CatalogItem.TYPE.part,
                    ItemType.SET: CatalogItem.TYPE.set}


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
        data = {'userid': settings.BRIXDB['BRICKLINK_USERNAME'], 'password': settings.BRIXDB['BRICKLINK_PASSWORD'],
                'keepme_loggedin': False, 'mid': '168ceb4f73700000-a25f3a8ad3ebeb5f', 'pageid': 'MAIN'}
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
        lines = [line.strip().split('\t') for line in response.split('\n') if line.strip()][1:]
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
        # dotted bl_id from the category names, separated by /, and then use
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
        for line in data:
            colour_id, colour_name = int(line[0]), line[1]
            Colour.objects.update_or_create(number=colour_id, defaults={'name': colour_name})

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

        for line in data:
            category_id, category_name, set_number, set_name, year, weight, dimensions = line[:7]
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
            defaults = {'name': name[:256], 'category': self.get_category(category_name),
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

    def import_elements(self, data, blacklist=None):
        """
        Import Bricklink's list of part+colour combinations and create Elements
        for them. This needs to handle cases of multiple element-ids from TLG
        for the same part+colour combination since Bricklink doesn't consider
        those separate, and neither do we.
        """
        # BL have in their infinite wisdom decided to have some minifigs in the
        # list of elements..
        blacklist = blacklist if blacklist else {}
        colours = {c.name: c for c in Colour.objects.all()}
        elements = {}
        for element in Element.objects.select_related('colour', 'part'):
            for element_id in element.lego_ids:
                elements[element_id] = element
        for part_number, colour_name, element_id in data:
            if part_number in blacklist:
                continue
            element_id = int(element_id)
            element = elements.get(element_id)
            if element and element.part.number == part_number and element_id in element.lego_ids:
                continue
            element = self.get_element(part_number, colours[colour_name].number)
            element.lego_ids.append(element_id)
            element.save()

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

    def get_colour(self, number=None, name=None):
        """
        Not 100% if we need this, but might as well have it. Since getting an
        unknown colour out of the blue is highly unlikely we don't bother with
        clever error handling here.
        """
        if not self.colours:
            self.colours = {}
            for colour in Colour.objects.all():
                self.colours[colour.number] = colour
                self.colours[colour.name] = colour
        # NOTE: we crash here if given an invalid number, while lookups by name
        #       are allowed to fail.
        return self.colours[int(number)] if number is not None else self.colours.get(name, None)

    def get_element_key(self, number, colour):
        """
        The lookup key for elements
        """
        return '{}_{}'.format(number, colour)

    def get_element(self, number=None, colour=None, element_id=None):
        """
        When the item type in the inventory is ItemType.PART we actually want
        to map to an Element
        """
        if not self.elements:
            self.elements = {}
            self.elements_by_id = {}
            for element in Element.objects.select_related('part', 'colour'):
                elem_key = self.get_element_key(element.part.number, element.colour.number)
                self.elements[elem_key] = element
                # map lego ids to elements as well
                for id_ in element.lego_ids:
                    # this shouldn't be necessary, but BL has some duplicated ids :-/
                    # TODO: find those and blacklist them in import_elements()
                    if id_ not in self.elements_by_id:
                        self.elements_by_id[id_] = element

        if element_id:
            # if we didn't have the element mapped already we most likely must
            # create it, that is easier to do outside this method
            return self.elements_by_id.get(int(element_id), None)

        colour = self.get_colour(colour)
        elem_key = '{}_{}'.format(number, colour.number)
        # this on the other hand can probably happen, so we have to handle it
        element = self.elements.get(elem_key)
        if element is None:
            part = self.get_part(number)
            self.elements[elem_key] = element = Element.objects.get_or_create(part=part, colour=colour)[0]
        return element

    def get_minifig(self, number=None, name=None):
        return self.get_item(CatalogItem.TYPE.minifig, number=number, name=name)

    def get_part(self, number=None, name=None, tlg_name=None):
        return self.get_item(CatalogItem.TYPE.part, number=number, name=name, tlg_name=tlg_name)

    def get_set(self, number=None, name=None):
        return self.get_item(CatalogItem.TYPE.set, number=number, name=name)

    def get_item(self, item_type, number=None, name=None, tlg_name=None):
        """
        Whenever we're not adding an Element to the Item's inventory we use
        this method. Later we intend to extend this to handle lookups by name
        too, for importing Bricklink orders.
        """
        # later we might want to do this in a more sensible way..
        if self.items is None:
            self.items = {}
            for item in CatalogItem.objects.all():
                self.items['{}_{}'.format(item.item_type, item.number)] = item
                self.items['{}_{}'.format(item.item_type, slugify(item.name))] = item
                for other_name in item.other_names:
                    self.items['{}_{}'.format(item.item_type, slugify(other_name))] = item
                # if the item has a TLG name we'll map that as well
                if item.tlg_name:
                    self.items['{}_{}'.format(item.item_type, slugify(item.tlg_name))] = item

        # TODO: item_type kwarg really must be required for this to work
        key = '{}_{}'.format(item_type, (number if number else slugify(name)))
        item = self.items.get(key, None)
        if not item:
            # we allow failures when doing lookup by name, this because we
            # can't know how many words of a line in an email from Bricklink
            # actually are the item name
            if name or tlg_name:
                return None
            # try doing an extra lookup in case the item is of a different type?
            raise ValueError("Invalid number {num} for item_type {typ}!".format(num=number, typ=item_type))
        else:
            self.items[key] = item
        return self.items[key]

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

        # ensure we get a fresh copy
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
                kwargs['item'] = self.get_item(item_type=item_type_mapper[item_type], number=item_number)
            inventory[inv_key] = item.inventory.create(**kwargs)

    def parse_bricklink_order_email(self, msg):
        """
        Parses an order confirmation email from Bricklink, `msg` should be a
        Message object from Python's email package.
        """
        # Subject:( )*Bricklink Order #(\d+)', re.IGNORECASE)

        # all lines for order content, regardless of type, starts with either "[New" or "[Used"
        is_content_re = re.compile(r'^\[(New|Used)', re.IGNORECASE)
        part_content_re = re.compile(r'^\[(?P<state>New|Used)\] (?P<part_name>.*)  \(x(?P<quantity>\d+)\)')
        set_content_re = re.compile(r'^\[(?P<state>New|Used) (?P<state2>Sealed|Complete|Incomplete)\] (?P<set_number>\S+)  \(x(?P<quantity>\d+)\)')  # noqa

        def is_set(line):
            return set_content_re.match(line)

        def is_part(line):
            return part_content_re.match(line)

        def is_gear(line):
            return False

        def is_minifig(colour_and_item):
            """
            Determine if the given colour_and_item string (which usually is a
            colour and a part name) is most likely to be a Minifig.
            """
            tokens = colour_and_item.split(' ')
            # If there isn't a Colour that has, or has had, a name that starts
            # with the first word we can safely assume this isn't a Colour and
            # try to treat it as a Minifig. This obviously won't work for
            # content lines that are sets, but they should already be handled
            # by the time we check for minifigs.
            if not Colour.objects.filter(Q(name__istartswith=tokens[0]) |
                                         Q(other_names__0__istartswith=tokens[0])).exists():
                return True

            # TODO: do copious amounts of magic to determine whether a line is
            #       a part with colour, or a minifig with a name that starts
            #       with a valid colour name, such as "Black Widow".
            return False

        # find order number
        order_number = None
        subject = str(msg['Subject'])
        old_match, new_match = order_number_old_re.match(subject), order_number_new_re.match(subject)
        if old_match:
            order_number = int(old_match.groups()[0])
        elif new_match:
            order_number = int(new_match.groups()[0])
        else:
            # TODO: error handling
            return False, 'invalid data, no order number'

        # time to start parsing the payload
        content_lines = []
        lines = msg.get_payload().split('\n')
        for line in lines:
            if is_content_re.match(line):
                content_lines.append(line)
        print('Order {}: {} content lines'.format(order_number, len(content_lines)))

        sets, parts, minifigs = [], [], []
        for line in content_lines:
            # print(line)
            # first see if it's looks like a Set as that's easiset to handle
            set_match = is_set(line)
            # print('Set match:', bool(set_match))
            if set_match:
                groups = set_match.groupdict()
                state, number, quantity = groups['state'], groups['set_number'], int(groups['quantity'])
                sets.append(self.get_set(number=number))
                continue

            # evidently not a Set, see if it's a Part instead (which might also
            # be a Minifig because Bricklink)
            part_match = is_part(line)
            # print('Part match:', bool(part_match))
            if part_match:
                groups = part_match.groupdict()
                state, colour_and_item, quantity = groups['state'], groups['part_name'], int(groups['quantity'])
                if is_minifig(colour_and_item):
                    minifigs.append((self.get_minifig(name=colour_and_item), quantity))
                    continue

                # we have concluded that this must be a Part, so we must find
                # the colour and part name
                # print(f'State: {state}\nPart: {colour_and_item}\nQuantity: {quantity}\n\n')
                colour, part_name, tokens, part_offset, part = None, '', colour_and_item.split(' '), 0, None
                # print(tokens)
                colour_name = tokens[0]
                for i, token in enumerate(tokens[1:]):
                    # add the next token to colour_name until we find a Colour
                    colour = self.get_colour(name=colour_name)
                    if colour:
                        # if we have found a valid colour we stop looking for
                        # colour and save the position for starting to look for
                        # the Part in the next loop
                        part_offset = i + 1
                        break
                    colour_name += (' {}'.format(token))

                # if we've gotten here without finding a colour something is very wrong
                if not colour:
                    return False, 'invalid line encountered, colour name: {}'.format(colour_name)

                # then we look for a part in the remaining tokens
                tokens = tokens[part_offset:]
                while tokens:
                    # we start by looking for the whole remainder as a part
                    # name and cut off one word each iteration until we find
                    # something. in most cases we'll find it on the first
                    # lookup so this isn't as stupid as it looks.
                    part_name = ' '.join(tokens)
                    # print(part_name)
                    part = self.get_part(name=part_name)
                    if part:
                        break
                    tokens.pop(-1)

                if part:
                    element = self.get_element(number=part.number, colour=colour.number)
                    parts.append((element, quantity))
                else:
                    # TODO: handle unknown parts
                    print(f'Content not found: {line}')

        return True, {'order_number': order_number, 'parts': parts, 'sets': sets, 'minifigs': minifigs}

    def import_bricklink_order(owner, number, parts, sets):
        """
        Parses an order confirmation email from Bricklink and imports it as a "Set"
        owned by "owner"
        """
        cat = Category.objects.get_or_create(name='__Bricklink order', bl_id=9999)[0]
        set_ = Set.objects.create(name='Bricklink order #{}'.format(number), category=cat,
                                  number='__blorder%d' % number)
        owner.sets_owned.create(owned_set=set_)
        # XXX: store price of order?
        for element, quantity in parts:
            set_.inventory.create(element=element, amount=quantity)
        return True, set_


def get_store_inventory(username):
    """
    Fetches the inventory of the Bricklink store with the given username.
    """
    # 1: fetch the whole store front (because BL sucks)
    front_url = 'https://store.bricklink.com/{username}#/shop?o={opts}'.format(username=username,
                                                                               opts='{%22showHomeItems%22:1}')
    headers = fake_headers(front_url)
    r = requests.get(front_url, headers=headers)
    if r.status_code != 200:
        return []
    # 2: find the JavaScript blob with the store config
    t = r.text
    base_idx = t.index('var StoreFront = {}')
    start = t.find('StoreFront.store', base_idx, len(t))
    end = t.find('StoreFront.user', base_idx, len(t))
    jsblob = t[start:end]
    # 3: find the actual store id
    id_start = jsblob.find('id: ')
    id_end = jsblob.find(',', id_start, -1)
    store_id = jsblob[id_start:id_end].replace('id:', '').replace(' ', '').replace('\t', '')

    # 4: do a number of fetches to get the whole parts inventory (we ignore
    # other item types for now)
    all_items = []
    inventory_url = 'https://store.bricklink.com/ajax/clone/store/searchitems.ajax?pgSize=100&itemType=P&showHomeItems=0&sid={store_id}'.format(store_id=store_id)  # noqa
    r = requests.get(inventory_url, headers=headers)
    if r.status_code != 200:
        return all_items
    groups = r.json()['result']['groups']
    total = groups[0]['total']
    all_items = groups[0]['items']
    # calculate number of pages and do all the remaining fetches
    pages = total / 100
    pages = int(pages) + (1 if pages - int(pages) else 0)
    if not all_items or pages <= 1:
        return all_items

    for i in range(2, pages+1):
        r = requests.get(inventory_url+('&pg={}'.format(i)), headers=headers)
        if r.status_code != 200:
            return all_items
        groups = r.json()['result']['groups']
        all_items.extend(groups[0]['items'])
    return all_items


def get_element_prices(element, desired_quantity=1):
    """
    Fetches price information for the given Element from Bricklink
    """
    part, colour = element.part, element.colour
    base_url = 'https://www.bricklink.com/v2/catalog/catalogitem.page?P={number}'.format(number=part.number)
    headers = fake_headers(base_url)
    # 0: find bl_id for the part if we don't have it already
    if not element.part.bl_id:
        response = requests.get(base_url, headers=headers)
        if response.status_code != 200:
            return []
        match = re.search(r'var\s+_var_item\s+=\s+{\s+idItem:\s+(\d+)', response.text)
        if not match:
            return []
        part.bl_id = match.groups()[0]
        part.save()

    prices_url = 'https://www.bricklink.com/ajax/clone/catalogifs.ajax?itemid={item_id}&color={colour_id}&iconly=0'
    response = requests.get(prices_url.format(item_id=part.bl_id, colour_id=colour.number), headers=headers)
    if response.status_code != 200:
        return []
    items = response.json()['list']
    return [{'price': float(item['mDisplaySalePrice'].split(' ')[1]), 'storeName': item['strStorename'],
             'country': item['strSellerCountryCode'],
             'storeUsername': item['strSellerUsername'], 'quantity': item['n4Qty']} for item in items]


def fetch_bricklink_emails():
    """
    Fetch Bricklink order confirmation emails for import.
    """
    imap = imaplib.IMAP4_SSL(settings.BRIXDB['IMAP_HOST'])
    try:
        r, data = imap.login(settings.BRIXDB['IMAP_USERNAME'], settings.BRIXDB['IMAP_PASSWORD'])
    except imaplib.IMAP4.error:
        print("IMAP login failed, giving up.")
        return

    r, data = imap.select(settings.BRIXDB['IMAP_FOLDER'])
    r, data = imap.search(None, 'ALL')
    messages = data[0].split(b' ')
    ret = []
    for message_id in messages:
        r, data = imap.fetch(message_id, '(RFC822)')
        msg = email.message_from_bytes(data[0][1])
        subject = str(msg['Subject'])
        if order_number_old_re.match(subject) or order_number_new_re.match(subject):
            ret.append(msg)
    return ret
