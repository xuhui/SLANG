#! /usr/bin/python

import urllib2
import sys
import os
import logging
import threading
import signal
import httplib
from twisted.web import xmlrpc, server
from twisted.internet import reactor

import config
import probestore
import maintainer
import probed
import remoteproc

class Manager:

    manager_host = None
    cfg_path = None
    probed_cfg_path = "/tmp/probed.conf"

    logger = None
    config = None
    server = None
    pstore = None
    probed = None
    maintainer = None

    thread_stop = False

    def __init__(self, cfg_path):
        """ Constructor """

        # reload
        self.logger = logging.getLogger(self.__class__.__name__)

        self.cfg_path = cfg_path
        self.config = config.Config(self.cfg_path)
        try:
            self.config_url = self.config.get_param('config_url') 
        except config.ConfigError, e:
            raise ManagerError()

        # fetch configuration
        try:
            self.reload()      

        except ManagerError, e:

            # if there is an existing config file, use it
            if os.path.isfile(self.probed_cfg_path):
                self.logger.info("using existing config")

            else:
                # Otherwise, try to write an empty one for probed
                self.logger.warning("writing empty config")
                try:
                    f = open(self.probed_cfg_path, "w")
                    f.write("<config></config>")
                    f.close()
                except IOError, e:
                    self.logger.critical("unable to write empty config: %s" % str(e))

        try:
            self.pstore = probestore.ProbeStore()
            self.maintainer = maintainer.Maintainer(self.pstore)
            self.probed = probed.Probed(self.pstore, self.probed_cfg_path)

            # Create XML-RPC server
            self.xmlrpc = remoteproc.RemoteProc(self.pstore, self)
            xmlrpc.addIntrospection(self.xmlrpc)
            reactor.listenTCP(8000, server.Site(self.xmlrpc))

        except Exception, e:
            self.logger.critical("Cannot start: %s" % e)
            self.stop()


    def reload(self):
        """ Reload 

           Fetches probe configuration from central node and saves to disk.
           Then, send a SIGHUP to the probe application to make it reload
           the configuration.
        """

        self.logger.info("received reload request")

        try:
            # fetch probed config
            f_cfg = urllib2.urlopen(self.config_url, timeout=5)
            cfg_data = f_cfg.read()

            # write to disk
            probed_cfg_file = open(self.probed_cfg_path, "w")
            probed_cfg_file.write(cfg_data)
            probed_cfg_file.close()

        except (urllib2.URLError, IOError), e:
            estr = str("unable to fetch probed config (%s): %s" % (e.__class__.__name__, str(e)))
            self.logger.critical(estr)
            raise ManagerError(estr)

        # send SIGHUP
        if self.probed is not None:
            self.probed.reload()

    
    def recv_config(self, cfg_data):
        """ Save config 'cfg_data' to disk and reload application. """

        self.logger.info("received configuration")

        # write to disk
        try:
            probed_cfg_file = open(self.probed_cfg_path, "w")
            probed_cfg_file.write(cfg_data)
            probed_cfg_file.close()
        except IOError, e:
            estr = str("Unable to write config file: %s" % str(e))
            self.logger.critical(estr)
            raise ManagerError(estr)

        # send SIGHUP
        if self.probed is not None:
            self.probed.reload()

    
    def sighandler(self, signum, frame):
        """ Signal handler. """

        if signum == signal.SIGINT or signum == signal.SIGTERM:
            self.stop()


    def stop(self):
        """ Stop everything """

        self.logger.info("Stopping all threads...")

        # stop threads
        try:
            self.maintainer.stop()
        except:
            pass

        try:
            self.probed.stop()
        except:
            pass

        try:
            self.pstore.stop()
        except:
            pass

        try:
            reactor.stop()
        except:
            pass

        # wait for threads to finish...
        self.logger.debug("Waiting for maintainer...")
        try:
            self.maintainer.join()
        except:
            pass

        self.logger.debug("Maintainer done. Waiting for probed...")

        try:
            self.probed.join()
        except:
            pass

        self.logger.debug("Probed done.")


    def run(self):
        """ Start the application """

        self.logger.info("Starting execution")
        
        # start threads
        try:
            self.probed.start()
            self.maintainer.start()
        except:
            self.logger.error("Unable to start threads.")

        reactor.run()

        self.logger.info("Exiting...")


class ManagerError(Exception):
    pass
