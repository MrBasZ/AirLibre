import textwrap
from collections import namedtuple
from paramiko import SSHClient, AutoAddPolicy
from scp import SCPClient

class Device(object):
    def __init__(self, host, username, password):
        self.host = host
        self.username = username
        self.password = password
        self.session = SSHClient()
        self.session.set_missing_host_key_policy(AutoAddPolicy())
        self.connect()

    def __repr__(self):
        return '{0}{1}'.format(self.__class__.__name__, self.host)

    @classmethod
    def auto_detect(cls, host, username, password):
        generic_device = cls(host, username, password)
        model = generic_device.model()

        if 'AirFiber' in model:
            return AirFiber(generic_device.host,
                    generic_device.username,
                    generic_device.password,
                    generic_device.session)
        else:
            return generic_device


    def connect(self):
        self.session.connect(self.host, username=self.username,
                password=self.password)

    def transport(self):
        return self.session.get_transport()

    def scp(self):
        return SCPClient(self.transport())

    def download_conf(self, local_path=''):
        return self.scp().get('/tmp/system.cfg', local_path=local_path)

    def run(self, command):
        stdin, stdout, stderr = self.session.exec_command(command)
        output = [line.rstrip() for line in stdout.readlines()]
        return list(output)

    def read_conf(self, name, config="/tmp/system.cfg"):
        values = self.run('grep "{0}=" {1}'.format(name, config))

        if len(values) == 1:
            name_length = len(name) + 1  # Plus 1 to ignore '=' in config
            value = values[0][name_length:]

            if value == 'enabled':
                return True
            elif value == 'disabled':
                return False
            else:
                return values[0][name_length:]
        else:
            raise AttributeError

    def apply(self):
        return self.run('cfgmtd -w -p /etc/')

    def restart(self):
        return self.run('/usr/etc/rc.d/rc.softrestart save')

    def disconnect(self):
        self.session.close()

    def version(self):
        return self.run('cat /etc/version')[0]

    def hostname(self):
        return self.read_conf('resolv.host.1.name')

    def frequency(self):
        if self.mode() == 'managed':
            return self.live_frequency()
        freq = self.read_conf('radio.1.freq')
        if freq != '0':
            return int(freq)
        else:
            return self.live_frequency()

    def channel_width(self):
        try:
            clksel = self.read_conf('radio.1.clksel')
            chanbw = self.read_conf('radio.1.chanbw')
            if clksel == '4':
                return 5
            elif clksel == '2':
                if chanbw == '8':
                    return int(chanbw)
                else:
                    return 10
            elif clksel == '1':
                if chanbw == '30':
                    return int(chanbw)
                else:
                    return 20
        except AttributeError:
            chanbw = self.read_conf('radio.1.chanbw')
            return int(chanbw)

    def channel_shift(self):
        try:
            if self.read_conf('radio.1.chanshift') == '0':
                return 'disabled'
            else:
                return 'enabled'
        except AttributeError:
            return None

    def txpower(self):
        return int(self.read_conf('radio.1.txpower'))

    def distance(self):
        model = self.model()
        if model == 'airFiber 24G' or model == 'airFiber 5' or model == 'airFiber 5X':
            return None
        return self.read_conf('radio.1.ackdistance')

    def distance_miles(self):
        distance = self.distance()
        if distance is not None:
            return round(int(distance) * 0.00062137, 1)
        else:
            return None

    def mac_address(self):
        mac = self.read_conf('board.hwaddr', '/etc/board.info')
        return ':'.join(textwrap.wrap(mac, 2))

    def model(self):
        return self.read_conf('board.name', '/etc/board.info')

    def mode(self):
        return self.read_conf('radio.1.mode')

    def wds(self):
        return self.read_conf('wireless.1.wds.status')

    def live(self):
        return self.run('iwconfig 2> /dev/null')[0]

    def live_frequency(self):
        cmd = 'iwconfig 2> /dev/null | grep Mode | cut -d ":" -f3 | cut -d " " -f1'
        freq = self.run(cmd)[0].replace('.','')

        if freq.startswith('9'):
            return int(freq)
        elif len(freq) == 3:
            return int(freq + '0')
        elif len(freq) == 2:
            return int(freq + '00')
        else:
            return int(freq)


class AirFiber(Device):
    def __init__(self, host, username, password, session=None):
        self.host = host
        self.username = username
        self.password = password

        if session is None:
            self.session = SSHClient()
            self.session.set_missing_host_key_policy(AutoAddPolicy())
        else:
            self.session = session

    def channel_width(self):
        rxchanbw = self.read_conf('radio.1.rxchanbw')

        if rxchanbw == '256':
            rxchanbw = '40'
        elif rxchanbw == '128':
            rxchanbw = '30'
        elif rxchanbw == '64':
            rxchanbw = '20'
        else:
            rxchanbw = '10'

        txchanbw = self.read_conf('radio.1.txchanbw')

        if txchanbw == '256':
            txchanbw = '40'
        elif txchanbw == '128':
            txchanbw = '30'
        elif txchanbw == '64':
            txchanbw = '20'
        else:
            txchanbw = '10'

        Bandwidth = namedtuple('Bandwidth', ['rx', 'tx'])
        return Bandwidth(rxchanbw, txchanbw)

    def frequency(self):
        Frequency = namedtuple('Frequency', ['rx', 'tx'])
        return Frequency(self.read_conf('radio.1.tx_freq'),
                            self.read_conf('radio.1.rx_freq'))
