from rest_framework import serializers

from . import models


class SetSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.Set
        lookup_field = 'number'
        fields = ('number', 'name', )


class PartSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.Part
        lookup_field = 'number'
        fields = ('number', 'name', )


class ColourSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.Colour
        lookup_field = 'slug'
        fields = ('pk', 'slug', 'name')


class ElementSerializer(serializers.HyperlinkedModelSerializer):
    part = PartSerializer(many=False, read_only=True)
    colour = ColourSerializer(many=False, read_only=True)

    class Meta:
        model = models.Element
        lookup_field = 'pk'
        fields = ('pk', 'part', 'colour')


class OwnedColourSerializer(serializers.Serializer):
    # Very lazy solution that hopefully works
    colour_name = serializers.CharField(max_length=256)
    colour_slug = serializers.CharField(max_length=256)
    count = serializers.IntegerField()


class PartDetailSerializer(serializers.HyperlinkedModelSerializer):
    elements = ElementSerializer(many=True)
    ownedColours = serializers.ListField(child=OwnedColourSerializer(), source='owned_colours')

    class Meta:
        model = models.Part
        lookup_field = 'number'
        fields = ('number', 'name', 'elements', 'ownedColours')

    def to_representation(self, obj):
        request = self.context.get('request', None)
        if request.user.is_authenticated:
            obj.owned_colours = models.Part.objects.get_owned_colour_counts(obj, request.user)
        else:
            obj.owned_colours = []
        return super(PartDetailSerializer, self).to_representation(obj)
