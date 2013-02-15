#!/usr/bin/env python
import socket
import yaml
import views
from flask import Flask, current_app, render_template, session, request, flash, redirect, url_for, _request_ctx_stack
from elliptics import Logger, Node, log_level, Session

_logger = Logger("/tmp/cocainoom-elliptics.log", log_level.debug)

def get_node():
    if current_app.config.get('ELLIPTICS_HOSTNAME'):
        return current_app.node
    return current_app.nodes.get(session.get('remote'))


#node = LocalProxy(partial(_lookup_object, 'elliptics_session'))


def fill_groups(elliptics_session):
    groups = set()
    for elliptics_id, ip in elliptics_session.get_routes():
        groups.add(elliptics_id.group_id)

    elliptics_session.add_groups(list(groups))
    return elliptics_session

def init_elliptics(host, port=1025, protocol=2):
    node = Node(_logger)
    try:
        node.add_remote(host, port, protocol)
    except RuntimeError:
        return False

    return node


def get_host_port_from_remote(remote):
    protocol = 2
    if ':' in remote:
        if remote.count(':') == 1:
            host, port = remote.split(':')
        else:
            host, port, protocol = remote.split(':')

        if not port.isdigit():
            flash('Port `%s` should be integer' % port, 'danger')
            return remote.encode('utf-8'), 1025, protocol

        return host.encode('utf-8'), int(port)
    return remote.encode('utf-8'), 1025, protocol


def before():
    if request.endpoint == 'static':
        return None

    disconnect = request.form.get('disconnect', False)
    if disconnect:
        session.pop('remote', None)
        return redirect(url_for('home'))

    remote = request.form.get('remote')

    if remote:
        node = init_elliptics(*get_host_port_from_remote(remote))

        if not node:
            flash("Unable to connect to address `%s`" % remote, 'danger')
            return render_template('home.html')

        _request_ctx_stack.top.elliptics_session = Session(node)

        current_app.nodes = {
            remote: node
        }

        session['remote'] = remote
        return redirect(url_for('home'))

    if 'remote' not in session:
        return render_template('home.html')

    current_nodes = getattr(current_app, 'nodes', {})
    if session['remote'] not in current_nodes:
        node = init_elliptics(*get_host_port_from_remote(session['remote']))
        if not node:
            flash("Unable to connect to address `%s`" % session['remote'], 'danger')
            session.pop('remote', None)
            return render_template('home.html')

        current_app.nodes = {
            session['remote']: node
        }

    _request_ctx_stack.top.elliptics_session = Session(get_node())


def create_app():
    app = Flask(__name__)
    with open('/etc/ella/settings.yml') as f:
        app.config.update(**yaml.load(f))

    ELLIPTICS_HOSTNAME = app.config.get('ELLIPTICS_HOSTNAME')

    if ELLIPTICS_HOSTNAME:
        app.node = init_elliptics(ELLIPTICS_HOSTNAME)
    else:
        app.before_request(before)

    app.add_url_rule('/', 'home', view_func=views.home, methods=['GET', 'POST'])
    app.add_url_rule('/routing', view_func=views.routing)
    app.add_url_rule('/stats', view_func=views.stats)
    app.add_url_rule('/find', view_func=views.find)
    app.add_url_rule('/write/<string:key>/<string:value>', view_func=views.write)
    app.add_url_rule('/download/<string:key>', view_func=views.download)
    return app


if __name__ == '__main__':
    app = create_app()
    #app.run(debug=True, host=app.config.get('HOSTNAME', socket.gethostname()), port=int(app.config['PORT']))
    app.run(debug=True, host=app.config.get('HOSTNAME', socket.gethostname()), port=int(5004))
