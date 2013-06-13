from django.db.models.query import QuerySet


class SetQuerySet(QuerySet):
    def get_queryset(self, *args, **kwargs):
        return super(SetQuerySet, self).get_queryset(*args, **kwargs).filter(item_type=self.model.TYPE.set)


class PartQuerySet(QuerySet):
    pass
