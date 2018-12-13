# IAM-Starter

A CLI which starts your program with AWS IAM credentials in the environment by assuming a role or a profile

## Installation

```shell
$ pip install iam-starter
```

## Usage

A few examples:

```shell
# start a program given an IAM Role (assumes default creds can assume role)
$ iam-starter --role myrole --command ./my-program.sh

# start a program with a profile
$ iam-starter --profile myprofile --command ./my-program.sh

# start a program with an IAM Role using a profile to assume that role
$ iam-starter --role myrole --profile dev --command ./my-program.sh

# get export commands to paste into shell to assume the role manually
$ iam-starter --role myrole
export AWS_ACCESS_KEY_ID="ASIAI....UOCA"
export AWS_SECRET_ACCESS_KEY="DWYnQ....h93k"
export AWS_SESSION_TOKEN="KMWSz...8wX=="

# note that these two are equivalent:
$ iam-starter --profile myprofile --command aws s3 ls
$ aws s3 ls --profile myprofile

# you can use iamx as shorthand for iam-starter (less typing)
$ iamx --role myrole --command aws s3 ls
```

## Motivation

The desire was to be able to easily run programs that need AWS credentials locally the same way you can run them in AWS, and to do so without requiring code changes or complex logic to support multiple methods of obtaining AWS credentials.  On EC2 you simply attach an IAM role to the instance and then anything you do on that instance is automatically in the context of that IAM role.  Locally it isn't quite as easy to run things in the context of a role, you have to setup an AWS profile (already something you don't do inside AWS) to assume your role, then your program has to support using the named profile when authenticating to AWS, which isn't always an option (not all tools correctly/fully support using AWS profiles).

If you care to execute your app with the context of a role rather than running everything with your full admin developer credentials and waiting to find out in production that you have an IAM permissions issue, you are probably using named profiles (`aws configure --profile profilename`).  However when running your app locally in order for your AWS API calls to use that profile it requires a code change to specify the profile name to the AWS SDK.  That sounds okay at first until you realize that those profiles will not exist when deployed into AWS, so code that "works on your machine" doesn't work in production.

If you haven't already given up on trying to be a good citizen and run/test your app locally with the limited IAM policy you defined for it, this causes you to have to do unfortunate stuff like this all over your code:

```python
# how annoying that I have to pass an optional profile name here
def do_something_with_aws(profile=None)
    if profile:
        # this is what will happen on my laptop
        session = boto3.Session(profile_name=profile)
        client = session.client('s3')
    else:
        # this is what will happen when running on EC2
        client = boto3.client('s3')
```
(a python example but this is true of the AWS SDK for any language or the AWS CLI)

IAM-Starter makes it easy for you to run locally and in AWS using roles or named profiles, via the same credential method -- environment variables, which are the most universally supported credential method.

```python
def do_something_with_aws()
    # yay, simple and the same everywhere!
    client = boto3.client('s3')
```

## Use with Docker

This is primarily intended to be used outside Docker.  To run a Docker container with an assumed IAM Role, you are probably better off using [IAM-Docker-Run](https://github.com/billtrust/iam-docker-run).

## Use with SSM-Starter

This can be chained with [SSM-Starter](https://github.com/billtrust/ssm-starter).  The following example starts a program with the given IAM role and loads the SSM parameters for the given path into the environment, then runs your program which now has the benefit of the IAM role and the configuration loaded into the environment.

```shell
$ export AWS_REGION=us-east-1 # needed for ssm-starter
$ iam-starter --role myrole --profile dev --command ssm-starter --ssm-name /myssmprefix/ --command ./my-program.sh
```

## Limitations

**This is a development workflow tool, not designed to run production applications.**

Temporary credentials expire within 1 hour and do not auto renew.  This tool was designed to be used with development, adhoc, or witih build/CI environments where execution time is short.

## Publishing Updates to PyPi

For the maintainer - to publish an updated version of ssm-search, increment the version number in version.py and run the following:

```shell
docker build -f ./Dockerfile.buildenv -t iam-starter:build .
docker run --rm -it --entrypoint make iam-starter:build publish
```

At the prompts, enter the username and password to the pypi.org repo.

## Testing

Test execution in a container by inserting your local AWS credentials into the container.

```shell
docker build -f ./Dockerfile.buildenv -t iam-starter:build .
docker run -it -v $(cd ~/.aws; pwd):/root/.aws iam-starter:build
# then, inside the container
pip install awscli
# assumes a local profile named "dev" which has access to list S3 buckets
iam-starter --profile dev --command aws s3 ls
```
