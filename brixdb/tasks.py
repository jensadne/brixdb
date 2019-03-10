# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals

from celery import shared_task


@shared_task
def bricklink_sync():
    """
    Downloads and imports all relevant data from Bricklink's catalog
    """
    # step 1: get categories

    # step 2: get colours


    # step 3: get sets


    # step 4: get parts


    # step 5: get element mappings


    # step 6 get item inventories
