# -*- coding: utf-8 -*-

from __future__ import print_function
import os
import sys
import argparse
import subprocess
from . import aws_iam_utils
from .aws_util_exceptions import RoleNotFoundError
from .aws_util_exceptions import AssumeRoleError


def set_environ(key, value, verbose = None):
    os.environ[key] = value
    if verbose:
        print("{}={}".format(key, value))


def start_with_credentials(
          access_key,
          secret_key,
          session_token,
          region,
          command,
          verbose):
    set_environ('AWS_ACCESS_KEY_ID', access_key, verbose)
    set_environ('AWS_SECRET_ACCESS_KEY', secret_key, verbose)
    set_environ('AWS_SESSION_TOKEN', session_token, verbose)
    if region:
        set_environ('AWS_DEFAULT_REGION', region, verbose)
        set_environ('AWS_REGION', region, verbose)
    # ensure stdout flows without being buffered
    set_environ('PYTHONUNBUFFERED', '1', verbose)
    exit_code = exec_command(command)
    return exit_code


def exec_command(command):
    """Shell execute a command and return the exit code."""
    try:
        p = subprocess.Popen(command, shell=True)
        p.communicate()
    except Exception as e:
        print("Error executing command: {}".format(e))
        return 1
    return p.returncode


def print_shell_sts_commands(
          access_key,
          secret_key,
          session_token,
          role,
          profile):
    print('export AWS_ACCESS_KEY_ID="{}"'.format(access_key))
    print('export AWS_SECRET_ACCESS_KEY="{}"'.format(secret_key))
    print('export AWS_SESSION_TOKEN="{}"'.format(session_token))
    print('# Run this to configure your shell:')
    print('# eval $(iam-starter --role {}{})'.format(
      role,
      ' --profile {}'.format(profile) if profile else ''))


def create_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('--role', required=True,
                        help='The AWS IAM role name to assume')
    parser.add_argument('--profile', required=False,
                        help='The AWS creds used on your laptop to generate the STS temp credentials')
    parser.add_argument('--region', required=False,
                        help='The AWS region to default to')
    parser.add_argument('--verbose', action='store_true', default=False)
    parser.add_argument('--command', nargs=argparse.REMAINDER,
                        help='The program to execute after the IAM role is assumed')
    return parser


def main():
    here = os.path.abspath(os.path.dirname(__file__))
    about = {}
    with open(os.path.join(here, 'version.py'), 'r') as f:
        exec(f.read(), about)

    print('IAM Starter version {}'.format(about['__version__']))

    args = create_parser().parse_args()

    region = args.region or \
             os.environ.get('AWS_REGION',
             os.environ.get('AWS_DEFAULT_REGION', None))

    try:
        access_key, secret_key, session_token, role_arn = \
            aws_iam_utils.generate_aws_temp_creds(
              args.role, profile=args.profile, verbose=args.verbose)
        if args.verbose:
            print("Role arn: {}".format(role_arn))
        print("Generated temporary AWS credentials: {}".format(access_key))
    except RoleNotFoundError as e:
        try:
            account_id = aws_iam_utils.get_aws_account_id(args.profile)
        except Exception as e:
            if args.verbose:
                print("Error retrieving AWS Account ID: {}".format(str(e)))
            account_id = 'error'
        print("IAM role '{}' not found in account id {}, credential method: {}".format(
            args.role,
            account_id,
            e.credential_method
        ))
        sys.exit(1)
    except AssumeRoleError as e:
        if args.verbose:
            print(str(e))
        try:
            account_id = aws_iam_utils.get_aws_account_id(args.profile)
        except Exception as e:
            if args.verbose:
                print("Error retrieving AWS Account ID: {}".format(str(e)))
            account_id = 'error'
        print("Error assuming IAM role '{}' from account id {}, credential method: {}, error: {}".format(
            args.role,
            account_id,
            e.credential_method,
            e
        ))
        sys.exit(1)

    command = ' '.join(args.command)
    print(command)
    exit_code = None
    if args.command:
        exit_code = start_with_credentials(
          access_key,
          secret_key,
          session_token,
          region,
          command,
          args.verbose
          )
        print("IAM Starter - application ended with exit code {}".format(exit_code))
    else:
        print_shell_sts_commands(
          access_key,
          secret_key,
          session_token,
          args.role,
          args.profile
        )
    
    sys.exit(exit_code if exit_code else 0)
