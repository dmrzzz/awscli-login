import logging

from datetime import datetime, timezone
from os import path
from time import sleep
from typing import Dict, List, Tuple

from awscli.customizations.configure.set import ConfigureSetCommand
from awscli_login.exceptions import SAML
from awscli_login.typing import Role
from botocore.session import Session

awsconfigfile = path.join('.aws', 'credentials')

logger = logging.getLogger(__name__)

TRUE = ("yes", "true", "t", "1")
FALSE = ("no", "false", "f", "0")


def sort_roles(role_arns: List[Role]) \
               -> List[Tuple[str, List[Tuple[int, str]]]]:
    """ TODO """
    accounts: Dict[str, List[Tuple[int, str]]] = {}
    r: List[Tuple[str, List[Tuple[int, str]]]] = []

    for index, arn in enumerate(role_arns):
        acct: str = arn[1].split(':')[4]
        role: str = arn[1].split(':')[5].split('/')[1]

        role_list = accounts.get(acct, list())
        role_list.append((index, role))
        accounts[acct] = role_list

    for acct in sorted(accounts.keys()):
        accounts[acct].sort(key=lambda x: x[1])
        r.append((acct, accounts[acct]))

    return r


def get_selection(role_arns: List[Role]) -> Role:
    """ Interactively prompts the user for a role selection. """
    i = 0
    n = len(role_arns)
    select: Dict[int, int] = {}

    if n > 1:
        print("Please choose the role you would like to assume:")

        accounts = sort_roles(role_arns)
        for acct, roles in accounts:
            print(' ' * 4, "Account:", acct)

            for index, role in roles:
                print(' ' * 8, "[ %d ]:" % i, role)
                select[i] = index
                i += 1

        print("Selection:\a ", end='')
# TODO need error checking
        return role_arns[select[int(input())]]
    elif n == 1:
        return role_arns[0]
    else:
        raise SAML("No roles returned!")


class Args:
    """ A stub class for passing arguments to ConfigureSetCommand """
    def __init__(self, varname: str, value: str) -> None:
        self.varname = varname
        self.value = value


def _aws_set(session: Session, varname: str, value: str) -> None:
    """
    This is a helper function for save_credentials.

    The function is the same as running:

    $ aws configure set varname value
    """
    set_command = ConfigureSetCommand(session)
    set_command._run_main(Args(varname, value), parsed_globals=None)


def remove_credentials(session: Session) -> None:
    """
    Removes current profile's credentials from ~/.aws/credentials.
    """
    profile = session.profile if session.profile else 'default'

    _aws_set(session, 'aws_access_key_id', '')
    _aws_set(session, 'aws_secret_access_key', '')
    _aws_set(session, 'aws_session_token',  '')
    logger.info("Removed temporary STS credentials from profile: " + profile)


def save_credentials(session: Session, token: Dict) -> datetime:
    """ Takes an Amazon token and stores it in ~/.aws/credentials """
    creds = token['Credentials']
    profile = session.profile if session.profile else 'default'

    _aws_set(session, 'aws_access_key_id', creds['AccessKeyId'])
    _aws_set(session, 'aws_secret_access_key', creds['SecretAccessKey'])
    _aws_set(session, 'aws_session_token',  creds['SessionToken'])
    logger.info("Saved temporary STS credentials to profile: " + profile)

    assert isinstance(creds['Expiration'], datetime), \
        "Amazon returned bad Expiration!"
    return creds['Expiration']


def file2bytes(filename: str) -> bytes:
    """
    Takes a filename and returns a byte string with the content of the file.
    """
    with open(filename, 'rb') as f:
        data = f.read()
    return data


def file2str(filename: str) -> str:
    """ Takes a filename and returns a string with the content of the file. """
    with open(filename, 'r') as f:
        data = f.read()
    return data


def nap(expires: datetime, percent: float) -> None:
    """TODO. """
    tz = timezone.utc
    ttl = int((expires - datetime.now(tz)).total_seconds())
    sleep_for = ttl * 0.9

    logger.info('Going to sleep for %d seconds.' % sleep_for)
    sleep(sleep_for)
