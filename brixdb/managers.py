#from django.db.models import Manager
from model_utils.managers import PassThroughManager
from django.db.models.query import QuerySet


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

