from struct import unpack
from timespec import Timespec

class Probe:
    """ A probe. """

    created = None
    t1 = None
    t2 = None
    t3 = None
    t4 = None

    addr = None
    msess_id = None
    seq = None

    def __init__(self, data):

        data = unpack('llc16siillllllll16s', data)

        self.created = Timespec(data[0], data[1])
        self.state = data[2]
        self.addr = data[3]
        self.msess_id = data[4]
        self.seq = data[5]
        self.t1 = Timespec(data[6], data[7])
        self.t2 = Timespec(data[8], data[9])
        self.t3 = Timespec(data[10], data[11])
        self.t4 = Timespec(data[12], data[13])

    def rtt(self):
        """ Calculates the rtt of the probe. """

        return (self.t4 - self.t1) - (self.t3 - self.t2)

class ProbeSet:
    """ A set of probes. """

    def __init__():
        pass

    def avg_rtt():
        """ Find the average RTT """
        pass

    def mean_rtt():
        """ Find the mean RTT """
        pass
