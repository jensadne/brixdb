from ..models import Set, Minifig


def parse_brickset_file(data):
    """
    Brickset's exported tab-separated files are slightly more sane than
    Bricklink's.
    """
    d = [l.strip().split('\t') for l in data.split('\n') if l.strip()]
    # there have been some issues with not enough columns always, so slicing to
    # 18 at most seems to work well enough
    headers = d.pop(0)[:18]
    out = []
    for l in d:
        out.append({h: l[i] for i, h in enumerate(headers)})
    return out


def import_brickset_sets(owner, data, ignore_missing=True):
    """
    Imports an exported tab-separated file from Brickset with sets, and set
    shem as owned by the given User.
    """
    all_sets = {(s.brickset_id if s.brickset_id else s.number): s for s in Set.objects.all()}
    sets = parse_brickset_file(data)
    not_found = []
    # validate that everything can be imported, if we're not just skipping those
    for line in sets:
        if l['Number'] not in all_sets:
            not_found.append(l)
    # TODO: decide how to handle this
    if not_found and not ignore_missing:
        return False

    # do the actual import
    imported = 0
    for line in sets:
        set_ = all_sets.get(line['Number'], None)
        if set_ is None and ignore_missing:
            continue
        # TODO: fix this to use bulk_create()
        quantity = int(l['QtyOwned'])
        owner.items_owned.create(owned_item=set_, quantity=quantity)
        imported += quantity 
    return imported


def import_brickset_minifigs(owner, data, ignore_missing=True):
    """
    Imports a tab-separated file from Brickset with minifigs owned. Only cares
    about those owned loose, since the others are assumed to be found through
    the sets they're part of.
    """
    all_minifigs = {mf.number: mf for mf in Minifig.objects.all()}
    minifigs = parse_brickset_file(data)
    not_found = []
    # validate that everything can be imported, if we're not just skipping those
    for line in minfigs:
        if l['Number'] not in all_minifigs:
            not_found.append(l)
    # TODO: decide how to handle this
    if not_found and not ignore_missing:
        return False

    # do the actual import
    imported = 0
    for line in minifigs:
        minifig = all_minifigs.get(line['MinifigNumber'], None)
        if minifig is None and ignore_missing:
            continue
        # TODO: fix this to use bulk_create()
        quantity = int['OwnedLoose']
        owner.items_owned.create(owned_item=minifig, quantity=quantity)
        imported += quantity
    return imported
