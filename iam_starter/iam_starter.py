# -*- coding: utf-8 -*-

from __future__ import print_function
import os
import sys
import argparse
import subprocess
from . import aws_iam_utils
from .aws_util_exceptions import ProfileParsingError
from .aws_util_exceptions import RoleNotFoundError
from .aws_util_exceptions import AssumeRoleError


def set_environ(key, value, verbose = None):
    os.environ[key] = value
    if verbose:
        print("{}={}".format(key, value))


def start_with_credentials(
        aws_creds,
        region,
        command,
        verbose):
    set_environ('AWS_ACCESS_KEY_ID', aws_creds['AWS_ACCESS_KEY_ID'], verbose)
    set_environ('AWS_SECRET_ACCESS_KEY', aws_creds['AWS_SECRET_ACCESS_KEY'], verbose)
    if 'AWS_SESSION_TOKEN' in aws_creds:
        set_environ('AWS_SESSION_TOKEN', aws_creds['AWS_SESSION_TOKEN'], verbose)
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
        aws_creds,
        role,
        profile):
    print('# Run these statements in your shell')
    print('# or specify a --command argument to execute a command within this IAM context')
    print('export AWS_ACCESS_KEY_ID="{}"'.format(aws_creds['AWS_ACCESS_KEY_ID']))
    print('export AWS_SECRET_ACCESS_KEY="{}"'.format(aws_creds['AWS_SECRET_ACCESS_KEY']))
    if 'AWS_SESSION_TOKEN' in aws_creds:
        print('export AWS_SESSION_TOKEN="{}"'.format(aws_creds['AWS_SESSION_TOKEN']))
    print('# To clear, use:')
    print('unset AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN')


def get_aws_creds(profile_name=None, role_name=None, verbose=False):
    aws_creds = {}
    role_arn = None

    if profile_name:
        if verbose:
            print("Reading AWS profile {}".format(profile_name))
        aws_creds = aws_iam_utils.get_aws_profile_credentials(profile_name, verbose)
    else:
        # if a profile isn't specified, get the creds from the environment
        access_key_id = os.environ.get('AWS_ACCESS_KEY_ID', None)
        if not access_key_id:
            msg = "No AWS profile specified and no AWS credentials found in the environment."
            raise ProfileParsingError(msg)
        if verbose:
            print("Starting with AWS creds in environment ({})".format(
                access_key_id
            ))
        aws_creds = {
            'AWS_ACCESS_KEY_ID': access_key_id,
            'AWS_SECRET_ACCESS_KEY': os.environ.get('AWS_SECRET_ACCESS_KEY', None),
            'AWS_SESSION_TOKEN': os.environ.get('AWS_SESSION_TOKEN', None)
        }

    # if the profile itself specifies a role, first assume that role
    if 'role_arn' in aws_creds:
        print("Assuming role specified in profile {}: {}".format(
            profile_name, aws_creds['role_arn']
        ))
        aws_creds = aws_iam_utils.generate_aws_temp_creds(
            role_arn=aws_creds['role_arn'],
            aws_creds=aws_creds,
            verbose=verbose
        )

    # then if --role argument given here, further assume that role
    if role_name:
        if verbose:
            print("Looking up role arn from role name: {}".format(role_name))
        role_arn = aws_iam_utils.get_role_arn_from_name(
            aws_creds,
            role_name,
            verbose=verbose)
        print("Assuming role given as argument: {}".format(role_arn))
        aws_creds = aws_iam_utils.generate_aws_temp_creds(
            role_arn=role_arn,
            aws_creds=aws_creds,
            verbose=verbose
        )
    
    return aws_creds


def create_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('--role', required=False,
                        help='The AWS IAM role name to assume')
    parser.add_argument('--profile', required=False,
                        help='The AWS creds used on your laptop to generate the STS temp credentials')
    parser.add_argument('--region', required=False,
                        help='The AWS region to default to')
    parser.add_argument('--verbose', action='store_true', default=False)
    parser.add_argument('--command', required=False, nargs=argparse.REMAINDER,
                        help='The program to execute after the IAM role is assumed')
    return parser


def main():
    here = os.path.abspath(os.path.dirname(__file__))
    about = {}
    with open(os.path.join(here, 'version.py'), 'r') as f:
        exec(f.read(), about)

    print('IAM Starter version {}'.format(about['__version__']))

    parser = create_parser()
    args = parser.parse_args()

    if not args.profile and not args.role:
        parser.print_help()
        print('You must specify --profile and/or --role')
        sys.exit(1)

    region = args.region or \
             os.environ.get('AWS_REGION',
             os.environ.get('AWS_DEFAULT_REGION', None))

    aws_creds = {}
    try:
        aws_creds = get_aws_creds(args.profile, args.role, args.verbose)
    except ProfileParsingError as e:
         print(e)
         sys.exit(1)
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
        credential_method = e.credential_method if hasattr(e, 'credential_method') else '(unknown)'
        print("Error assuming IAM role '{}' from account id {}, credential method: {}, error: {}".format(
            args.role,
            account_id,
            credential_method,
            e
        ))
        sys.exit(1)

    exit_code = None
    if args.command:
        command = ' '.join(args.command)
        print(command)
        exit_code = start_with_credentials(
            aws_creds,
            region,
            command,
            args.verbose
            )
        print("IAM Starter - application ended with exit code {}".format(exit_code))
    else:
        print_shell_sts_commands(
            aws_creds,
            args.role,
            args.profile
        )
    
    sys.exit(exit_code if exit_code else 0)
