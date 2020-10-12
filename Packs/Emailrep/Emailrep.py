"""EmailRep Integration for Cortex XSOAR"""
import demistomock as demisto
from CommonServerPython import *
from CommonServerUserPython import *

import urllib3
import traceback
from typing import Any, Dict, List, Optional

# Disable insecure warnings
urllib3.disable_warnings()


''' CONSTANTS '''


ACCEPTED_TAGS = ['account_takeover', 'bec', 'brand_impersonation', 'browser_exploit', 'credential_phishing',
                 'generic_phishing', 'malware', 'scam', 'spam', 'spoofed', 'task_request', 'threat_actor']
APP_NAME = 'Cortex-XSOAR'
INTEGRATION_NAME = 'EmailRep'

''' CLIENT CLASS '''


class Client(BaseClient):
    """Client class to interact with the EmailRep service API"""

    def get_email_address_reputation(self, email: str) -> Dict[str, Any]:
        """Get email reputation using the '/{email}' API endpoint"""

        return self._http_request(
            method='GET',
            url_suffix=f"/{email}"
        )

    def post_email_address_report(self, email: str, tags: List[str], description: Optional[str],
                                  timestamp: Optional[int], expires: Optional[int]) -> Dict[str, Any]:
        """Report email reputation using the '/report' API endpoint"""
        request_params: Dict[str, Any] = {}
        request_params['email'] = email
        request_params['tags'] = tags

        if description:
            request_params['description'] = description

        if timestamp:
            request_params['timestamp'] = timestamp

        if expires:
            request_params['expires'] = expires

        return self._http_request(
            method='POST',
            url_suffix='/report',
            params=request_params
        )


''' COMMAND FUNCTIONS '''


def test_module(client: Client, first_fetch_time: int) -> str:
    """Tests API connectivity and authentication'

    Returning 'ok' indicates that the integration works like it is supposed to.
    Connection to the service is successful.
    Raises exceptions if something goes wrong.

    :type client: ``Client``
    :param Client: HelloWorld client to use

    :type name: ``str``
    :param name: name to append to the 'Hello' string

    :return: 'ok' if test passed, anything else will fail the test.
    :rtype: ``str``
    """

    # INTEGRATION DEVELOPER TIP
    # Client class should raise the exceptions, but if the test fails
    # the exception text is printed to the Cortex XSOAR UI.
    # If you have some specific errors you want to capture (i.e. auth failure)
    # you should catch the exception here and return a string with a more
    # readable output (for example return 'Authentication Error, API Key
    # invalid').
    # Cortex XSOAR will print everything you return different than 'ok' as
    # an error
    try:
        client.search_alerts(max_results=1, start_time=first_fetch_time, alert_status=None, alert_type=None, severity=None)
    except DemistoException as e:
        if 'Forbidden' in str(e):
            return 'Authorization Error: make sure API Key is correctly set'
        else:
            raise e
    return 'ok'


def email_command(client: Client, args: Dict[str, Any]) -> CommandResults:
    """Get email address reputation from EmailRep and calculate DBotScore.

    DBot score:
    Good: Suspicious = false
    Malicious: Suspicious = true + (malicious_activity_recent = true or credentials_leaked_recent = true)
    Suspicious: Suspicious = true and not malicious
    """

    emails = argToList(args.get('email_address'))
    if len(emails) == 0:
        raise ValueError('Email(s) not specified')

    email_data_list: List[Dict[str, Any]] = []
    email_score_list: List[Dict[str, Any]] = []
    for email in emails:
        email_data = client.get_email_address_reputation(email)
        email_data_list.append(email_data)

        score = Common.DBotScore.NONE
        description = f'{INTEGRATION_NAME} returned'
        suspicious = email_data.get('suspicious')
        malicious_activity_recent = email_data.get('details.malicious_activity_recent')
        credentials_leaked_recent = email_data.get('details.credentials_leaked_recent')
        if not suspicious:
            score = Common.DBotScore.GOOD
            description = None
        elif malicious_activity_recent or credentials_leaked_recent:
            if malicious_activity_recent:
                description += ' malicious_activity_recent '
            if credentials_leaked_recent:
                description += ' credentials_leaked_recent'
            score = Common.DBotScore.BAD
        else:
            score = Common.DBotScore.SUSPICIOUS
            description = None

        dbot_score = Common.DBotScore(
            indicator=email,
            indicator_type=DBotScoreType.EMAIL_ADDRESS,
            integration_name=INTEGRATION_NAME,
            score=score,
            malicious_description=description
        )

        email_context = Common.Email(
            email_address=email,
            dbot_score=dbot_score
        )

        email_score_list.append(email_context)

    readable_output = tableToMarkdown('Email List', email_data_list)

    return CommandResults(
        readable_output=readable_output,
        outputs_prefix=f'{INTEGRATION_NAME}.EmailScore',
        outputs_key_field='email',
        outputs=email_data_list,
        indicators=email_score_list
    )


def email_reputation_command(client: Client, args: Dict[str, Any]) -> CommandResults:
    """Get email address reputation from EmailRep"""

    emails = argToList(args.get('email_address'))
    if len(emails) == 0:
        raise ValueError('Email(s) not specified')

    email_data_list: List[Dict[str, Any]] = []
    for email in emails:
        email_data = client.get_email_address_reputation(email)
        email_data_list.append(email_data)

    readable_output = tableToMarkdown('Email List', email_data_list)

    return CommandResults(
        readable_output=readable_output,
        outputs_prefix=f'{INTEGRATION_NAME}.Email',
        outputs_key_field='email',
        outputs=email_data_list
    )

def report_email_address_command(client: Client, args: Dict[str, Any]) -> CommandResults:
    """Report email address to EmailRep"""

    email_address = args.get('email_address')
    if email_address == '':
        raise ValueError('Email(s) not specified')
    tags = argToList(args.get('tags'))
    if len(tags) == 0:
        raise ValueError('Tag(s) not specified')
    for tag in tags:
        if tag not in ACCEPTED_TAGS:
            raise ValueError(f'Tag \'{tag}\' not in accepted tag list: {ACCEPTED_TAGS}')

    description = args.get('description')
    timestamp = args.get('timestamp')
    if timestamp is not None:
        timestamp = int(args.get('timestamp'))

    expires = args.get('expires')
    if expires is not None:
        expires = int(args.get('expires'))

    result = client.post_email_address_report(email_address, tags, description, timestamp, expires)

    readable_output = tableToMarkdown('Email Report Response', result)

    return CommandResults(
        readable_output=readable_output,
        outputs_prefix=f'{INTEGRATION_NAME}.Report',
        outputs_key_field='status',
        outputs=result
    )


''' MAIN FUNCTION '''


def main() -> None:
    """main function, parses params and runs command functions"""

    api_key = demisto.params().get('apikey')

    # get the service API url
    base_url = demisto.params()['url']
    verify_certificate = not demisto.params().get('insecure', False)
    proxy = demisto.params().get('proxy', False)

    demisto.debug(f'Command being called is {demisto.command()}')
    try:
        headers = {
            'Key': f'{api_key}',
            'User-Agent': APP_NAME
        }
        client = Client(
            base_url=base_url,
            verify=verify_certificate,
            headers=headers,
            proxy=proxy)

        if demisto.command() == 'emailrep-email-reputation-get':
            return_results(email_reputation_command(client, demisto.args()))

        elif demisto.command() == 'email':
            return_results(email_command(client, demisto.args()))

        elif demisto.command() == 'emailrep-email-address-report':
            return_results(report_email_address_command(client, demisto.args()))

        elif demisto.command() == 'test-module':
            # This is the call made when pressing the integration Test button.
            result = test_module(client, first_fetch_time)
            return_results(result)


    # Log exceptions and return errors
    except Exception as e:
        demisto.error(traceback.format_exc())  # print the traceback
        return_error(f'Failed to execute {demisto.command()} command.\nError:\n{str(e)}')


''' ENTRY POINT '''


if __name__ in ('__main__', '__builtin__', 'builtins'):
    main()