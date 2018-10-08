'''
Task that deploys a Ceph cluster using DeepSea
'''
import logging
import os.path
import time

from salt_util import SaltUtil
from teuthology import misc
from teuthology.exceptions import (CommandFailedError, ConfigError)
from teuthology.orchestra import run
from teuthology.task import Task

log = logging.getLogger(__name__)

class Survive(Task):
    """
    Handles any command that potentially causes a reboot on the node

    Assumes a Salt cluster is already running (use the Salt task to achieve this).

    This task understands the following config keys:

        command: (Any command, salt-run state.orch ceph.stage.0)

    Example:

        tasks:
        - survive:
            command: salt-run state.orch ceph.stage.0

    :param ctx: the argparse.Namespace object
    :param config: the config dict
    """
    def __init__(self, ctx, config):
        super(Survive, self).__init__(ctx, config)

        def _check_config_key(key, default_value):
            if key not in self.config or not self.config[key]:
                self.config[key] = default_value

        _check_config_key('command', 'touch test.patch')

        log.debug("Munged config is {}".format(self.config))

        self.su = SaltUtil(self.ctx, self.config)

    def __exec_cmd(self):
        self.log.info("command to execute: {}".format(self.config["command"]))

        self.salt.master_remote.run(args=[
            self.config["command"],
            ])


    def setup(self):
        super(Survive, self).setup()
        log.info("Survive task setup...")
        log.info("Dummy....")

    def begin(self):
        super(Survive, self).begin()
        log.info("Survive task begin...")
        self.__exec_cmd()
        log.info("deepsea task complete")

    def end(self):
        super(Survive, self).end()
        log.info("Survive task end...")
        self.su.gather_logfile('deepsea.log')

    def teardown(self):
        super(Survive, self).teardown()
        log.info("Survive task teardown...")


task = Survive
