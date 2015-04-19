import os
import logging
from paramiko import SSHClient, AutoAddPolicy
from paramiko.ssh_exception import SSHException
from paramiko.ssh_exception import AuthenticationException
from paramiko.ssh_exception import BadHostKeyException


class Device(object):
    def __init__(self, host, username, password):
        self.__dict__["host"] = host
        self.__dict__["username"] = username
        self.__dict__["password"] = password
        self.__dict__["session"] = SSHClient()
        self.__dict__["transport"] = self.session.get_transport()
        self.session.set_missing_host_key_policy(AutoAddPolicy())
        self.connect()

    def __enter__(self):
        return self

    def __exit__(self):
        self.disconnect()

    def __repr__(self):
        return '{0}{1}'.format(self.__class__.__name__, self.host)

    def __getattr__(self, name):
        config_name = name.replace('_', '.')
        values = self.run('grep "{0}" /tmp/system.cfg'.format(config_name))

        if len(values) == 1:
            name_length = len(name) + 1 # Plus 1 to ignore '=' in config
            value = values[0][name_length:]

            if value == 'enabled':
                return True
            elif value == 'disabled':
                return False
            else:
                return values[0][name_length:]
        else:
            raise AttributeError

    def __setattr__(self, name, value):
        try:
            getattr(self, name)
        except AttributeError:
            raise
        else:
            config_name = name.replace('_', '.')

            if value is True:
                value = 'enabled'
            elif value is False:
                value = 'disabled'

            cmd = 'sed -i "/{0}/ c {0}={1}" /tmp/system.cfg'.format(config_name, value)
            self.run(cmd)

    def __delattr__(self, name):
        try:
            getattr(self, name)
        except AttributeError:
            raise
        else:
            name = name.replace('_', '.')
            cmd = 'sed -i /{0}/d /tmp/system.cfg'.format(name)
            self.run(cmd)

    def connect(self):
        try:
            self.session.connect(self.host, username=self.username,
                                 password=self.password)
        except AuthenticationException:
            logging.error('Incorrect username/password by host %s', self.host)
        except (BadHostKeyException, SSHException) as e:
            logging.error('Connection refused: %s. By host %s', e, self.host)

    def run(self, command):
        stdin, stdout, stderr = self.session.exec_command(command)
        output = map(lambda x: x.rstrip(), stdout.readlines())
        return list(output)

    def apply(self):
        return self.run('cfgmtd -w')

    # Don't like this...needs to be using SFTPClient()
    def upload(self, local_file, to='/tmp/upload/'):
        with open(local_file, 'r') as f:
            return self.run('printf "{0}" > {1}{2}'.format(''.join(f.read()),
                to, os.path.basename(local_file)))

    # Real upload to be implemented later
    # def upload(self, local_file, to='/tmp/uploads'):
    #     file_session = self.session.open_sftp()
    #     file_session.put(local_file, '{0}/{1}'.format(to, local_file))
    #     file_session.close()

    def disconnect(self):
        self.session.close()

    def is_alive(self):
        return self.transport.is_alive()

    # Daemons
    def start_snmp_daemon(self):
        return self.run(
            'tinysnmpd --daemon /etc/snmp.conf /lib/tinysnmp --logfile /tmp/snmp.log')
