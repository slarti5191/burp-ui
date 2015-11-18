# -*- coding: utf8 -*-
import re
import socket
import errno
import time
import struct
import pickle
import traceback
try:
    import ujson as json
except ImportError:
    import json
try:
    import ConfigParser
except ImportError:
    import configparser as ConfigParser

from future.utils import iteritems

from .interface import BUIbackend


class Burp(BUIbackend):
    """The :class:`burpui.misc.backend.multi.Burp` class provides a consistent
    backend to interact with ``agents``.

    It is actually the *real* multi backend implementing the
    :class:`burpui.misc.backend.interface.BUIbackend` class.

    For each agent found in the configuration, it will load a
    :class:`burpui.misc.backend.multi.NClient` class.

    :param server: ``Burp-UI`` server instance in order to access logger
                   and/or some global settings
    :type server: :class:`burpui.server.BUIServer`

    :param conf: Configuration file to use
    :type conf: str
    """

    def __init__(self, server=None, conf=None):
        self.app = None
        self.acl_handler = False
        if server:
            if hasattr(server, 'app'):
                self.app = server.app
                self.set_logger(self.app.logger)
            self.acl_handler = server.acl_handler
        self.servers = {}
        self.app.config['SERVERS'] = []
        self.running = {}
        if conf:
            config = ConfigParser.ConfigParser()
            with open(conf) as fp:
                config.readfp(fp)
                for sec in config.sections():
                    r = re.match('^Agent:(.+)$', sec)
                    if r:
                        ssl = False
                        host = self._safe_config_get(config.get, 'host', sec)
                        port = self._safe_config_get(config.getint, 'port', sec, cast=int)
                        password = self._safe_config_get(config.get, 'password', sec)
                        ssl = self._safe_config_get(config.getboolean, 'ssl', sec, cast=bool)

                        self.servers[r.group(1)] = NClient(self.app, host, port, password, ssl)

        self.app.logger.debug(self.servers)
        for (key, serv) in iteritems(self.servers):
            self.app.config['SERVERS'].append(key)

    def status(self, query='\n', agent=None):
        """See :func:`burpui.misc.backend.interface.BUIbackend.status`"""
        return self.servers[agent].status(query)

    def get_backup_logs(self, number, client, forward=False, agent=None):
        """See :func:`burpui.misc.backend.interface.BUIbackend.get_backup_logs`"""
        return self.servers[agent].get_backup_logs(number, client, forward)

    def get_clients_report(self, clients, agent=None):
        """See :func:`burpui.misc.backend.interface.BUIbackend.get_clients_report`"""
        return self.servers[agent].get_clients_report(clients)

    def get_counters(self, name=None, agent=None):
        """See :func:`burpui.misc.backend.interface.BUIbackend.get_counters`"""
        return self.servers[agent].get_counters(name)

    def is_backup_running(self, name=None, agent=None):
        """See :func:`burpui.misc.backend.interface.BUIbackend.is_backup_running`"""
        return self.servers[agent].is_backup_running(name)

    def is_one_backup_running(self, agent=None):
        """See :func:`burpui.misc.backend.interface.BUIbackend.is_one_backup_running`"""
        r = []
        if agent:
            r = self.servers[agent].is_one_backup_running(agent)
            self.running[agent] = r
        else:
            r = {}
            for a in self.servers:
                r[a] = self.servers[a].is_one_backup_running(a)
            self.running = r
        self.refresh = time.time()
        return r

    def get_all_clients(self, agent=None):
        """See :func:`burpui.misc.backend.interface.BUIbackend.get_all_clients`"""
        if agent not in self.servers:
            return []
        return self.servers[agent].get_all_clients()

    def get_client(self, name=None, agent=None):
        """See :func:`burpui.misc.backend.interface.BUIbackend.get_client`"""
        return self.servers[agent].get_client(name)

    def get_tree(self, name=None, backup=None, root=None, agent=None):
        """See :func:`burpui.misc.backend.interface.BUIbackend.get_tree`"""
        return self.servers[agent].get_tree(name, backup, root)

    def restore_files(self, name=None, backup=None, files=None, strip=None, archive='zip', password=None, agent=None):
        """See :func:`burpui.misc.backend.interface.BUIbackend.restore_files`"""
        return self.servers[agent].restore_files(name, backup, files, strip, archive, password)

    def read_conf_cli(self, client=None, conf=None, agent=None):
        """See :func:`burpui.misc.backend.interface.BUIbackend.read_conf_cli`"""
        return self.servers[agent].read_conf_cli(client, conf)

    def read_conf_srv(self, conf=None, agent=None):
        """See :func:`burpui.misc.backend.interface.BUIbackend.read_conf_srv`"""
        return self.servers[agent].read_conf_srv(conf)

    def store_conf_cli(self, data, client=None, conf=None, agent=None):
        """See :func:`burpui.misc.backend.interface.BUIbackend.store_conf_cli`"""
        return self.servers[agent].store_conf_cli(data, client, conf)

    def store_conf_srv(self, data, conf=None, agent=None):
        """See :func:`burpui.misc.backend.interface.BUIbackend.store_conf_srv`"""
        return self.servers[agent].store_conf_srv(data, conf)

    def expand_path(self, path=None, client=None, agent=None):
        """See :func:`burpui.misc.backend.interface.BUIbackend.expand_path`"""
        return self.servers[agent].expand_path(path, client)

    def delete_client(self, client=None, agent=None):
        """See :func:`burpui.misc.backend.interface.BUIbackend.delete_client`"""
        return self.servers[agent].delete_client(client)

    def clients_list(self, agent=None):
        """See :func:`burpui.misc.backend.interface.BUIbackend.clients_list`"""
        return self.servers[agent].clients_list()

    def get_parser_attr(self, attr=None, agent=None):
        """See :func:`burpui.misc.backend.interface.BUIbackend.get_parser_attr`"""
        return self.servers[agent].get_parser_attr(attr)

    def schedule_restore(self, name=None, backup=None, files=None, strip=None, force=None, prefix=None, restoreto=None, agent=None):
        """See :func:`burpui.misc.backend.interface.BUIbackend.schedule_restore`"""
        return self.servers[agent].schedule_restore(name, backup, files, strip, force, prefix, restoreto)


class NClient(BUIbackend):
    """The :class:`burpui.misc.backend.multi.NClient` class provides a
    consistent backend to interact with ``agents``.

    It acts as a proxy so it works with any agent running a backend implementing
    the :class:`burpui.misc.backend.interface.BUIbackend` class.

    :param app: The application context
    :type app: Flask object

    :param host: Address of the remote agent
    :type host: str

    :param port: Port of the remote agent
    :type port: int

    :param password: Secret between the agent and the burp-ui server
    :type password: str

    :param ssl: Use SSL to communicate with the agent
    :type ssl: bool
    """

    def __init__(self, app=None, host=None, port=None, password=None, ssl=None):
        self.host = host
        self.port = port
        self.password = password
        self.ssl = ssl
        self.connected = False
        self.app = app

    def conn(self):
        """Connects to the agent if needed"""
        try:
            if self.connected:
                return
            self.sock = self.do_conn()
            self.connected = True
            self.app.logger.debug('OK, connected to agent %s:%s', self.host, self.port)
        except Exception as e:
            self.connected = False
            self.app.logger.error('Could not connect to %s:%s => %s', self.host, self.port, str(e))

    def do_conn(self):
        """Do the actual connection to the agent"""
        ret = None
        if self.ssl:
            import ssl
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(5)
            ret = ssl.wrap_socket(s, cert_reqs=ssl.CERT_NONE, ssl_version=ssl.PROTOCOL_SSLv23)
            try:
                ret.connect((self.host, self.port))
            except Exception as e:
                self.app.logger.error('ERROR: %s', str(e))
                raise e
        else:
            ret = socket.create_connection((self.host, self.port), timeout=5)
        return ret

    def ping(self):
        """Check if we are connected to the agent"""
        self.conn()
        res = self.connected
        return res

    def close(self, force=True):
        """Disconnect from the agent"""
        if self.connected and force:
            self.sock.close()
        self.connected = False

    def do_command(self, data=None, restarted=False):
        """Send a command to the remote agent"""
        self.conn()
        res = '[]'
        toclose = True
        if not data or not self.connected:
            return res
        try:
            data['password'] = self.password
            raw = json.dumps(data)
            length = len(raw)
            self.sock.sendall(struct.pack('!Q', length))
            self.sock.sendall(raw.encode('UTF-8'))
            self.app.logger.debug("Sending: %s", raw)
            tmp = self.sock.recv(2).decode('UTF-8')
            self.app.logger.debug("recv: '%s'", tmp)
            if 'OK' != tmp:
                self.app.logger.debug('Ooops, unsuccessful!')
                return res
            self.app.logger.debug("Data sent successfully")
            tmp = 'OK'
            if data['func'] == 'restore_files':
                tmp = self.sock.recv(2)
            lengthbuf = self.sock.recv(8)
            length, = struct.unpack('!Q', lengthbuf)
            if data['func'] == 'restore_files':
                err = None
                if tmp == 'KO':
                    err = self.recvall(length)
                toclose = False
                res = (self.sock, length, err)
            else:
                res = self.recvall(length).decode('UTF-8')
        except IOError as e:
            if not restarted and e.errno == errno.EPIPE:
                toclose = True
                return self.do_command(data, True)
            elif e.errno == errno.ECONNRESET:
                self.app.logger.error('!!! {} !!!\nPlease check your SSL configuration on both sides!'.format(str(e)))
            else:
                toclose = True
                self.app.logger.error('!!! {} !!!\n{}'.format(str(e), traceback.format_exc()))
        except Exception as e:
            toclose = True
            self.app.logger.error('!!! {} !!!\n{}'.format(str(e), traceback.format_exc()))
        finally:
            self.close(toclose)

        return res

    def recvall(self, length=1024):
        """Read the answer of the agent"""
        buf = b''
        bsize = 1024
        received = 0
        if length < bsize:
            bsize = length
        while received < length:
            newbuf = self.sock.recv(bsize)
            if not newbuf:
                return None
            buf += newbuf
            received += len(newbuf)
        return buf

    """
    Utilities functions
    """

    def status(self, query='\n', agent=None):
        """See :func:`burpui.misc.backend.interface.BUIbackend.status`"""
        data = {'func': 'status', 'args': {'query': query}}
        return json.loads(self.do_command(data))

    def get_backup_logs(self, number, client, forward=False, agent=None):
        """See :func:`burpui.misc.backend.interface.BUIbackend.get_backup_logs`"""
        data = {'func': 'get_backup_logs', 'args': {'number': number, 'client': client, 'forward': forward}}
        return json.loads(self.do_command(data))

    def get_clients_report(self, clients, agent=None):
        """See :func:`burpui.misc.backend.interface.BUIbackend.get_clients_report`"""
        data = {'func': 'get_clients_report', 'args': {'clients': clients}}
        return json.loads(self.do_command(data))

    def get_counters(self, name=None, agent=None):
        """See :func:`burpui.misc.backend.interface.BUIbackend.get_counters`"""
        data = {'func': 'get_counters', 'args': {'name': name}}
        return json.loads(self.do_command(data))

    def is_backup_running(self, name=None, agent=None):
        """See :func:`burpui.misc.backend.interface.BUIbackend.is_backup_running`"""
        data = {'func': 'is_backup_running', 'args': {'name': name}}
        return json.loads(self.do_command(data))

    def is_one_backup_running(self, agent=None):
        """See :func:`burpui.misc.backend.interface.BUIbackend.is_one_backup_running`"""
        data = {'func': 'is_one_backup_running', 'args': {'agent': agent}}
        return json.loads(self.do_command(data))

    def get_all_clients(self, agent=None):
        """See :func:`burpui.misc.backend.interface.BUIbackend.get_all_clients`"""
        data = {'func': 'get_all_clients', 'args': None}
        return json.loads(self.do_command(data))

    def get_client(self, name=None, agent=None):
        """See :func:`burpui.misc.backend.interface.BUIbackend.get_client`"""
        data = {'func': 'get_client', 'args': {'name': name}}
        return json.loads(self.do_command(data))

    def get_tree(self, name=None, backup=None, root=None, agent=None):
        """See :func:`burpui.misc.backend.interface.BUIbackend.get_tree`"""
        data = {'func': 'get_tree', 'args': {'name': name, 'backup': backup, 'root': root}}
        return json.loads(self.do_command(data))

    def restore_files(self, name=None, backup=None, files=None, strip=None, archive='zip', password=None, agent=None):
        """See :func:`burpui.misc.backend.interface.BUIbackend.restore_files`"""
        data = {'func': 'restore_files', 'args': {'name': name, 'backup': backup, 'files': files, 'strip': strip, 'archive': archive, 'password': password}}
        return self.do_command(data)

    def read_conf_cli(self, client=None, conf=None, agent=None):
        """See :func:`burpui.misc.backend.interface.BUIbackend.read_conf_cli`"""
        data = {'func': 'read_conf_cli', 'args': {'conf': conf, 'client': client}}
        return json.loads(self.do_command(data))

    def read_conf_srv(self, conf=None, agent=None):
        """See :func:`burpui.misc.backend.interface.BUIbackend.read_conf_srv`"""
        data = {'func': 'read_conf_srv', 'args': {'conf': conf}}
        return json.loads(self.do_command(data))

    def store_conf_cli(self, data, client=None, conf=None, agent=None):
        """See :func:`burpui.misc.backend.interface.BUIbackend.store_conf_cli`"""
        # serialize data as it is a nested dict
        # TODO: secure the serialization
        data = {'func': 'store_conf_cli', 'args': pickle.dumps({'data': data, 'conf': conf, 'client': client}), 'pickled': True}
        return json.loads(self.do_command(data))

    def store_conf_srv(self, data, conf=None, agent=None):
        """See :func:`burpui.misc.backend.interface.BUIbackend.store_conf_srv`"""
        # serialize data as it is a nested dict
        # TODO: secure the serialization
        data = {'func': 'store_conf_srv', 'args': pickle.dumps({'data': data, 'conf': conf}), 'pickled': True}
        return json.loads(self.do_command(data))

    def expand_path(self, path=None, client=None, agent=None):
        """See :func:`burpui.misc.backend.interface.BUIbackend.expand_path`"""
        data = {'func': 'expand_path', 'args': {'path': path, 'client': client}}
        return json.loads(self.do_command(data))

    def delete_client(self, client=None, agent=None):
        """See :func:`burpui.misc.backend.interface.BUIbackend.delete_client`"""
        data = {'func': 'delete_client', 'args': {'client': client}}
        return json.loads(self.do_command(data))

    def clients_list(self, agent=None):
        """See :func:`burpui.misc.backend.interface.BUIbackend.clients_list`"""
        data = {'func': 'clients_list', 'args': None}
        return json.loads(self.do_command(data))

    def get_parser_attr(self, attr=None, agent=None):
        """See :func:`burpui.misc.backend.interface.BUIbackend.get_parser_attr`"""
        data = {'func': 'get_parser_attr', 'args': {'attr': attr}}
        return json.loads(self.do_command(data))

    def schedule_restore(self, name=None, backup=None, files=None, strip=None, force=None, prefix=None, restoreto=None, agent=None):
        """See :func:`burpui.misc.backend.interface.BUIbackend.schedule_restore`"""
        data = {'func': 'schedule_restore', 'args': {'name': name, 'backup': backup, 'files': files, 'strip': strip, 'force': force, 'prefix': prefix, 'restoreto': restoreto}}
        return json.loads(self.do_command(data))
