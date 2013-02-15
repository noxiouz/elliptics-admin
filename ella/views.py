# -*- coding: utf-8 -*-
import re
import hashlib
import subprocess
from copy import deepcopy
from itertools import groupby
from operator import itemgetter
from urllib import quote_plus
from flask import render_template, request, abort, current_app
from elliptics import Session
from globals import node, fill_groups


def home():
    return render_template('layout.html', node=node,
                           hardcoded_elliptics_hostname=current_app.config.get('ELLIPTICS_HOSTNAME', False))


def routes_to_groups(routes, first_digits=2):
    rv = {}
    for elliptics_id, ip in routes:
        int_str_to_bin_str = lambda x: bin(x)[2:].rjust(8, '0')
        cut_id = int(''.join(map(int_str_to_bin_str, elliptics_id.id[:first_digits])), 2)
        rv.setdefault(elliptics_id.group_id, {})[cut_id] = ip
    return rv


def routing():
    routes = node.get_routes()
    number_of_digits_to_use = 2
    groups = routes_to_groups(routes, first_digits=number_of_digits_to_use)
    pie_groups_interest = {}
    for group_id, group_info in groups.items():
        pie_groups_interest.setdefault(group_id, {})
        max = 2 ** (8 * number_of_digits_to_use) - 1
        last = sorted(group_info.keys())[-1]
        for cut_id in reversed(sorted(group_info.keys())):
            pie_groups_interest[group_id][cut_id] = max - cut_id
            max = cut_id
        else:
            pie_groups_interest[group_id][last] += max

    return render_template("routing.html", **locals())


def find():
    key = request.args.get('key')
    if key:
        urlencoded_key = quote_plus(key)
        try:
            fill_groups(node)
            data = node.read(key)
            lookup_tuple = node.lookup(str(key))
            routes = node.get_routes()
            if len(routes):
                elliptics_id, ip = routes[0]
                hash = hashlib.sha512(key).hexdigest()
                p = subprocess.Popen("dnet_find -r %s:2 -I %s" % (ip, hash),
                                     stderr=subprocess.PIPE, shell=True)
                p.wait()
                dnet_find_stderr = p.stderr.read()
                if dnet_find_stderr:
                    objects = []
                    for index, line in enumerate(dnet_find_stderr.split('\n')):
                        print line
                        if "meta" in line:
                            break
                        if line.endswith('status: -2'):
                            continue

                        line = line.split(':', 3)[3].strip()
                        match = re.search(r'((?:\d+|\.){7}:\d+):\s*should live at:\s*((?:\d+|\.){7}:\d+)', line)
                        if match:
                            if match.groups()[0] != match.groups()[1]:
                                line = line.replace(match.groups()[0],
                                                    "<span class='alert-success'>%s</span>" % match.groups()[0])
                                line = line.replace(match.groups()[1],
                                                    "<span class='alert-danger'>%s</span>" % match.groups()[1])
                            else:
                                line = line.replace(match.groups()[0],
                                                    "<span class='alert-success'>%s</span>" % match.groups()[0])
                                line = line.replace(match.groups()[1],
                                                    "<span class='alert-success'>%s</span>" % match.groups()[1])

                        line = line.replace(hash[:12]+":", "")
                        line = line.replace("FIND-OK object:", "")
                        line = "Group " + line
                        objects.append(line)
                        objects.sort()

                    meta = []
                    for index, line in enumerate(dnet_find_stderr.split('\n')[index:]):
                        if line.endswith('status: -2') or hash in line or not line:
                            continue
                        line = line.split(':', 3)[3].strip()
                        match = re.match(r'(\d+).*?((?:\d+|\.){7}:\d+)', line)
                        if match:
                            group, ip = match.groups()
                            meta.append({'group': group, 'ip': ip, 'lines': []})
                        else:
                            meta[-1]['lines'].append(line)

                    meta.sort(key=itemgetter('group'))
                else:
                    log = []
        except RuntimeError:
            data = None

    return render_template('find.html', **locals())


def write(key, value):
    fill_groups(node)
    node.write_data(key.encode('utf-8'), value.encode('utf-8'))
    return 'ok'


def download(key):
    try:
        fill_groups(node)
        data = node.read(key)
    except RuntimeError:
        return abort(404)

    return str(data)


def reduce_counters(group_stats, key, val_to_reduce):
    stored_val = group_stats.setdefault(key, deepcopy(val_to_reduce))
    if val_to_reduce == stored_val:
        return group_stats

    for attr, attr_val in val_to_reduce.items():
        group_stats[key][attr] = (stored_val[attr][0] + attr_val[0], stored_val[attr][1] + attr_val[1])


def aggregate_stats(grouper):
    group_stats = {}
    for group in grouper:
        for key, val in group.items():
            if key in set(['group_id', 'addr']):
                group_stats.setdefault(key, val)
                continue
            reduce_counters(group_stats, key, val)


    group_stats['addr'] = "Aggregated statistics"
    return group_stats


def stats():
    aggr_stats = []
    for group_id, grouper in groupby(sorted(node.stat_log(), key=itemgetter('group_id')), lambda x: x['group_id']):
        grouper_list = list(grouper)
        aggr_stats.append([aggregate_stats(grouper_list), grouper_list])
    return render_template('stats.html', **locals())
