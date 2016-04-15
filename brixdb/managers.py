from django.apps import apps
from django.db.models.query import QuerySet

#from django.db.models import Manager
from model_utils.managers import PassThroughManager


class SetQuerySet(QuerySet):
    pass
    #def all(self, *args, **kwargs):
    #    return super(SetQuerySet, self).all(*args, **kwargs).filter(item_type=self.model.TYPE.set)


class SetManager(PassThroughManager):
    def get_query_set(self, *args, **kwargs):
        return super(SetManager, self).get_query_set(*args, **kwargs).filter(item_type=self.model.TYPE.set)


class PartQuerySet(QuerySet):
#    def all(self, *args, **kwargs):
    pass


class PartManager(PassThroughManager):
    def get_query_set(self, *args, **kwargs):
        return super(PartManager, self).get_query_set(*args, **kwargs).filter(item_type=self.model.TYPE.part)


class ElementQuerySet(QuerySet):
    def not_owned_by(self, user):
        """
        Returns the Elements `user` doesn't own.
        """
        ItemElement = apps.get_model('brixdb', 'ItemElement')
        ielems = ItemElement.objects.filter(item__in=user.sets_owned.values_list('owned_set', flat=True))
        return self.exclude(pk__in=ielems.values_list('element', flat=True)).distinct()

    def owned_by(self, user):
        ItemElement = apps.get_model('brixdb', 'ItemElement')
        ielems = ItemElement.objects.filter(item__in=user.sets_owned.values_list('owned_set', flat=True))
        return self.filter(pk__in=ielems.values_list('element', flat=True)).distinct()

    def for_user(self, user, owned=True):
        return self.owned_by(user) if owned else self.not_owned_by(user)

    def by_colour(self, colour):
        return self.filter(colour=colour)
