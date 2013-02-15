# -*- coding: utf-8 -*-
from functools import partial
from flask import session, current_app
from flask.globals import _lookup_object
from werkzeug.local import LocalProxy


def get_node():
    if current_app.config.get('ELLIPTICS_HOSTNAME'):
        return current_app.node
    return current_app.nodes.get(session.get('remote'))


node = LocalProxy(partial(_lookup_object, 'elliptics_session'))

def fill_groups(elliptics_session):
    groups = set()
    for elliptics_id, ip in elliptics_session.get_routes():
        groups.add(elliptics_id.group_id)

    elliptics_session.add_groups(list(groups))
    return elliptics_session
