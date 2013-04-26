# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'SetElement.is_alternate'
        db.add_column(u'brixdb_setelement', 'is_alternate',
                      self.gf('django.db.models.fields.BooleanField')(default=False),
                      keep_default=False)

        # Adding field 'Set.number'
        db.add_column(u'brixdb_set', 'number',
                      self.gf('django.db.models.fields.CharField')(default='bleh', max_length=32),
                      keep_default=False)

        # Adding field 'Set.no_inventory'
        db.add_column(u'brixdb_set', 'no_inventory',
                      self.gf('django.db.models.fields.BooleanField')(default=False),
                      keep_default=False)

        # Deleting field 'SetOwned.number'
        db.delete_column(u'brixdb_setowned', 'number')

        # Adding field 'SetOwned.amount'
        db.add_column(u'brixdb_setowned', 'amount',
                      self.gf('django.db.models.fields.PositiveIntegerField')(default=1),
                      keep_default=False)


        # Changing field 'Colour.ldraw_number'
        db.alter_column(u'brixdb_colour', 'ldraw_number', self.gf('django.db.models.fields.PositiveIntegerField')(null=True))

        # Changing field 'Colour.number'
        db.alter_column(u'brixdb_colour', 'number', self.gf('django.db.models.fields.PositiveIntegerField')())

        # Changing field 'Colour.tlg_number'
        db.alter_column(u'brixdb_colour', 'tlg_number', self.gf('django.db.models.fields.PositiveIntegerField')(null=True))
        # Adding field 'Part.category'
        db.add_column(u'brixdb_part', 'category',
                      self.gf('django.db.models.fields.related.ForeignKey')(default=1, to=orm['brixdb.Category']),
                      keep_default=False)

        # Adding field 'Part.ldraw_name'
        db.add_column(u'brixdb_part', 'ldraw_name',
                      self.gf('django.db.models.fields.CharField')(default='', max_length=256, blank=True),
                      keep_default=False)

        # Adding field 'Part.tlg_name'
        db.add_column(u'brixdb_part', 'tlg_name',
                      self.gf('django.db.models.fields.CharField')(default='', max_length=256, blank=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'SetElement.is_alternate'
        db.delete_column(u'brixdb_setelement', 'is_alternate')

        # Deleting field 'Set.number'
        db.delete_column(u'brixdb_set', 'number')

        # Deleting field 'Set.no_inventory'
        db.delete_column(u'brixdb_set', 'no_inventory')

        # Adding field 'SetOwned.number'
        db.add_column(u'brixdb_setowned', 'number',
                      self.gf('django.db.models.fields.PositiveIntegerField')(default=1),
                      keep_default=False)

        # Deleting field 'SetOwned.amount'
        db.delete_column(u'brixdb_setowned', 'amount')


        # Changing field 'Colour.ldraw_number'
        db.alter_column(u'brixdb_colour', 'ldraw_number', self.gf('django.db.models.fields.CharField')(default=0, max_length=128))

        # Changing field 'Colour.number'
        db.alter_column(u'brixdb_colour', 'number', self.gf('django.db.models.fields.CharField')(max_length=128))

        # Changing field 'Colour.tlg_number'
        db.alter_column(u'brixdb_colour', 'tlg_number', self.gf('django.db.models.fields.CharField')(default=0, max_length=256))
        # Deleting field 'Part.category'
        db.delete_column(u'brixdb_part', 'category_id')

        # Deleting field 'Part.ldraw_name'
        db.delete_column(u'brixdb_part', 'ldraw_name')

        # Deleting field 'Part.tlg_name'
        db.delete_column(u'brixdb_part', 'tlg_name')


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'brixdb.category': {
            'Meta': {'object_name': 'Category'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '256'})
        },
        u'brixdb.colour': {
            'Meta': {'object_name': 'Colour'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ldraw_name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '256', 'blank': 'True'}),
            'ldraw_number': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
            'number': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'tlg_name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '256', 'blank': 'True'}),
            'tlg_number': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        u'brixdb.element': {
            'Meta': {'object_name': 'Element'},
            'colour': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['brixdb.Colour']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lego_id': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'part': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['brixdb.Part']"})
        },
        u'brixdb.part': {
            'Meta': {'object_name': 'Part'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['brixdb.Category']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ldraw_name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '256', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
            'tlg_name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '256', 'blank': 'True'})
        },
        u'brixdb.set': {
            'Meta': {'object_name': 'Set'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['brixdb.Category']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
            'no_inventory': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'number': ('django.db.models.fields.CharField', [], {'max_length': '32'})
        },
        u'brixdb.setelement': {
            'Meta': {'object_name': 'SetElement'},
            'amount': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1'}),
            'element': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['brixdb.Element']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'in_set': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['brixdb.Set']"}),
            'is_alternate': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_counterpart': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_extra': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        u'brixdb.setowned': {
            'Meta': {'object_name': 'SetOwned'},
            'amount': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'owned_set': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'owners'", 'to': u"orm['brixdb.Set']"}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'sets_owned'", 'to': u"orm['auth.User']"})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['brixdb']