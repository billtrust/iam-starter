import uuid
import boto3
from botocore.exceptions import ClientError
from .aws_util_exceptions import RoleNotFoundError
from .aws_util_exceptions import AssumeRoleError


def get_aws_account_id(profile=None):
    if profile:
        session = boto3.Session(profile_name=profile)
        client = session.client('sts')
    else:
        client = boto3.client('sts')
    account_id = client.get_caller_identity()['Account']
    return account_id


def get_credential_method_description(session):
    """Provides a helpful message describing the current IAM execution context."""
    profile = ''
    try:
        profile = session.profile_name
    except:
        pass
    try:
        credentials = session.get_credentials()
        return "{} ({}{})".format(
            credentials.method,
            "profile {} -> ".format(profile) if profile != 'default' else '',
            credentials.access_key
        )
    except:
        return 'error describing session credentials'


def get_boto3_session(aws_creds):
    if aws_creds:
        session_token = None
        if 'AWS_SESSION_TOKEN' in aws_creds:
            session_token = aws_creds['AWS_SESSION_TOKEN']
        return boto3.Session(
            aws_access_key_id=aws_creds['AWS_ACCESS_KEY_ID'],
            aws_secret_access_key=aws_creds['AWS_SECRET_ACCESS_KEY'],
            aws_session_token=session_token,
        )
    else:
        return boto3.Session()


def get_aws_profile_credentials(profile_name):
    from ConfigParser import ConfigParser
    from ConfigParser import ParsingError
    from ConfigParser import NoOptionError
    from ConfigParser import NoSectionError
    from os import path

    aws_creds = {}

    config = ConfigParser()
    config_file_path = path.join(path.expanduser("~"),'.aws/config')
    config.read([config_file_path])

    try:
        section = 'profile {}'.format(profile_name)
        aws_creds['role_arn'] = config.get(section, 'role_arn')
        source_profile = config.get(section, 'source_profile')
    except ParsingError:
        print('Error parsing AWS config file')
        raise
    except (NoSectionError, NoOptionError):
        print('Unable to find AWS profile named {} in {}'.format(
            profile_name,
            config_file_path))
        raise

    credentials = ConfigParser()
    credentials_file_path = path.join(path.expanduser("~"),'.aws/credentials')
    credentials.read([credentials_file_path])

    try:
        aws_creds['AWS_ACCESS_KEY_ID'] = credentials.get(source_profile, 'aws_access_key_id')
        aws_creds['AWS_SECRET_ACCESS_KEY'] = credentials.get(source_profile, 'aws_secret_access_key')
    except ParsingError:
        print('Error parsing AWS credentials file')
        raise
    except (NoSectionError, NoOptionError):
        print('Unable to find AWS profile named {} in {}'.format(
            profile_name,
            credentials_file_path))
        raise
    return aws_creds


def get_role_arn_from_name(aws_creds, role_name, verbose=False):
    try:
        session = get_boto3_session(aws_creds)
        iam_client = session.client('iam')
        role_arn = iam_client.get_role(RoleName=role_name)['Role']['Arn']
        return role_arn
    except ClientError as e:
        if verbose:
          print(e)
        method = get_credential_method_description(session)
        if e.response['Error']['Code'] == 'NoSuchEntity':
            raise RoleNotFoundError(method, e)
        else:
            raise AssumeRoleError(method, "Error reading role arn for role name {}: {}".format(role_name, e))
    except Exception as e:
        if verbose:
          print(e)
        method = get_credential_method_description(session)            
        raise AssumeRoleError(method, "Error reading role arn for role name {}: {}".format(role_name, e))


def generate_aws_temp_creds(role_arn, aws_creds=None, verbose=False):
    session = get_boto3_session(aws_creds)
    sts_client = session.client('sts')

    try:
        random_session = uuid.uuid4().hex
        assumed_role_object = sts_client.assume_role(
            RoleArn=role_arn,
            RoleSessionName="docker-session-{}".format(random_session),
            DurationSeconds=3600  # 1 hour max
        )
        access_key = assumed_role_object["Credentials"]["AccessKeyId"]
        secret_key = assumed_role_object["Credentials"]["SecretAccessKey"]
        session_token = assumed_role_object["Credentials"]["SessionToken"]
    except Exception as e:
        if verbose:
          print(e)
        method = get_credential_method_description(session)
        raise AssumeRoleError(method, "Error assuming role {}: {}".format(role_arn, e))

    return access_key, secret_key, session_token
