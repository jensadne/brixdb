# -*- coding: utf-8 -*-
from django.db import connection
from django.db.models.expressions import RawSQL
from django.db.models.query import QuerySet

from polymorphic.managers import PolymorphicQuerySet


class CatalogItemQuerySet(PolymorphicQuerySet):
    pass


class SetQuerySet(CatalogItemQuerySet):
    pass


class PartQuerySet(CatalogItemQuerySet):
    def get_owned_colour_counts(self, part, owner):
        """
        Aggregates the number of colours the given User owns the given Part in.
        """
        sql = """SELECT c.slug, c.name, SUM(ii.quantity*oi.quantity)
                FROM brixdb_iteminventory ii, brixdb_colour c, brixdb_element e, brixdb_owneditem oi
                WHERE ii.element_id = e.id and e.colour_id = c.id AND e.part_id = {part_id}
                    AND ii.part_of_id = oi.item_id AND oi.owner_id = {owner_id}
                    GROUP BY c.slug, c.name
                    ORDER BY SUM DESC
                 """.format(part_id=part.pk, owner_id=owner.pk)
        c = connection.cursor()
        c.execute(sql)
        return [{'colour_slug': slug, 'colour_name': name, 'count': count} for slug, name, count in c.fetchall()]


class ElementQuerySet(QuerySet):
    def not_owned_by(self, user):
        """
        Returns the Elements `user` doesn't own.
        """
        from .models import ItemInventory
        # TODO: use recursive query for owned Items
        ielems = ItemInventory.objects.filter(part_of__in=user.sets_owned.values_list('owned_set', flat=True))
        return self.exclude(pk__in=ielems.values_list('element', flat=True)).distinct()

    def owned_by(self, user):
        from .models import ItemInventory
        # TODO: use recursive query for owned Items
        ielems = ItemInventory.objects.filter(part_of__in=user.owned_items.values_list('item', flat=True))
        return self.filter(pk__in=ielems.values_list('element', flat=True)).distinct()

    def for_user(self, user, owned=True):
        return self.owned_by(user) if owned else self.not_owned_by(user)

    def by_colour(self, colour):
        return self.filter(colour=colour)

    def by_part(self, part):
        return self.filter(part=part)


class MinifigQuerySet(CatalogItemQuerySet):
    pass
