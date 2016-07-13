# pylint: skip-file

'''
   GcloudCLI class that wraps the oc commands in a subprocess
'''

import string
import random
import json
import os
import yaml
import shutil
import subprocess
import atexit

class GcloudCLIError(Exception):
    '''Exception class for openshiftcli'''
    pass

# pylint: disable=too-few-public-methods
class GcloudCLI(object):
    ''' Class to wrap the command line tools '''
    def __init__(self, credentials=None, verbose=False):
        ''' Constructor for OpenshiftCLI '''
        self.credentials = credentials
        self.verbose = verbose

    def _create_image(self, image_name, image_info):
        '''create an image name'''
        cmd = ['compute', 'images', 'create', image_name]
        for key, val in image_info.items():
            if val:
                cmd.extend(['--%s' % key, val])

        return self.gcloud_cmd(cmd, output=True, output_type='raw')

    def _delete_image(self, image_name):
        '''delete image by name '''
        cmd = ['compute', 'images', 'delete', image_name]
        if image_name:
            cmd.extend(['describe', image_name])
        else:
            cmd.append('list')

        cmd.append('-q')

        return self.gcloud_cmd(cmd, output=True, output_type='raw')

    def _list_images(self, image_name=None):
        '''list images.
           if name is supplied perform a describe and return
        '''
        cmd = ['compute', 'images']
        if image_name:
            cmd.extend(['describe', image_name])
        else:
            cmd.append('list')

        return self.gcloud_cmd(cmd, output=True, output_type='raw')

    def _list_deployments(self, simple=True):
        '''list deployments by name '''
        cmd = ['deployment-manager', 'deployments', 'list']
        if simple:
            cmd.append('--simple-list')
        return self.gcloud_cmd(cmd, output=True, output_type='raw')

    def _delete_deployment(self, dname):
        '''list deployments by name '''
        cmd = ['deployment-manager', 'deployments', 'delete', dname, '-q']
        return self.gcloud_cmd(cmd, output=True, output_type='raw')

    def _create_deployment(self, dname, config=None, opts=None):
        ''' create a deployment'''
        cmd = ['deployment-manager', 'deployments', 'create', dname]
        if config:
            if isinstance(config, dict):
                config = Utils.create_file(dname, config)

            if isinstance(config, str) and os.path.exists(config):
                cmd.extend(['--config=%s' % config])

        if opts:
            for key, val in opts.items():
                cmd.append('--%s=%s' % (key, val))

        return self.gcloud_cmd(cmd, output=True, output_type='raw')

    def _update_deployment(self, dname, config=None, opts=None):
        ''' create a deployment'''
        cmd = ['deployment-manager', 'deployments', 'update', dname]
        if config:
            if isinstance(config, dict):
                config = Utils.create_file(dname, config)

            if isinstance(config, str) and os.path.exists(config):
                cmd.extend(['--config=%s' % config])

        if opts:
            for key, val in opts.items():
                cmd.append('--%s=%s' % (key, val))

        return self.gcloud_cmd(cmd, output=True, output_type='raw')

    def _list_manifests(self, deployment, mname=None):
        ''' list manifests
            if a name is specified then perform a describe
        '''
        cmd = ['deployment-manager', 'manifests', '--deployment', deployment]
        if mname:
            cmd.extend(['describe', mname])
        else:
            cmd.append('list')

        return self.gcloud_cmd(cmd, output=True, output_type='raw')

    def _delete_address(self, aname):
        ''' list addresses
            if a name is specified then perform a describe
        '''
        cmd = ['compute', 'addresses', 'delete', aname, '-q']

        return self.gcloud_cmd(cmd, output=True, output_type='raw')

    def _list_addresses(self, aname=None):
        ''' list addresses
            if a name is specified then perform a describe
        '''
        cmd = ['compute', 'addresses']
        if aname:
            cmd.extend(['describe', aname])
        else:
            cmd.append('list')

        return self.gcloud_cmd(cmd, output=True, output_type='raw')

    def _create_address(self, address_name, address_info, address=None, isglobal=False):
        ''' create a deployment'''
        cmd = ['compute', 'addresses', 'create', address_name]

        if address:
            cmd.append(address)

        if isglobal:
            cmd.append('--global')

        for key, val in address_info.items():
            if val:
                cmd.extend(['--%s' % key, val])

        return self.gcloud_cmd(cmd, output=True, output_type='raw')

    def _list_metadata(self):
        '''create metadata'''
        cmd = ['compute', 'project-info', 'describe']

        return self.gcloud_cmd(cmd, output=True, output_type='raw')

    def _delete_metadata(self, keys, remove_all=False):
        '''create metadata'''
        cmd = ['compute', 'project-info', 'remove-metadata']

        if remove_all:
            cmd.append('--all')

        else:
            cmd.append('--keys')
            cmd.append(','.join(keys))

        cmd.append('-q')

        return self.gcloud_cmd(cmd, output=True, output_type='raw')

    def _create_metadata(self, metadata=None, metadata_from_file=None):
        '''create metadata'''
        cmd = ['compute', 'project-info', 'add-metadata']

        data = None

        if metadata_from_file:
            cmd.append('--metadata-from-file')
            data = metadata_from_file
        else:
            cmd.append('--metadata')
            data = metadata

        cmd.append(','.join(['%s=%s' % (key, val) for key, val in data.items()]))

        return self.gcloud_cmd(cmd, output=True, output_type='raw')

    def _list_service_accounts(self, sa_name=None):
        '''return service accounts '''
        cmd = ['iam', 'service-accounts']
        if sa_name:
            cmd.extend(['describe', sa_name])
        else:
            cmd.append('list')

        cmd.extend(['--format', 'json'])

        return self.gcloud_cmd(cmd, output=True, output_type='json')

    def _delete_service_account(self, sa_name):
        '''delete service account '''
        cmd = ['iam', 'service-accounts', 'delete', sa_name, '-q']

        cmd.extend(['--format', 'json'])

        return self.gcloud_cmd(cmd, output=True, output_type='json')

    def _create_service_account(self, sa_name, display_name=None):
        '''create service account '''
        cmd = ['iam', 'service-accounts', 'create', sa_name]
        if display_name:
            cmd.extend(['--display-name', display_name])

        cmd.extend(['--format', 'json'])

        return self.gcloud_cmd(cmd, output=True, output_type='json')

    def _update_service_account(self, sa_name, display_name=None):
        '''update service account '''
        cmd = ['iam', 'service-accounts', 'update', sa_name]
        if display_name:
            cmd.extend(['--display-name', display_name])

        cmd.extend(['--format', 'json'])

        return self.gcloud_cmd(cmd, output=True, output_type='json')

    def gcloud_cmd(self, cmd, output=False, output_type='json'):
        '''Base command for gcloud '''
        cmds = ['/usr/bin/gcloud']

        cmds.extend(cmd)

        rval = {}
        results = ''
        err = None

        if self.verbose:
            print ' '.join(cmds)

        proc = subprocess.Popen(cmds,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                env={})

        proc.wait()
        stdout = proc.stdout.read()
        stderr = proc.stderr.read()
        rval = {"returncode": proc.returncode,
                "results": results,
                "cmd": ' '.join(cmds),
               }

        if proc.returncode == 0:
            if output:
                if output_type == 'json':
                    try:
                        rval['results'] = json.loads(stdout)
                    except ValueError as err:
                        if "No JSON object could be decoded" in err.message:
                            err = err.message
                elif output_type == 'raw':
                    rval['results'] = stdout

            if self.verbose:
                print stdout
                print stderr

            if err:
                rval.update({"err": err,
                             "stderr": stderr,
                             "stdout": stdout,
                             "cmd": cmds
                            })

        else:
            rval.update({"stderr": stderr,
                         "stdout": stdout,
                         "results": {},
                        })

        return rval

################################################################################
# utilities and helpers for generation
################################################################################
class Utils(object):
    ''' utilities for openshiftcli modules '''

    COMPUTE_URL_BASE = 'https://www.googleapis.com/compute/v1/'

    @staticmethod
    def create_file(rname, data, ftype='yaml'):
        ''' create a file in tmp with name and contents'''
        path = os.path.join('/tmp', rname)
        with open(path, 'w') as fds:
            if ftype == 'yaml':
                fds.write(yaml.safe_dump(data, default_flow_style=False))

            elif ftype == 'json':
                fds.write(json.dumps(data))
            else:
                fds.write(data)

        # Register cleanup when module is done
        atexit.register(Utils.cleanup, [path])
        return path

    @staticmethod
    def global_compute_url(project, collection, rname):
        '''build the global compute url for a resource'''
        return ''.join([Utils.COMPUTE_URL_BASE, 'projects/', project, '/global/', collection, '/', rname])

    @staticmethod
    def zonal_compute_url(project, zone, collection, rname):
        '''build the zone compute url for a resource'''
        return ''.join([Utils.COMPUTE_URL_BASE, 'projects/', project, '/zones/', zone, '/', collection, '/', rname])

    @staticmethod
    def generate_random_name(size):
        '''generate a random string of lowercase and digits the length of size'''
        return ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(size))


    @staticmethod
    def cleanup(files):
        '''Clean up on exit '''
        for sfile in files:
            if os.path.exists(sfile):
                if os.path.isdir(sfile):
                    shutil.rmtree(sfile)
                elif os.path.isfile(sfile):
                    os.remove(sfile)

