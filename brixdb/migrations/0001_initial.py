# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Category'
        db.create_table(u'brixdb_category', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('parent', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='sub_categories', null=True, to=orm['brixdb.Category'])),
            ('bl_id', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=256)),
        ))
        db.send_create_signal(u'brixdb', ['Category'])

        # Adding model 'CatalogItem'
        db.create_table(u'brixdb_catalogitem', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('category', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['brixdb.Category'])),
            ('item_type', self.gf('django.db.models.fields.PositiveIntegerField')(default=2, db_index=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=256)),
            ('number', self.gf('django.db.models.fields.CharField')(max_length=32)),
            ('no_inventory', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('year_released', self.gf('django.db.models.fields.PositiveIntegerField')(default=0)),
            ('bl_id', self.gf('django.db.models.fields.PositiveIntegerField')(default=0)),
            ('ldraw_name', self.gf('django.db.models.fields.CharField')(default='', max_length=256, blank=True)),
            ('tlg_name', self.gf('django.db.models.fields.CharField')(default='', max_length=256, blank=True)),
        ))
        db.send_create_signal(u'brixdb', ['CatalogItem'])

        # Adding model 'Colour'
        db.create_table(u'brixdb_colour', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=256)),
            ('number', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('tlg_name', self.gf('django.db.models.fields.CharField')(default='', max_length=256, blank=True)),
            ('tlg_number', self.gf('django.db.models.fields.PositiveIntegerField')(null=True, blank=True)),
            ('ldraw_name', self.gf('django.db.models.fields.CharField')(default='', max_length=256, blank=True)),
            ('ldraw_number', self.gf('django.db.models.fields.PositiveIntegerField')(null=True, blank=True)),
        ))
        db.send_create_signal(u'brixdb', ['Colour'])

        # Adding model 'Element'
        db.create_table(u'brixdb_element', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('part', self.gf('django.db.models.fields.related.ForeignKey')(related_name='elements', to=orm['brixdb.CatalogItem'])),
            ('colour', self.gf('django.db.models.fields.related.ForeignKey')(related_name='elements', to=orm['brixdb.Colour'])),
            ('lego_id', self.gf('django.db.models.fields.PositiveIntegerField')(null=True, blank=True)),
        ))
        db.send_create_signal(u'brixdb', ['Element'])

        # Adding model 'ItemElement'
        db.create_table(u'brixdb_itemelement', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('item', self.gf('django.db.models.fields.related.ForeignKey')(related_name='inventory', to=orm['brixdb.CatalogItem'])),
            ('element', self.gf('django.db.models.fields.related.ForeignKey')(related_name='in_sets', to=orm['brixdb.Element'])),
            ('amount', self.gf('django.db.models.fields.PositiveIntegerField')(default=1)),
            ('is_extra', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('is_counterpart', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('is_alternate', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('match_id', self.gf('django.db.models.fields.PositiveIntegerField')(default=0, blank=True)),
        ))
        db.send_create_signal(u'brixdb', ['ItemElement'])

        # Adding model 'SetOwned'
        db.create_table(u'brixdb_setowned', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('owned_set', self.gf('django.db.models.fields.related.ForeignKey')(related_name='owners', to=orm['brixdb.CatalogItem'])),
            ('owner', self.gf('django.db.models.fields.related.ForeignKey')(related_name='sets_owned', to=orm['auth.User'])),
            ('amount', self.gf('django.db.models.fields.PositiveIntegerField')(default=1)),
        ))
        db.send_create_signal(u'brixdb', ['SetOwned'])


    def backwards(self, orm):
        # Deleting model 'Category'
        db.delete_table(u'brixdb_category')

        # Deleting model 'CatalogItem'
        db.delete_table(u'brixdb_catalogitem')

        # Deleting model 'Colour'
        db.delete_table(u'brixdb_colour')

        # Deleting model 'Element'
        db.delete_table(u'brixdb_element')

        # Deleting model 'ItemElement'
        db.delete_table(u'brixdb_itemelement')

        # Deleting model 'SetOwned'
        db.delete_table(u'brixdb_setowned')


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
        u'brixdb.catalogitem': {
            'Meta': {'object_name': 'CatalogItem'},
            'bl_id': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['brixdb.Category']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'item_type': ('django.db.models.fields.PositiveIntegerField', [], {'default': '2', 'db_index': 'True'}),
            'ldraw_name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '256', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
            'no_inventory': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'number': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'tlg_name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '256', 'blank': 'True'}),
            'year_released': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'})
        },
        u'brixdb.category': {
            'Meta': {'object_name': 'Category'},
            'bl_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'sub_categories'", 'null': 'True', 'to': u"orm['brixdb.Category']"})
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
            'colour': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'elements'", 'to': u"orm['brixdb.Colour']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lego_id': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'part': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'elements'", 'to': u"orm['brixdb.CatalogItem']"})
        },
        u'brixdb.itemelement': {
            'Meta': {'object_name': 'ItemElement'},
            'amount': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1'}),
            'element': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'in_sets'", 'to': u"orm['brixdb.Element']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_alternate': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_counterpart': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_extra': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'item': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'inventory'", 'to': u"orm['brixdb.CatalogItem']"}),
            'match_id': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0', 'blank': 'True'})
        },
        u'brixdb.setowned': {
            'Meta': {'object_name': 'SetOwned'},
            'amount': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'owned_set': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'owners'", 'to': u"orm['brixdb.CatalogItem']"}),
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