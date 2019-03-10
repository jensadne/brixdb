from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser
from django.contrib.postgres import fields as pgfields
from django.db import models
from django.template.defaultfilters import slugify
from django.utils.translation import ugettext, ugettext_lazy as _

from model_utils import Choices

from polymorphic.managers import PolymorphicManager
from polymorphic.models import PolymorphicModel

from .managers import CatalogItemQuerySet, ElementQuerySet, MinifigQuerySet, PartQuerySet, SetQuerySet


class User(AbstractBaseUser):
    email = models.EmailField(verbose_name='email address', max_length=255, unique=True)
    name = models.CharField(max_length=256, blank=True, default='')

    USERNAME_FIELD = 'email'
    EMAIL_FIELD = 'email'

    def __str__(self):
        return self.name if self.name else self.email.split('@')[0]


class Category(models.Model):
    parent = models.ForeignKey('self', related_name='sub_categories', blank=True, null=True, on_delete=models.CASCADE)
    bl_id = models.PositiveIntegerField()
    name = models.CharField(max_length=256)

    def __str__(self):
        return self.name 


class CatalogItem(PolymorphicModel):
    TYPE = Choices(('set', _('Set')), ('part', _('Part')), ('minifig', _('Minifig')), ('gear', _("Gear")))
    category = models.ForeignKey(Category, related_name='items', on_delete=models.CASCADE)
    item_type = models.CharField(max_length=16, default=TYPE.part, choices=TYPE)
    # name and number correspond to BL catalog for simplicity
    name = models.CharField(max_length=256)
    number = models.CharField(max_length=32)
    no_inventory = models.BooleanField(default=False)
    year_released = models.PositiveIntegerField(default=0)
    bl_id = models.PositiveIntegerField(default=0)

    # most of TLG's names are horribly weird, but we'd like to keep track of them anyway
    tlg_name = models.CharField(max_length=256, blank=True, default='')

    objects = PolymorphicManager.from_queryset(CatalogItemQuerySet)()
    all_objects = models.Manager()

    def __str__(self):
        return self.name

    def import_inventory(self):
        from .service.bricklink import import_bricklink_inventory, fetch_bricklink_inventory
        import_bricklink_inventory(self, fetch_bricklink_inventory(self))


class Set(CatalogItem):
    objects = PolymorphicManager.from_queryset(SetQuerySet)()

    class Meta:
        ordering = ('number',)

    def __str__(self):
        return '%s %s' % (self.number, self.name)

    def save(self, *args, **kwargs):
        self.item_type = self.TYPE.set
        super(Set, self).save(*args, **kwargs)


class Part(CatalogItem):
    objects = PolymorphicManager.from_queryset(PartQuerySet)()

    class Meta:
        proxy = True
        ordering = ('name',)

    def save(self, *args, **kwargs):
        self.item_type = self.TYPE.part
        super(Part, self).save(*args, **kwargs)


class Minifig(CatalogItem):
    objects = PolymorphicManager.from_queryset(MinifigQuerySet)()

    class Meta:
        proxy = True
        ordering = ('name',)
    
    def save(self, *args, **kwargs):
        self.item_type = self.TYPE.minifig
        super(Minifig, self).save(*args, **kwargs)


class Colour(models.Model):
    name = models.CharField(max_length=256)
    number = models.PositiveIntegerField()
    slug = models.SlugField(default='', max_length=64, editable=False)

    tlg_name = models.CharField(max_length=256, blank=True, default='')
    tlg_number = models.PositiveIntegerField(blank=True, null=True)
    ldraw_name = models.CharField(max_length=256, blank=True, default='')
    ldraw_number = models.PositiveIntegerField(blank=True, null=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.slug = slugify(self.name)
        super(Colour, self).save(*args, **kwargs)


class Element(models.Model):
    """
    An Element is a Part in a given Colour. Due to TLG's ID numbers for
    elements changing when elements are reactivated with same mold we need a
    list for those since we don't differentiate between them.
    """
    part = models.ForeignKey(Part, related_name='elements', on_delete=models.CASCADE)
    colour = models.ForeignKey(Colour, related_name='elements', on_delete=models.CASCADE)
    lego_ids = pgfields.JSONField(default=list) 

    objects = ElementQuerySet.as_manager()

    def __str__(self):
        return '%s %s' % (self.colour, self.part)

    @property
    def lookup_key(self):
        return '%s_%d' % (self.part.number, self.colour.number)
    

class ItemInventory(models.Model):
    """
    Item inventories are tricky things since an Item can contain other Items
    that in turn can contain other Items etc. 
    """
    part_of = models.ForeignKey(CatalogItem, related_name='inventory', on_delete=models.CASCADE)
    item = models.ForeignKey(CatalogItem, null=True, related_name='part_of', on_delete=models.CASCADE)
    element = models.ForeignKey(Element, null=True, related_name='part_of', on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    # the fields below are included in case we go nuts and decide to mirror
    # BL's inventories closely, but that is unlikely
    is_extra = models.BooleanField(default=False)
    is_counterpart = models.BooleanField(default=False)
    is_alternate = models.BooleanField(default=False)
    match_id = models.PositiveIntegerField(blank=True, default=0)

    def __str__(self):
        return '%dx %s' % (self.amount, self.element)

    
class ItemOwned(models.Model):
    """
    All sorts of items can be owned
    """
    owned_item = models.ForeignKey(CatalogItem, related_name='owners', on_delete=models.CASCADE)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='sets_owned', on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    # XXX: state ? (parted out, MISB, deboxed, other?)

    def __str__(self):
        fmt_kw = {'quantity': self.quantity, 'name': self.owned_item.name, 'owner': self.owner}
        return ugettext("{quantity} x %{name} owned by {owner}").format(**fmt_kw) 
