from django.conf import settings
from django.db import models
from django.utils.translation import ugettext_lazy as _

from model_utils import Choices
from model_utils.managers import PassThroughManager

from .managers import SetQuerySet, PartQuerySet


class Category(models.Model):
    parent = models.ForeignKey('self', related_name='sub_categories', blank=True, null=True)
    bl_id = models.PositiveIntegerField()
    name = models.CharField(max_length=256)

    def __unicode__(self):
        return self.name 


class CatalogItem(models.Model):
    TYPE = Choices((1, 'set', _('Set')), (2, 'part', _('Part')), (3, 'minifig', _('Minifig')))

    category = models.ForeignKey(Category)
    item_type = models.PositiveIntegerField(default=TYPE.part, choices=TYPE, db_index=True)
    name = models.CharField(max_length=256)
    number = models.CharField(max_length=32)
    no_inventory = models.BooleanField(default=False)
    year_released = models.PositiveIntegerField(default=0)
    bl_id = models.PositiveIntegerField(default=0)
    ldraw_name = models.CharField(max_length=256, blank=True, default='')
    tlg_name = models.CharField(max_length=256, blank=True, default='')

    def __unicode__(self):
        return self.name

    def import_inventory(self):
        from .utils import import_bricklink_inventory, fetch_bricklink_inventory
        import_bricklink_inventory(self, fetch_bricklink_inventory(self))


class Set(CatalogItem):
    objects = PassThroughManager.for_queryset_class(SetQuerySet)()

    class Meta:
        proxy = True
        ordering = ('number',)

    def __unicode__(self):
        return '%s %s' % (self.number, self.name)


class Part(CatalogItem):
    objects = PassThroughManager.for_queryset_class(PartQuerySet)()

    class Meta:
        proxy = True
        ordering = ('name',)
        

class Minifig(CatalogItem):
    class Meta:
        proxy = True
        ordering = ('name',)


class Colour(models.Model):
    name = models.CharField(max_length=256)
    number = models.PositiveIntegerField()

    tlg_name = models.CharField(max_length=256, blank=True, default='')
    tlg_number = models.PositiveIntegerField(blank=True, null=True)
    ldraw_name = models.CharField(max_length=256, blank=True, default='')
    ldraw_number = models.PositiveIntegerField(blank=True, null=True)

    def __unicode__(self):
        return self.name


class Element(models.Model):
    part = models.ForeignKey(Part, related_name='elements')
    colour = models.ForeignKey(Colour, related_name='elements')
    lego_id = models.PositiveIntegerField(blank=True, null=True)

    def __unicode__(self):
        return '%s %s' % (self.colour, self.part)

    @property
    def lookup_key(self):
        return '%s_%d' % (self.part.number, self.colour.number)
    

class ItemElement(models.Model):
    """
    
    """
    item = models.ForeignKey(CatalogItem, related_name='inventory')
    element = models.ForeignKey(Element, related_name='in_sets')
    amount = models.PositiveIntegerField(default=1)
    is_extra = models.BooleanField(default=False)
    is_counterpart = models.BooleanField(default=False)
    is_alternate = models.BooleanField(default=False)
    match_id = models.PositiveIntegerField(blank=True, default=0)

    
class SetOwned(models.Model):
    owned_set = models.ForeignKey(Set, related_name='owners')
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='sets_owned')
    amount = models.PositiveIntegerField(default=1)

