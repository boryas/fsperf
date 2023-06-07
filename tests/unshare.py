from PerfTest import FioTest
import os
import subprocess
import utils

NR_SNAPS = 100
NR_FILES = 1000

# Measure the performance of writes that unshare snapshotted files.
class Unshare(FioTest):
    name = "unshare"
    use_opendir = True
    command = ("--name unshare --rw=randwrite --fsync=1 "
               "--filesize=128k --ioengine=psync --bs=4k")

    def __init__(self):
        self.bg_fios = {}

    def get_directory(self, config):
        base = config.get('main', 'directory')
        return os.path.join(base, "snap.victim")

    def setup(self, config, section):
        directory = config.get('main', 'directory')
        subv = os.path.join(directory, 'subv')
        victim = self.get_directory(config)
        utils.run_command(f'btrfs subvolume create {subv}')

        # fill out the subvolume
        utils.run_command(f'fio --name prep --directory={subv} --rw=write --ioengine=psync --bs=4k --filesize=128k --nrfiles={NR_FILES}')

        # create the snapshots
        utils.run_command(f'btrfs subvolume snapshot {subv} {victim}')
        for i in range(NR_SNAPS):
            snap = os.path.join(directory, f'snap.{i}')
            utils.run_command(f'btrfs subvolume snapshot {subv} {snap}')

        # start, but don't block on overwrites
        for i in range(NR_SNAPS):
            snap = os.path.join(directory, f'snap.{i}')
            self.bg_fios[i] = utils.run_command(f'fio --name overwrite.{i} --opendir={snap} --rw=randwrite --ioengine=psync --bs=4k --filesize=128k --overwrite=1 --fsync=1', outputfile=None, fg=False)

    def teardown(self, config, results):
        for i in range(NR_SNAPS):
            self.bg_fios[i].kill()
            self.bg_fios[i].communicate()
