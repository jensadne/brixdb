from django.conf import settings
from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=256)


class Set(models.Model):
    category = models.ForeignKey(Category)
    name = models.CharField(max_length=256)
    

class Part(models.Model):
    name = models.CharField(max_length=256)


class Colour(models.Model):
    name = models.CharField(max_length=256)
    number = models.CharField(max_length=128)

    tlg_name = models.CharField(max_length=256)
    tlg_number = models.CharField(max_length=256)
    ldraw_name = models.CharField(max_length=256)
    ldraw_number = models.CharField(max_length=128)



class Element(models.Model):
    part = models.ForeignKey(Part)
    colour = models.ForeignKey(Colour)
    lego_id = models.PositiveIntegerField(blank=True, null=True)


class SetElement(models.Model):
    in_set = models.ForeignKey(Set)
    element = models.ForeignKey(Element)
    amount = models.PositiveIntegerField(default=1)
    is_extra = models.BooleanField(default=False)
    is_counterpart = models.BooleanField(default=False)

    
class SetOwned(models.Model):
    owned_set = models.ForeignKey(Set)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL)
    number = models.PositiveIntegerField(default=1)

