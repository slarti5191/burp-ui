# -*- coding: utf8 -*-
import math
import sys

from flask import request, render_template, redirect, url_for, abort, flash, Blueprint, session
from flask.ext.login import login_user, login_required, logout_user, current_user

from .forms import LoginForm
from .exceptions import BUIserverException
from .utils import human_readable as _hr

if sys.version_info >= (3, 0):
    from urllib.parse import quote
else:
    from urllib import quote


class BPWrapper(Blueprint):
    bui = None
    __url__ = None
    __doc__ = None

    def init_bui(self, bui):
        """Loads the right context.
        :param bui: application context
        :type bui: :class:`burpui.server.BUIServer`
        """
        self.bui = bui

view = BPWrapper('view', __name__, template_folder='templates')


"""
Here are some custom filters
"""


@view.app_template_filter()
def mypad(s):
    """
    Filter: used to pad 0's to backup numbers as in the burp's status monitor
    """
    if not s:
        return '0000000'
    return '{0:07d}'.format(int(s))


@view.app_template_filter()
def time_human(d):
    s = ''
    seconds = (((d % 31536000) % 86400) % 3600) % 60
    minutes = math.floor((((d % 31536000) % 86400) % 3600) / 60)
    hours = math.floor(((d % 31536000) % 86400) / 3600)
    if hours > 0:
        s = '%02dH' % hours
    return '%s %02dm %02ds' % (s, minutes, seconds)


@view.app_template_filter()
def bytes_human(b):
    return '{0:.1eM}'.format(_hr(b))

"""
And here is the main site
"""


@view.route('/settings')
@view.route('/settings/<path:conf>')
@view.route('/<server>/settings')
@view.route('/<server>/settings/<path:conf>')
@login_required
def settings(server=None, conf=None):
    # Only the admin can edit the configuration
    if view.bui.acl and not view.bui.acl.is_admin(current_user.get_id()):
        abort(403)
    if not conf:
        try:
            conf = quote(request.args.get('conf'), safe='')
        except:
            pass
    server = server or request.args.get('server')
    return render_template('settings.html', settings=True, server=server, conf=conf)


@view.route('/client/client-settings')
@view.route('/<client>/client-settings')
@view.route('/<client>/client-settings/<path:conf>')
@view.route('/<server>/client/client-settings')
@view.route('/<server>/<client>/client-settings')
@view.route('/<server>/<client>/client-settings/<path:conf>')
@login_required
def cli_settings(server=None, client=None, conf=None):
    # Only the admin can edit the configuration
    if view.bui.acl and not view.bui.acl.is_admin(current_user.get_id()):
        abort(403)
    if not conf:
        try:
            conf = quote(request.args.get('conf'), safe='')
        except:
            pass
    client = client or request.args.get('client')
    server = server or request.args.get('server')
    return render_template('settings.html', settings=True, client=client, server=server, conf=conf)


@view.route('/live-monitor')
@view.route('/<server>/live-monitor')
@view.route('/live-monitor/<name>')
@view.route('/<server>/live-monitor/<name>')
@login_required
def live_monitor(server=None, name=None):
    """Live status monitor view"""
    server = server or request.args.get('server')
    view.bui.cli.is_one_backup_running()
    if view.bui.standalone:
        if not view.bui.cli.running:
            flash('Sorry, there are no running backups', 'warning')
            return redirect(url_for('.home'))
    else:
        run = False
        for a in view.bui.cli.servers:
            run = run or (a in view.bui.cli.running and view.bui.cli.running[a])
        if not run:
            flash('Sorry, there are no running backups', 'warning')
            return redirect(url_for('.home'))

    return render_template('live-monitor.html', live=True, cname=name, server=server)


@view.route('/client-browse/<name>', methods=['GET'])
@view.route('/<server>/client-browse/<name>', methods=['GET'])
@view.route('/client-browse/<name>/<int:backup>')
@view.route('/<server>/client-browse/<name>/<int:backup>')
@view.route('/client-browse/<name>/<int:backup>/<int:encrypted>')
@view.route('/<server>/client-browse/<name>/<int:backup>/<int:encrypted>')
@login_required
def client_browse(server=None, name=None, backup=None, encrypted=None):
    """Browse a specific backup of a specific client"""
    if request.args.get('encrypted') == '1':
        encrypted = 1
    server = server or request.args.get('server')
    bkp = request.args.get('backup')
    if bkp and not backup:
        return redirect(url_for('.client_browse', name=name, backup=bkp, encrypted=encrypted, server=server))
    return render_template('client-browse.html', tree=True, backup=True, overview=True, cname=name, nbackup=backup, encrypted=encrypted, server=server)


@view.route('/client-report/<name>')
@view.route('/<server>/client-report/<name>')
@login_required
def client_report(server=None, name=None):
    """Specific client report"""
    server = server or request.args.get('server')
    try:
        l = view.bui.cli.get_client(name, agent=server)
    except BUIserverException:
        l = []
    if len(l) == 1:
        return redirect(url_for('.backup_report', name=name, backup=l[0]['number'], server=server))
    return render_template('client-report.html', client=True, report=True, cname=name, server=server)


@view.route('/clients-report')
@view.route('/<server>/clients-report')
@login_required
def clients_report(server=None):
    """Global report"""
    server = server or request.args.get('server')
    return render_template('clients-report.html', clients=True, report=True, server=server)


@view.route('/backup-report/<name>', methods=['GET'])
@view.route('/<server>/backup-report/<name>', methods=['GET'])
@view.route('/backup-report/<name>/<int:backup>', methods=['GET'])
@view.route('/<server>/backup-report/<name>/<int:backup>', methods=['GET'])
@login_required
def backup_report(server=None, name=None, backup=None):
    """Backup specific report"""
    backup = backup or request.args.get('backup')
    server = server or request.args.get('server')
    return render_template('backup-report.html', client=True, backup=True, report=True, cname=name, nbackup=backup, server=server)


@view.route('/client', methods=['GET'])
@view.route('/<server>/client', methods=['GET'])
@view.route('/client/<name>')
@view.route('/<server>/client/<name>')
@login_required
def client(server=None, name=None):
    """Specific client overview"""
    c = name or request.args.get('name')
    server = server or request.args.get('server')
    if view.bui.cli.is_backup_running(c, agent=server):
        return redirect(url_for('.live_monitor', name=c, server=server))
    return render_template('client.html', client=True, overview=True, cname=c, server=server)


@view.route('/clients', methods=['GET'])
@view.route('/<server>/clients', methods=['GET'])
@login_required
def clients(server=None):
    server = server or request.args.get('server')
    return render_template('clients.html', clients=True, overview=True, server=server)


@view.route('/servers', methods=['GET'])
@login_required
def servers():
    return render_template('servers.html', servers=True, overview=True)


@view.route('/login', methods=['POST', 'GET'])
def login():
    form = LoginForm(request.form)
    if form.validate_on_submit():
        user = view.bui.uhandler.user(form.username.data)
        if user.active and user.login(form.username.data, passwd=form.password.data):
            login_user(user, remember=form.remember.data)
            flash('Logged in successfully', 'success')
            return redirect(request.args.get("next") or url_for('.home'))
        else:
            flash('Wrong username or password', 'danger')
    return render_template('login.html', form=form, login=True)


@view.route('/logout')
@login_required
def logout():
    if 'authenticated' in session:
        session.pop('authenticated')
    logout_user()
    return redirect(url_for('.home'))


@view.route('/about')
def about():
    """about view"""
    return render_template('about.html', about=True, login=(not current_user.is_authenticated), doc=view.__doc__, url=view.__url__)


@view.route('/')
@login_required
def home():
    """Home page"""
    if view.bui.standalone:
        return redirect(url_for('.clients'))
    else:
        server = request.args.get('server')
        if server:
            return redirect(url_for('.clients', server=server))
        return redirect(url_for('.servers'))
