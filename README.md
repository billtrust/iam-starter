# IAM-Starter

A CLI which starts your program in the context of an assumed AWS IAM Role

## Installation

```shell
$ pip install iam-starter
```

## Usage

```shell
# start a program given an IAM Role (assumes default creds can assume role)
$ iam-starter --role myrole --command ./my-program.sh

# start a program given an IAM Role and AWS Profile with access to assume that role
$ iam-starter --role myrole --profile dev --command ./my-program.sh

# get export commands to paste into shell to assume the role manually
$ iam-starter --role myrole --profile dev
export AWS_ACCESS_KEY_ID="ASIAI....UOCA"
export AWS_SECRET_ACCESS_KEY="DWYnQ....h93k"
export AWS_SESSION_TOKEN="KMWSz...8wX=="
# Run this to configure your shell:
# eval $(iam-starter --role myrole --profile dev)
```

## Motivation

To be able to use AWS IAM Roles wherever possible, and to avoid having to specify profile names in code, or necessitate any other code changes to support different methods of gaining AWS credentials inside or outside of EC2 / ECS.

The desire was to accomplish this without having to configure a profile in your `~/.aws/config` for each role as that may be cumbersome for a large number of different roles, or inconvenient when executing in environments such as CI servers where you may or may not have access to setup AWS profiles in that environment.

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
