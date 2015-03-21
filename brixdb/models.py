from __future__ import unicode_literals, absolute_import

from django.conf import settings
from django.db import models
from django.template.defaultfilters import slugify
from django.utils.translation import ugettext, ugettext_lazy as _

from model_utils import Choices
#from model_utils.managers import PassThroughManager

#from .managers import SetQuerySet, PartQuerySet
from .managers import SetManager, PartManager


class Category(models.Model):
    parent = models.ForeignKey('self', related_name='sub_categories', blank=True, null=True)
    bl_id = models.PositiveIntegerField()
    name = models.CharField(max_length=256)

    def __unicode__(self):
        return self.name 


class CatalogItem(models.Model):
    TYPE = Choices((1, 'set', _('Set')), (2, 'part', _('Part')), (3, 'minifig', _('Minifig')), (4, 'gear', _("Gear")))

    category = models.ForeignKey(Category, related_name='items')
    item_type = models.PositiveIntegerField(default=TYPE.part, choices=TYPE, db_index=True)
    name = models.CharField(max_length=256)
    number = models.CharField(max_length=32)
    no_inventory = models.BooleanField(default=False)
    year_released = models.PositiveIntegerField(default=0)
    bl_id = models.PositiveIntegerField(default=0)
    ldraw_name = models.CharField(max_length=256, blank=True, default='')
    tlg_name = models.CharField(max_length=256, blank=True, default='')

    all_objects = models.Manager()

    def __unicode__(self):
        return self.name

    def import_inventory(self):
        from .utils import import_bricklink_inventory, fetch_bricklink_inventory
        import_bricklink_inventory(self, fetch_bricklink_inventory(self))


class Set(CatalogItem):
    objects = SetManager()#PassThroughManager.for_queryset_class(SetQuerySet)()

    class Meta:
        proxy = True
        ordering = ('number',)

    def __unicode__(self):
        return '%s %s' % (self.number, self.name)

    def save(self, *args, **kwargs):
        self.item_type = self.TYPE.set
        super(Set, self).save(*args, **kwargs)


class Part(CatalogItem):
    objects = PartManager()#PassThroughManager.for_queryset_class(PartQuerySet)()

    class Meta:
        proxy = True
        ordering = ('name',)

    def save(self, *args, **kwargs):
        self.item_type = self.TYPE.part
        super(Part, self).save(*args, **kwargs)


class Minifig(CatalogItem):
    class Meta:
        proxy = True
        ordering = ('name',)


class Colour(models.Model):
    name = models.CharField(max_length=256)
    number = models.PositiveIntegerField()
    slug = models.SlugField(default='', max_length=32)

    tlg_name = models.CharField(max_length=256, blank=True, default='')
    tlg_number = models.PositiveIntegerField(blank=True, null=True)
    ldraw_name = models.CharField(max_length=256, blank=True, default='')
    ldraw_number = models.PositiveIntegerField(blank=True, null=True)

    def __unicode__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.slug = slugify(self.name)
        super(Colour, self).save(*args, **kwargs)


class Element(models.Model):
    """
    An Element is a Part in a given Colour. Due to TLG's ID numbers for
    elements changing when elements are reactivated with same mold we need a
    list of some kind for those since we don't differentiate between them.
    """
    part = models.ForeignKey(Part, related_name='elements')
    colour = models.ForeignKey(Colour, related_name='elements')
    #lego_id = models.PositiveIntegerField(blank=True, null=True)

    def __unicode__(self):
        return '%s %s' % (self.colour, self.part)

    @property
    def lookup_key(self):
        return '%s_%d' % (self.part.number, self.colour.number)
    

class ItemElement(models.Model):
    """
    An Element that's part of an Item (Set, Part, etc) 
    """
    item = models.ForeignKey(CatalogItem, related_name='inventory')
    element = models.ForeignKey(Element, related_name='in_sets')
    amount = models.PositiveIntegerField(default=1)
    is_extra = models.BooleanField(default=False)
    is_counterpart = models.BooleanField(default=False)
    is_alternate = models.BooleanField(default=False)
    match_id = models.PositiveIntegerField(blank=True, default=0)

    def __unicode__(self):
        return '%dx %s' % (self.amount, self.element)

    
class SetOwned(models.Model):
    owned_set = models.ForeignKey(Set, related_name='owners')
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='sets_owned')
    amount = models.PositiveIntegerField(default=1)
    # XXX: state ? (parted out, MISB, deboxed, other?)

    def __unicode__(self):
        dic = {'number': self.amount, 'name': self.owned_set.name, 'owner': self.user.username}
        return ugettext('%(number)s x %(name) owned by %(owner)s') % dic
