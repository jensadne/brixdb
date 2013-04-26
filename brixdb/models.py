from django.conf import settings
from django.db import models


class Category(models.Model):
    parent = models.ForeignKey('self', related_name='sub_categories', blank=True, null=True)
    bl_id = models.PositiveIntegerField()
    name = models.CharField(max_length=256)

    def __unicode__(self):
        return self.name 


class Set(models.Model):
    category = models.ForeignKey(Category)
    name = models.CharField(max_length=256)
    number = models.CharField(max_length=32)
    no_inventory = models.BooleanField(default=False)

    def __unicode__(self):
        return '%s %s' % (self.number, self.name)


class Part(models.Model):
    category = models.ForeignKey(Category)
    number = models.CharField(max_length=64)
    name = models.CharField(max_length=256)
    ldraw_name = models.CharField(max_length=256, blank=True, default='')
    tlg_name = models.CharField(max_length=256, blank=True, default='')


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

    @property
    def lookup_key(self):
        return '%s_%d' % (self.part.number, self.colour.number)
    

class SetElement(models.Model):
    """
    
    """
    in_set = models.ForeignKey(Set, related_name='inventory')
    element = models.ForeignKey(Element)
    amount = models.PositiveIntegerField(default=1)
    is_extra = models.BooleanField(default=False)
    is_counterpart = models.BooleanField(default=False)
    is_alternate = models.BooleanField(default=False)
    match_id = models.PositiveIntegerField(blank=True, default=0)

    
class SetOwned(models.Model):
    owned_set = models.ForeignKey(Set, related_name='owners')
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='sets_owned')
    amount = models.PositiveIntegerField(default=1)

