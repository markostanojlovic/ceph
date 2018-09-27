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

class DeepSea(Task):
    """
    Install DeepSea on the Salt Master node.

    Assumes a Salt cluster is already running (use the Salt task to achieve this).

    This task understands the following config keys:

        repo: (DeepSea git repo, e.g. https://github.com/SUSE/DeepSea.git)
        branch: (DeepSea git branch, e.g. master)
        install:
            package|pkg deepsea will be installed via package system
            source|src  deepsea will be installed via 'make install' (default)

    Example:

        tasks
        - deepsea:
            repo: https://github.com/SUSE/DeepSea.git
            branch: wip-foo
            install: source

    :param ctx: the argparse.Namespace object
    :param config: the config dict
    """
    def __init__(self, ctx, config):
        super(DeepSea, self).__init__(ctx, config)

        def _check_config_key(key, default_value):
            if key not in self.config or not self.config[key]:
                self.config[key] = default_value

        _check_config_key('install', 'source')
        _check_config_key('repo', 'https://github.com/SUSE/DeepSea.git')
        _check_config_key('branch', 'master')

        log.debug("Munged config is {}".format(self.config))

        self.su = SaltUtil(self.ctx, self.config)

    def __make_install(self):
        self.log.info("DeepSea repo: {}".format(self.config["repo"]))
        self.log.info("DeepSea branch: {}".format(self.config["branch"]))

        self.salt.master_remote.run(args=[
            'git',
            '--version',
            run.Raw(';'),
            'git',
            'clone',
            '--branch',
            self.config["branch"],
            self.config["repo"],
            run.Raw(';'),
            'cd',
            'DeepSea',
            run.Raw(';'),
            'git',
            'rev-parse',
            '--abbrev-ref',
            'HEAD',
            run.Raw(';'),
            'git',
            'rev-parse',
            'HEAD',
            run.Raw(';'),
            'git',
            'describe',
            run.Raw('||'),
            'true',
            ])

        self.log.info("Running \"make install\" in DeepSea clone...")
        self.salt.master_remote.run(args=[
            'cd',
            'DeepSea',
            run.Raw(';'),
            'sudo',
            'make',
            'install',
            ])

        self.log.info("installing deepsea dependencies...")
        self.salt.master_remote.run(args = [
            'sudo',
            'zypper',
            '--non-interactive',
            'install',
            '--no-recommends',
            run.Raw('$(rpmspec --requires -q DeepSea/deepsea.spec.in 2>/dev/null)')
            ])

    def __purge_osds(self):
        # FIXME: purge osds only on nodes that have osd role
        for _remote in self.ctx.cluster.remotes.iterkeys():
            self.log.info("stopping OSD services on {}"
                .format(_remote.hostname))
            _remote.run(args=[
                'sudo', 'sh', '-c',
                'systemctl stop ceph-osd.target ; sleep 10'
                ])
            self.log.info("unmounting OSD partitions on {}"
                .format(_remote.hostname))
            # bluestore XFS partition is vd?1 - unmount up to five OSDs
            _remote.run(args=[
                'sudo', 'sh', '-c',
                'for f in vdb1 vdc1 vdd1 vde1 vdf1 ; do test -b /dev/$f && umount /dev/$f || true ; done'
                ])
            # filestore XFS partition is vd?2 - unmount up to five OSDs
            _remote.run(args=[
                'sudo', 'sh', '-c',
                'for f in vdb2 vdc2 vdd2 vde2 vdf2; do test -b /dev/$f && umount /dev/$f || true ; done'
                ])

    def setup(self):
        super(DeepSea, self).setup()
        log.info("DeepSea task setup...")
        if self.config['install'] in ['source', 'src']:
            self.__make_install()
        elif self.config['install'] in ['package', 'pkg']:
            self.salt.master_remote.run(args=[
                'sudo',
                'zypper',
                '--non-interactive',
                'install',
                'deepsea',
                'deepsea-cli',
                'deepsea-qa'
                ])
        else:
            raise ConfigError("Unsupported deepsea install method '%s'"
                                                % self.config['install'])

    def begin(self):
        super(DeepSea, self).begin()
        log.info("DeepSea task begin...")
        self.salt.master_remote.run(args=[
            'sudo',
            'rpm',
            '-q',
            'ceph-test'
            ])
        suite_path = self.ctx.config.get('suite_path')
        log.info("suite_path is ->{}<-".format(suite_path))
        log.info("deepsea task complete")

    def end(self):
        super(DeepSea, self).end()
        log.info("DeepSea task end...")
        self.su.gather_logfile('deepsea.log')
        self.su.gather_logs('ganesha')

    def teardown(self):
        super(DeepSea, self).teardown()
        log.info("DeepSea task teardown...")
        self.__purge_osds()


task = DeepSea
