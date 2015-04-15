import os
import logging
from paramiko import SSHClient, AutoAddPolicy
from paramiko.ssh_exception import SSHException
from paramiko.ssh_exception import AuthenticationException
from paramiko.ssh_exception import BadHostKeyException

#TODO Improve __setattr__ for human error


class Device(object):
    def __init__(self, host, username, password):
        self.host = host
        self.username = username
        self.password = password
        self.session = SSHClient()
        self.session.set_missing_host_key_policy(AutoAddPolicy())
        self.connect()
        self.transport = self.session.get_transport()

    def __getattr__(self, name):
        name = name.replace('_', '.')
        values = self.run("grep '{0}' /tmp/system.cfg".format(name))
        if len(values) == 1:
            name_length = len(name) + 1
            value = values[0].rstrip()[name_length:]
            if value == "enabled":
                return True
            elif value == "disabled":
                return False
            else:
                return values[0].rstrip()[name_length:]
        else:
            logging.warning("Attribute '%s' not found!", name)
            return super(Device, self).__getattribute__(name)

    def __setattr__(self, name, value):
        try:
            name = name.replace("_", ".")

            if value is True:
                value = "enabled"
            elif value is False:
                value = "disabled"

            cmd = "sed -i '/{0}/ c {0}={1}' /tmp/system.cfg".format(name, value)
            return self.run(cmd)
        except RuntimeError:
            super(Device, self).__setattr__(name, value)

    def connect(self):
        try:
            self.session.connect(self.host,
                                 username=self.username,
                                 password=self.password)
        except AuthenticationException:
            logging.error("Incorrect username/password by host %s",
                           self.host)
        except (BadHostKeyException, SSHException) as e:
            logging.error("Connection refused: %s. By host %s",
                          e, self.host)

    def run(self, command):
        stdin, stdout, stderr = self.session.exec_command(command)
        return stdout.readlines()

    def apply(self):
        return self.run("cfgmtd -w")

    # Don't like this...needs to be using SFTPClient()
    def upload(self, local_file, to="/tmp/upload/"):
        with open(local_file, "r") as f:
            return self.run("printf '{0}' > {1}{2}".format("".join(f.read()),
                to, os.path.basename(local_file)))

    # Real upload to be implemented later
    # def upload(self, local_file, to="/tmp/uploads"):
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
            "tinysnmpd --daemon /etc/snmp.conf /lib/tinysnmp --logfile /tmp/snmp.log")


class Radio(Device):
    def __init__(self, ip, username, password):
        super().__init__(ip, username, password)


class Router(Device):
    def __init__(self, ip, username, password):
        super().__init__(ip, username, password)
