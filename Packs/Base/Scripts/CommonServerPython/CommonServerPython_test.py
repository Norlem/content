# -*- coding: utf-8 -*-
import demistomock as demisto
import copy
import json
import re
import os
import sys
import requests
from pytest import raises, mark
import pytest

from CommonServerPython import xml2json, json2xml, entryTypes, formats, tableToMarkdown, underscoreToCamelCase, \
    flattenCell, date_to_timestamp, datetime, camelize, pascalToSpace, argToList, \
    remove_nulls_from_dictionary, is_error, get_error, hash_djb2, fileResult, is_ip_valid, get_demisto_version, \
    IntegrationLogger, parse_date_string, IS_PY3, DebugLogger, b64_encode, parse_date_range, return_outputs, \
    argToBoolean, ipv4Regex, ipv4cidrRegex, ipv6cidrRegex, ipv6Regex, batch, FeedIndicatorType, \
    encode_string_results, safe_load_json, remove_empty_elements, aws_table_to_markdown, is_demisto_version_ge, \
    appendContext, auto_detect_indicator_type, handle_proxy, get_demisto_version_as_str, get_x_content_info_headers

try:
    from StringIO import StringIO
except ImportError:
    # Python 3
    from io import StringIO  # noqa

INFO = {'b': 1,
        'a': {
            'safd': 3,
            'b': [
                {'c': {'d': 432}, 'd': 2},
                {'c': {'f': 1}},
                {'b': 1234},
                {'c': {'d': 4567}},
                {'c': {'d': 11}},
                {'c': {'d': u'asdf'}}],
            'c': {'d': 10},
        }
        }


@pytest.fixture()
def clear_version_cache():
    """
    Clear the version cache at end of the test (in case we mocked demisto.serverVersion)
    """
    yield
    get_demisto_version._version = None


def test_xml():
    import json

    xml = b"<work><employee><id>100</id><name>foo</name></employee><employee><id>200</id><name>goo</name>" \
          b"</employee></work>"
    jsonExpected = '{"work": {"employee": [{"id": "100", "name": "foo"}, {"id": "200", "name": "goo"}]}}'

    jsonActual = xml2json(xml)
    assert jsonActual == jsonExpected, "expected\n" + jsonExpected + "\n to equal \n" + jsonActual

    jsonDict = json.loads(jsonActual)
    assert jsonDict['work']['employee'][0]['id'] == "100", 'id of first employee must be 100'
    assert jsonDict['work']['employee'][1]['name'] == "goo", 'name of second employee must be goo'

    xmlActual = json2xml(jsonActual)
    assert xmlActual == xml, "expected:\n{}\nto equal:\n{}".format(xml, xmlActual)


def toEntry(table):
    return {

        'Type': entryTypes['note'],
        'Contents': table,
        'ContentsFormat': formats['table'],
        'ReadableContentsFormat': formats['markdown'],
        'HumanReadable': table
    }


DATA = [
    {
        'header_1': 'a1',
        'header_2': 'b1',
        'header_3': 'c1'
    },
    {
        'header_1': 'a2',
        'header_2': 'b2',
        'header_3': 'c2'
    },
    {
        'header_1': 'a3',
        'header_2': 'b3',
        'header_3': 'c3'
    },
]


def test_tbl_to_md_only_data():
    # sanity
    table = tableToMarkdown('tableToMarkdown test', DATA)
    expected_table = '''### tableToMarkdown test
|header_1|header_2|header_3|
|---|---|---|
| a1 | b1 | c1 |
| a2 | b2 | c2 |
| a3 | b3 | c3 |
'''
    assert table == expected_table


def test_tbl_to_md_header_transform_underscoreToCamelCase():
    # header transform
    table = tableToMarkdown('tableToMarkdown test with headerTransform', DATA,
                            headerTransform=underscoreToCamelCase)
    expected_table = '''### tableToMarkdown test with headerTransform
|Header1|Header2|Header3|
|---|---|---|
| a1 | b1 | c1 |
| a2 | b2 | c2 |
| a3 | b3 | c3 |
'''
    assert table == expected_table


def test_tbl_to_md_multiline():
    # escaping characters: multiline + md-chars
    data = copy.deepcopy(DATA)
    for i, d in enumerate(data):
        d['header_2'] = 'b%d.1\nb%d.2' % (i + 1, i + 1,)
        d['header_3'] = 'c%d|1' % (i + 1,)

    table = tableToMarkdown('tableToMarkdown test with multiline', data)
    expected_table = '''### tableToMarkdown test with multiline
|header_1|header_2|header_3|
|---|---|---|
| a1 | b1.1<br>b1.2 | c1\\|1 |
| a2 | b2.1<br>b2.2 | c2\\|1 |
| a3 | b3.1<br>b3.2 | c3\\|1 |
'''
    assert table == expected_table


def test_tbl_to_md_url():
    # url + empty data
    data = copy.deepcopy(DATA)
    for i, d in enumerate(data):
        d['header_3'] = '[url](https:\\demisto.com)'
        d['header_2'] = None
    table_url_missing_info = tableToMarkdown('tableToMarkdown test with url and missing info', data)
    expected_table_url_missing_info = '''### tableToMarkdown test with url and missing info
|header_1|header_2|header_3|
|---|---|---|
| a1 |  | [url](https:\\demisto.com) |
| a2 |  | [url](https:\\demisto.com) |
| a3 |  | [url](https:\\demisto.com) |
'''
    assert table_url_missing_info == expected_table_url_missing_info


def test_tbl_to_md_single_column():
    # single column table
    table_single_column = tableToMarkdown('tableToMarkdown test with single column', DATA, ['header_1'])
    expected_table_single_column = '''### tableToMarkdown test with single column
|header_1|
|---|
| a1 |
| a2 |
| a3 |
'''
    assert table_single_column == expected_table_single_column


def test_is_ip_valid():
    valid_ip_v6 = "FE80:0000:0000:0000:0202:B3FF:FE1E:8329"
    valid_ip_v6_b = "FE80::0202:B3FF:FE1E:8329"
    invalid_ip_v6 = "KKKK:0000:0000:0000:0202:B3FF:FE1E:8329"
    valid_ip_v4 = "10.10.10.10"
    invalid_ip_v4 = "10.10.10.9999"
    invalid_not_ip_with_ip_structure = "1.1.1.1.1.1.1.1.1.1.1.1.1.1.1"
    not_ip = "Demisto"
    assert not is_ip_valid(valid_ip_v6)
    assert is_ip_valid(valid_ip_v6, True)
    assert is_ip_valid(valid_ip_v6_b, True)
    assert not is_ip_valid(invalid_ip_v6, True)
    assert not is_ip_valid(not_ip, True)
    assert is_ip_valid(valid_ip_v4)
    assert not is_ip_valid(invalid_ip_v4)
    assert not is_ip_valid(invalid_not_ip_with_ip_structure)


def test_tbl_to_md_list_values():
    # list values
    data = copy.deepcopy(DATA)
    for i, d in enumerate(data):
        d['header_3'] = [i + 1, 'second item']
        d['header_2'] = 'hi'

    table_list_field = tableToMarkdown('tableToMarkdown test with list field', data)
    expected_table_list_field = '''### tableToMarkdown test with list field
|header_1|header_2|header_3|
|---|---|---|
| a1 | hi | 1,<br>second item |
| a2 | hi | 2,<br>second item |
| a3 | hi | 3,<br>second item |
'''
    assert table_list_field == expected_table_list_field


def test_tbl_to_md_empty_fields():
    # all fields are empty
    data = [
        {
            'a': None,
            'b': None,
            'c': None,
        } for _ in range(3)
    ]
    table_all_none = tableToMarkdown('tableToMarkdown test with all none fields', data)
    expected_table_all_none = '''### tableToMarkdown test with all none fields
|a|b|c|
|---|---|---|
|  |  |  |
|  |  |  |
|  |  |  |
'''
    assert table_all_none == expected_table_all_none

    # all fields are empty - removed
    table_all_none2 = tableToMarkdown('tableToMarkdown test with all none fields2', data, removeNull=True)
    expected_table_all_none2 = '''### tableToMarkdown test with all none fields2
**No entries.**
'''
    assert table_all_none2 == expected_table_all_none2


def test_tbl_to_md_header_not_on_first_object():
    # header not on first object
    data = copy.deepcopy(DATA)
    data[1]['extra_header'] = 'sample'
    table_extra_header = tableToMarkdown('tableToMarkdown test with extra header', data,
                                         headers=['header_1', 'header_2', 'extra_header'])
    expected_table_extra_header = '''### tableToMarkdown test with extra header
|header_1|header_2|extra_header|
|---|---|---|
| a1 | b1 |  |
| a2 | b2 | sample |
| a3 | b3 |  |
'''
    assert table_extra_header == expected_table_extra_header


def test_tbl_to_md_no_header():
    # no header
    table_no_headers = tableToMarkdown('tableToMarkdown test with no headers', DATA,
                                       headers=['no', 'header', 'found'], removeNull=True)
    expected_table_no_headers = '''### tableToMarkdown test with no headers
**No entries.**
'''
    assert table_no_headers == expected_table_no_headers


def test_tbl_to_md_dict_value():
    # dict value
    data = copy.deepcopy(DATA)
    data[1]['extra_header'] = {'sample': 'qwerty', 'sample2': 'asdf'}
    table_dict_record = tableToMarkdown('tableToMarkdown test with dict record', data,
                                        headers=['header_1', 'header_2', 'extra_header'])
    expected_dict_record = '''### tableToMarkdown test with dict record
|header_1|header_2|extra_header|
|---|---|---|
| a1 | b1 |  |
| a2 | b2 | sample: qwerty<br>sample2: asdf |
| a3 | b3 |  |
'''
    assert table_dict_record == expected_dict_record


def test_tbl_to_md_string_header():
    # string header (instead of list)
    table_string_header = tableToMarkdown('tableToMarkdown string header', DATA, 'header_1')
    expected_string_header_tbl = '''### tableToMarkdown string header
|header_1|
|---|
| a1 |
| a2 |
| a3 |
'''
    assert table_string_header == expected_string_header_tbl


def test_tbl_to_md_list_of_strings_instead_of_dict():
    # list of string values instead of list of dict objects
    table_string_array = tableToMarkdown('tableToMarkdown test with string array', ['foo', 'bar', 'katz'], ['header_1'])
    expected_string_array_tbl = '''### tableToMarkdown test with string array
|header_1|
|---|
| foo |
| bar |
| katz |
'''
    assert table_string_array == expected_string_array_tbl


def test_tbl_to_md_list_of_strings_instead_of_dict_and_string_header():
    # combination: string header + string values list
    table_string_array_string_header = tableToMarkdown('tableToMarkdown test with string array and string header',
                                                       ['foo', 'bar', 'katz'], 'header_1')
    expected_string_array_string_header_tbl = '''### tableToMarkdown test with string array and string header
|header_1|
|---|
| foo |
| bar |
| katz |
'''
    assert table_string_array_string_header == expected_string_array_string_header_tbl


def test_tbl_to_md_dict_with_special_character():
    data = {
        'header_1': u'foo',
        'header_2': [u'\xe2.rtf']
    }
    table_with_character = tableToMarkdown('tableToMarkdown test with special character', data)
    expected_string_with_special_character = '''### tableToMarkdown test with special character
|header_1|header_2|
|---|---|
| foo | â.rtf |
'''
    assert table_with_character == expected_string_with_special_character


def test_tbl_to_md_header_with_special_character():
    data = {
        'header_1': u'foo'
    }
    table_with_character = tableToMarkdown('tableToMarkdown test with special character Ù', data)
    expected_string_with_special_character = '''### tableToMarkdown test with special character Ù
|header_1|
|---|
| foo |
'''
    assert table_with_character == expected_string_with_special_character


def test_flatten_cell():
    # sanity
    utf8_to_flatten = b'abcdefghijklmnopqrstuvwxyz1234567890!'.decode('utf8')
    flatten_text = flattenCell(utf8_to_flatten)
    expected_string = 'abcdefghijklmnopqrstuvwxyz1234567890!'

    assert flatten_text == expected_string

    # list of uft8 and string to flatten
    str_a = b'abcdefghijklmnopqrstuvwxyz1234567890!'
    utf8_b = str_a.decode('utf8')
    list_to_flatten = [str_a, utf8_b]
    flatten_text2 = flattenCell(list_to_flatten)
    expected_flatten_string = 'abcdefghijklmnopqrstuvwxyz1234567890!,\nabcdefghijklmnopqrstuvwxyz1234567890!'

    assert flatten_text2 == expected_flatten_string

    # special character test
    special_char = u'会'
    list_of_special = [special_char, special_char]

    flattenCell(list_of_special)
    flattenCell(special_char)

    # dictionary test
    dict_to_flatten = {'first': u'会'}
    expected_flatten_dict = u'{\n    "first": "\u4f1a"\n}'
    assert flattenCell(dict_to_flatten) == expected_flatten_dict


def test_hash_djb2():
    assert hash_djb2("test") == 2090756197, "Invalid value of hash_djb2"


def test_camelize():
    non_camalized = [{'chookity_bop': 'asdasd'}, {'ab_c': 'd e', 'fgh_ijk': 'lm', 'nop': 'qr_st'}]
    expected_output = [{'ChookityBop': 'asdasd'}, {'AbC': 'd e', 'Nop': 'qr_st', 'FghIjk': 'lm'}]
    assert camelize(non_camalized, '_') == expected_output

    non_camalized2 = {'ab_c': 'd e', 'fgh_ijk': 'lm', 'nop': 'qr_st'}
    expected_output2 = {'AbC': 'd e', 'Nop': 'qr_st', 'FghIjk': 'lm'}
    assert camelize(non_camalized2, '_') == expected_output2


# Note this test will fail when run locally (in pycharm/vscode) as it assumes the machine (docker image) has UTC timezone set
def test_date_to_timestamp():
    assert date_to_timestamp('2018-11-06T08:56:41') == 1541494601000
    assert date_to_timestamp(datetime.strptime('2018-11-06T08:56:41', "%Y-%m-%dT%H:%M:%S")) == 1541494601000


def test_pascalToSpace():
    use_cases = [
        ('Validate', 'Validate'),
        ('validate', 'Validate'),
        ('TCP', 'TCP'),
        ('eventType', 'Event Type'),
        ('eventID', 'Event ID'),
        ('eventId', 'Event Id'),
        ('IPAddress', 'IP Address'),
    ]
    for s, expected in use_cases:
        assert pascalToSpace(s) == expected, 'Error on {} != {}'.format(pascalToSpace(s), expected)


def test_safe_load_json():
    valid_json_str = '{"foo": "bar"}'
    expected_valid_json_result = {u'foo': u'bar'}
    assert expected_valid_json_result == safe_load_json(valid_json_str)


def test_remove_empty_elements():
    test_dict = {
        "foo": "bar",
        "baz": {},
        "empty": [],
        "nested_dict": {
            "empty_list": [],
            "hummus": "pita"
        },
        "nested_list": {
            "more_empty_list": []
        }
    }

    expected_result = {
        "foo": "bar",
        "nested_dict": {
            "hummus": "pita"
        }
    }
    assert expected_result == remove_empty_elements(test_dict)


def test_aws_table_to_markdown():
    header = "AWS DynamoDB DescribeBackup"
    raw_input = {
        'BackupDescription': {
            "Foo": "Bar",
            "Baz": "Bang",
            "TestKey": "TestValue"
        }
    }
    expected_output = '''### AWS DynamoDB DescribeBackup
|Baz|Foo|TestKey|
|---|---|---|
| Bang | Bar | TestValue |
'''

    assert expected_output == aws_table_to_markdown(raw_input, header)


def test_argToList():
    expected = ['a', 'b', 'c']
    test1 = ['a', 'b', 'c']
    test2 = 'a,b,c'
    test3 = '["a","b","c"]'
    test4 = 'a;b;c'
    test5 = 1
    test6 = '1'
    test7 = True

    results = [argToList(test1), argToList(test2), argToList(test2, ','), argToList(test3), argToList(test4, ';')]

    for result in results:
        assert expected == result, 'argToList test failed, {} is not equal to {}'.format(str(result), str(expected))

    assert argToList(test5) == [1]
    assert argToList(test6) == ['1']
    assert argToList(test7) == [True]


def test_remove_nulls():
    temp_dictionary = {"a": "b", "c": 4, "e": [], "f": {}, "g": None, "h": "", "i": [1], "k": ()}
    expected_dictionary = {"a": "b", "c": 4, "i": [1]}

    remove_nulls_from_dictionary(temp_dictionary)

    assert expected_dictionary == temp_dictionary, \
        "remove_nulls_from_dictionary test failed, {} is not equal to {}".format(str(temp_dictionary),
                                                                                 str(expected_dictionary))


def test_is_error_true():
    execute_command_results = [
        {
            "Type": entryTypes["error"],
            "ContentsFormat": formats["text"],
            "Contents": "this is error message"
        }
    ]
    assert is_error(execute_command_results)


def test_is_error_none():
    assert not is_error(None)


def test_is_error_single_entry():
    execute_command_results = {
        "Type": entryTypes["error"],
        "ContentsFormat": formats["text"],
        "Contents": "this is error message"
    }

    assert is_error(execute_command_results)


def test_is_error_false():
    execute_command_results = [
        {
            "Type": entryTypes["note"],
            "ContentsFormat": formats["text"],
            "Contents": "this is regular note"
        }
    ]
    assert not is_error(execute_command_results)


def test_not_error_entry():
    execute_command_results = "invalid command results as string"
    assert not is_error(execute_command_results)


def test_get_error():
    execute_command_results = [
        {
            "Type": entryTypes["error"],
            "ContentsFormat": formats["text"],
            "Contents": "this is error message"
        }
    ]
    error = get_error(execute_command_results)
    assert error == "this is error message"


def test_get_error_single_entry():
    execute_command_results = {
        "Type": entryTypes["error"],
        "ContentsFormat": formats["text"],
        "Contents": "this is error message"
    }

    error = get_error(execute_command_results)
    assert error == "this is error message"


def test_get_error_need_raise_error_on_non_error_input():
    execute_command_results = [
        {
            "Type": entryTypes["note"],
            "ContentsFormat": formats["text"],
            "Contents": "this is not an error"
        }
    ]
    try:
        get_error(execute_command_results)
    except ValueError as exception:
        assert "execute_command_result has no error entry. before using get_error use is_error" in str(exception)
        return

    assert False


@mark.parametrize('data,data_expected', [
    ("this is a test", b"this is a test"),
    (u"עברית", u"עברית".encode('utf-8')),
    (b"binary data\x15\x00", b"binary data\x15\x00"),
])  # noqa: E124
def test_fileResult(mocker, request, data, data_expected):
    mocker.patch.object(demisto, 'uniqueFile', return_value="test_file_result")
    mocker.patch.object(demisto, 'investigation', return_value={'id': '1'})
    file_name = "1_test_file_result"

    def cleanup():
        try:
            os.remove(file_name)
        except OSError:
            pass

    request.addfinalizer(cleanup)
    res = fileResult("test.txt", data)
    assert res['File'] == "test.txt"
    with open(file_name, 'rb') as f:
        assert f.read() == data_expected


# Error that always returns a unicode string to it's str representation
class SpecialErr(Exception):
    def __str__(self):
        return u"מיוחד"


def test_logger():
    from CommonServerPython import LOG
    LOG(u'€')
    LOG(Exception(u'€'))
    LOG(SpecialErr(12))


def test_logger_write(mocker):
    mocker.patch.object(demisto, 'params', return_value={
        'credentials': {'password': 'my_password'},
    })
    mocker.patch.object(demisto, 'info')
    ilog = IntegrationLogger()
    ilog.write("This is a test with my_password")
    ilog.print_log()
    # assert that the print doesn't contain my_password
    # call_args is tuple (args list, kwargs). we only need the args
    args = demisto.info.call_args[0]
    assert 'This is a test' in args[0]
    assert 'my_password' not in args[0]
    assert '<XX_REPLACED>' in args[0]


def test_logger_init_key_name(mocker):
    mocker.patch.object(demisto, 'params', return_value={
        'key': {'password': 'my_password'},
        'secret': 'my_secret'
    })
    mocker.patch.object(demisto, 'info')
    ilog = IntegrationLogger()
    ilog.write("This is a test with my_password and my_secret")
    ilog.print_log()
    # assert that the print doesn't contain my_password
    # call_args is tuple (args list, kwargs). we only need the args
    args = demisto.info.call_args[0]
    assert 'This is a test' in args[0]
    assert 'my_password' not in args[0]
    assert 'my_secret' not in args[0]
    assert '<XX_REPLACED>' in args[0]


def test_logger_replace_strs(mocker):
    mocker.patch.object(demisto, 'params', return_value={
        'apikey': 'my_apikey',
    })
    ilog = IntegrationLogger()
    ilog.add_replace_strs('special_str', '')  # also check that empty string is not added by mistake
    ilog('my_apikey is special_str and b64: ' + b64_encode('my_apikey'))
    assert ('' not in ilog.replace_strs)
    assert ilog.messages[0] == '<XX_REPLACED> is <XX_REPLACED> and b64: <XX_REPLACED>'


TEST_SSH_KEY = '-----BEGIN OPENSSH PRIVATE KEY-----\nb3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAACFw' \
               'AAAAdzc2gtcn\n-----END OPENSSH PRIVATE KEY-----'

SENSITIVE_PARAM = {
    'app': None,
    'authentication': {
        'credential': '',
        'credentials': {
            'id': '',
            'locked': False,
            'modified': '0001-01-01T00: 00: 00Z',
            'name': '',
            'password': 'cred_pass',
            'sortValues': None,
            'sshkey': TEST_SSH_KEY,
            'sshkeyPass': 'ssh_key_secret_pass',
            'user': '',
            'vaultInstanceId': '',
            'version': 0,
            'workgroup': ''
        },
        'identifier': 'admin',
        'password': 'ident_pass',
        'passwordChanged': False
    },
}


def test_logger_replace_strs_credentials(mocker):
    mocker.patch.object(demisto, 'params', return_value=SENSITIVE_PARAM)
    ilog = IntegrationLogger()
    # log some secrets
    ilog('my cred pass: cred_pass. my ssh key: ssh_key_secret. my ssh pass: ssh_key_secret_pass. ident: ident_pass:')
    for s in ('cred_pass', TEST_SSH_KEY, 'ssh_key_secret_pass', 'ident_pass'):
        assert s not in ilog.messages[0]


def test_debug_logger_replace_strs(mocker):
    mocker.patch.object(demisto, 'params', return_value=SENSITIVE_PARAM)
    debug_logger = DebugLogger()
    debug_logger.int_logger.set_buffering(True)
    debug_logger.log_start_debug()
    msg = debug_logger.int_logger.messages[0]
    assert 'debug-mode started' in msg
    assert 'Params:' in msg
    for s in ('cred_pass', 'ssh_key_secret', 'ssh_key_secret_pass', 'ident_pass'):
        assert s not in msg


def test_is_mac_address():
    from CommonServerPython import is_mac_address

    mac_address_false = 'AA:BB:CC:00:11'
    mac_address_true = 'AA:BB:CC:00:11:22'

    assert (is_mac_address(mac_address_false) is False)
    assert (is_mac_address(mac_address_true))


def test_return_error_command(mocker):
    from CommonServerPython import return_error
    err_msg = "Testing unicode Ё"
    outputs = {'output': 'error'}
    expected_error = {
        'Type': entryTypes['error'],
        'ContentsFormat': formats['text'],
        'Contents': err_msg,
        "EntryContext": outputs
    }

    # Test command that is not fetch-incidents
    mocker.patch.object(demisto, 'command', return_value="test-command")
    mocker.patch.object(sys, 'exit')
    mocker.spy(demisto, 'results')
    return_error(err_msg, '', outputs)
    assert str(demisto.results.call_args) == "call({})".format(expected_error)


def test_return_error_fetch_incidents(mocker):
    from CommonServerPython import return_error
    err_msg = "Testing unicode Ё"

    # Test fetch-incidents
    mocker.patch.object(demisto, 'command', return_value="fetch-incidents")
    returned_error = False
    try:
        return_error(err_msg)
    except Exception as e:
        returned_error = True
        assert str(e) == err_msg
    assert returned_error


def test_return_error_fetch_indicators(mocker):
    from CommonServerPython import return_error
    err_msg = "Testing unicode Ё"

    # Test fetch-indicators
    mocker.patch.object(demisto, 'command', return_value="fetch-indicators")
    returned_error = False
    try:
        return_error(err_msg)
    except Exception as e:
        returned_error = True
        assert str(e) == err_msg
    assert returned_error


def test_return_error_long_running_execution(mocker):
    from CommonServerPython import return_error
    err_msg = "Testing unicode Ё"

    # Test long-running-execution
    mocker.patch.object(demisto, 'command', return_value="long-running-execution")
    returned_error = False
    try:
        return_error(err_msg)
    except Exception as e:
        returned_error = True
        assert str(e) == err_msg
    assert returned_error


def test_return_error_script(mocker, monkeypatch):
    from CommonServerPython import return_error
    mocker.patch.object(sys, 'exit')
    mocker.spy(demisto, 'results')
    monkeypatch.delattr(demisto, 'command')
    err_msg = "Testing unicode Ё"
    outputs = {'output': 'error'}
    expected_error = {
        'Type': entryTypes['error'],
        'ContentsFormat': formats['text'],
        'Contents': err_msg,
        "EntryContext": outputs
    }

    assert not hasattr(demisto, 'command')
    return_error(err_msg, '', outputs)
    assert str(demisto.results.call_args) == "call({})".format(expected_error)


def test_exception_in_return_error(mocker):
    from CommonServerPython import return_error, IntegrationLogger

    expected = {'EntryContext': None, 'Type': 4, 'ContentsFormat': 'text', 'Contents': 'Message'}
    mocker.patch.object(demisto, 'results')
    mocker.patch.object(IntegrationLogger, '__call__')
    with raises(SystemExit, match='0'):
        return_error("Message", error=ValueError("Error!"))
    results = demisto.results.call_args[0][0]
    assert expected == results
    # IntegrationLogger = LOG (2 times if exception supplied)
    assert IntegrationLogger.__call__.call_count == 2


def test_get_demisto_version(mocker, clear_version_cache):
    # verify expected server version and build returned in case Demisto class has attribute demistoVersion
    mocker.patch.object(
        demisto,
        'demistoVersion',
        return_value={
            'version': '5.0.0',
            'buildNumber': '50000'
        }
    )
    assert get_demisto_version() == {
        'version': '5.0.0',
        'buildNumber': '50000'
    }
    # call again to check cache
    assert get_demisto_version() == {
        'version': '5.0.0',
        'buildNumber': '50000'
    }
    # call count should be 1 as we cached
    assert demisto.demistoVersion.call_count == 1
    # test is_demisto_version_ge
    assert is_demisto_version_ge('5.0.0')
    assert is_demisto_version_ge('4.5.0')
    assert not is_demisto_version_ge('5.5.0')
    assert get_demisto_version_as_str() == '5.0.0-50000'


def test_is_demisto_version_ge_4_5(mocker, clear_version_cache):
    get_version_patch = mocker.patch('CommonServerPython.get_demisto_version')
    get_version_patch.side_effect = AttributeError('simulate missing demistoVersion')
    assert not is_demisto_version_ge('5.0.0')
    assert not is_demisto_version_ge('6.0.0')
    with raises(AttributeError, match='simulate missing demistoVersion'):
        is_demisto_version_ge('4.5.0')


def test_is_demisto_version_build_ge(mocker):
    mocker.patch.object(
        demisto,
        'demistoVersion',
        return_value={
            'version': '6.0.0',
            'buildNumber': '50000'
        }
    )
    assert is_demisto_version_ge('6.0.0', '49999')
    assert is_demisto_version_ge('6.0.0', '50000')
    assert not is_demisto_version_ge('6.0.0', '50001')
    assert not is_demisto_version_ge('6.1.0', '49999')
    assert not is_demisto_version_ge('5.5.0', '50001')


def test_assign_params():
    from CommonServerPython import assign_params
    res = assign_params(a='1', b=True, c=None, d='')
    assert res == {'a': '1', 'b': True}


class TestBuildDBotEntry(object):
    def test_build_dbot_entry(self):
        from CommonServerPython import build_dbot_entry
        res = build_dbot_entry('user@example.com', 'Email', 'Vendor', 1)
        assert res == {'DBotScore': {'Indicator': 'user@example.com', 'Type': 'email', 'Vendor': 'Vendor', 'Score': 1}}

    def test_build_dbot_entry_no_malicious(self):
        from CommonServerPython import build_dbot_entry
        res = build_dbot_entry('user@example.com', 'Email', 'Vendor', 3, build_malicious=False)
        assert res == {'DBotScore': {'Indicator': 'user@example.com', 'Type': 'email', 'Vendor': 'Vendor', 'Score': 3}}

    def test_build_dbot_entry_malicious(self):
        from CommonServerPython import build_dbot_entry, outputPaths
        res = build_dbot_entry('user@example.com', 'Email', 'Vendor', 3, 'Malicious email')

        assert res == {
            "DBotScore": {
                "Vendor": "Vendor",
                "Indicator": "user@example.com",
                "Score": 3,
                "Type": "email"
            },
            outputPaths['email']: {
                "Malicious": {
                    "Vendor": "Vendor",
                    "Description": "Malicious email"
                },
                "Address": "user@example.com"
            }
        }

    def test_build_malicious_dbot_entry_file(self):
        from CommonServerPython import build_malicious_dbot_entry, outputPaths
        res = build_malicious_dbot_entry('md5hash', 'MD5', 'Vendor', 'Google DNS')
        assert res == {
            outputPaths['file']:
                {"Malicious": {"Vendor": "Vendor", "Description": "Google DNS"}, "MD5": "md5hash"}}

    def test_build_malicious_dbot_entry(self):
        from CommonServerPython import build_malicious_dbot_entry, outputPaths
        res = build_malicious_dbot_entry('8.8.8.8', 'ip', 'Vendor', 'Google DNS')
        assert res == {outputPaths['ip']: {
            'Address': '8.8.8.8', 'Malicious': {'Vendor': 'Vendor', 'Description': 'Google DNS'}}}

    def test_build_malicious_dbot_entry_wrong_indicator_type(self):
        from CommonServerPython import build_malicious_dbot_entry, DemistoException
        with raises(DemistoException, match='Wrong indicator type'):
            build_malicious_dbot_entry('8.8.8.8', 'notindicator', 'Vendor', 'Google DNS')

    def test_illegal_dbot_score(self):
        from CommonServerPython import build_dbot_entry, DemistoException
        with raises(DemistoException, match='illegal DBot score'):
            build_dbot_entry('1', 'ip', 'Vendor', 8)

    def test_illegal_indicator_type(self):
        from CommonServerPython import build_dbot_entry, DemistoException
        with raises(DemistoException, match='illegal indicator type'):
            build_dbot_entry('1', 'NOTHING', 'Vendor', 2)

    def test_file_indicators(self):
        from CommonServerPython import build_dbot_entry, outputPaths
        res = build_dbot_entry('md5hash', 'md5', 'Vendor', 3)
        assert res == {
            "DBotScore": {
                "Indicator": "md5hash",
                "Type": "file",
                "Vendor": "Vendor",
                "Score": 3
            },
            outputPaths['file']: {
                "MD5": "md5hash",
                "Malicious": {
                    "Vendor": "Vendor",
                    "Description": None
                }
            }
        }


class TestCommandResults:
    def test_multiple_outputs_keys(self):
        """
        Given
        - File has 3 unique keys. sha256, md5 and sha1

        When
        - creating CommandResults with outputs_key_field=[sha1, sha256, md5]

        Then
        - entrycontext DT expression contains all 3 unique fields
        """
        from CommonServerPython import CommandResults

        files = [
            {
                'sha256': '111',
                'sha1': '111',
                'md5': '111'
            },
            {
                'sha256': '222',
                'sha1': '222',
                'md5': '222'
            }
        ]
        results = CommandResults(outputs_prefix='File', outputs_key_field=['sha1', 'sha256', 'md5'], outputs=files)

        assert list(results.to_context()['EntryContext'].keys())[0] == \
               'File(val.sha1 == obj.sha1 && val.sha256 == obj.sha256 && val.md5 == obj.md5)'

    def test_output_prefix_includes_dt(self):
        """
        Given
        - Returning File with only outputs_prefix which includes DT in it
        - outputs key fields are not provided

        When
        - creating CommandResults

        Then
        - EntryContext key should contain only the outputs_prefix
        """
        from CommonServerPython import CommandResults

        files = []
        results = CommandResults(outputs_prefix='File(val.sha1 == obj.sha1 && val.md5 == obj.md5)',
                                 outputs_key_field='', outputs=files)

        assert list(results.to_context()['EntryContext'].keys())[0] == \
               'File(val.sha1 == obj.sha1 && val.md5 == obj.md5)'

    def test_readable_only_context(self):
        """
        Given:
        - Markdown entry to CommandResults

        When:
        - Returning results

        Then:
        - Validate HumanReadable exists
        """
        from CommonServerPython import CommandResults
        markdown = '## Something'
        context = CommandResults(readable_output=markdown).to_context()
        assert context.get('HumanReadable') == markdown

    def test_empty_outputs(self):
        """
        Given:
        - Empty outputs

        When:
        - Returning results

        Then:
        - Validate EntryContext key value

        """
        from CommonServerPython import CommandResults
        res = CommandResults(
            outputs_prefix='FoundIndicators',
            outputs_key_field='value',
            outputs=[]
        )
        context = res.to_context()
        assert {'FoundIndicators(val.value == obj.value)': []} == context.get('EntryContext')

    def test_return_command_results(self, clear_version_cache):
        from CommonServerPython import Common, CommandResults, EntryFormat, EntryType, DBotScoreType

        dbot_score = Common.DBotScore(
            indicator='8.8.8.8',
            integration_name='Virus Total',
            indicator_type=DBotScoreType.IP,
            score=Common.DBotScore.GOOD
        )

        ip = Common.IP(
            ip='8.8.8.8',
            dbot_score=dbot_score,
            asn='some asn',
            hostname='test.com',
            geo_country=None,
            geo_description=None,
            geo_latitude=None,
            geo_longitude=None,
            positive_engines=None,
            detection_engines=None
        )

        results = CommandResults(
            outputs_key_field=None,
            outputs_prefix=None,
            outputs=None,
            indicators=[ip]
        )

        assert results.to_context() == {
            'Type': EntryType.NOTE,
            'ContentsFormat': EntryFormat.JSON,
            'Contents': None,
            'HumanReadable': None,
            'EntryContext': {
                'IP(val.Address && val.Address == obj.Address)': [
                    {
                        'Address': '8.8.8.8',
                        'ASN': 'some asn',
                        'Hostname': 'test.com'
                    }
                ],
                'DBotScore(val.Indicator && val.Indicator == obj.Indicator && '
                'val.Vendor == obj.Vendor && val.Type == obj.Type)': [
                    {
                        'Indicator': '8.8.8.8',
                        'Vendor': 'Virus Total',
                        'Score': 1,
                        'Type': 'ip'
                    }
                ]
            },
            'IndicatorTimeline': []
        }

    def test_multiple_indicators(self, clear_version_cache):
        from CommonServerPython import Common, CommandResults, EntryFormat, EntryType, DBotScoreType
        dbot_score1 = Common.DBotScore(
            indicator='8.8.8.8',
            integration_name='Virus Total',
            indicator_type=DBotScoreType.IP,
            score=Common.DBotScore.GOOD
        )
        ip1 = Common.IP(
            ip='8.8.8.8',
            dbot_score=dbot_score1,
            asn='some asn',
            hostname='test.com',
            geo_country=None,
            geo_description=None,
            geo_latitude=None,
            geo_longitude=None,
            positive_engines=None,
            detection_engines=None
        )

        dbot_score2 = Common.DBotScore(
            indicator='5.5.5.5',
            integration_name='Virus Total',
            indicator_type=DBotScoreType.IP,
            score=Common.DBotScore.GOOD
        )
        ip2 = Common.IP(
            ip='5.5.5.5',
            dbot_score=dbot_score2,
            asn='some asn',
            hostname='test.com',
            geo_country=None,
            geo_description=None,
            geo_latitude=None,
            geo_longitude=None,
            positive_engines=None,
            detection_engines=None
        )

        results = CommandResults(
            outputs_key_field=None,
            outputs_prefix=None,
            outputs=None,
            indicators=[ip1, ip2]
        )

        assert results.to_context() == {
            'Type': EntryType.NOTE,
            'ContentsFormat': EntryFormat.JSON,
            'Contents': None,
            'HumanReadable': None,
            'EntryContext': {
                'IP(val.Address && val.Address == obj.Address)': [
                    {
                        'Address': '8.8.8.8',
                        'ASN': 'some asn',
                        'Hostname': 'test.com'
                    },
                    {
                        'Address': '5.5.5.5',
                        'ASN': 'some asn',
                        'Hostname': 'test.com'
                    }
                ],
                'DBotScore(val.Indicator && val.Indicator == obj.Indicator && '
                'val.Vendor == obj.Vendor && val.Type == obj.Type)': [
                    {
                        'Indicator': '8.8.8.8',
                        'Vendor': 'Virus Total',
                        'Score': 1,
                        'Type': 'ip'
                    },
                    {
                        'Indicator': '5.5.5.5',
                        'Vendor': 'Virus Total',
                        'Score': 1,
                        'Type': 'ip'
                    }
                ]
            },
            'IndicatorTimeline': []
        }

    def test_return_list_of_items(self, clear_version_cache):
        from CommonServerPython import CommandResults, EntryFormat, EntryType
        tickets = [
            {
                'ticket_id': 1,
                'title': 'foo'
            },
            {
                'ticket_id': 2,
                'title': 'goo'
            }
        ]
        results = CommandResults(
            outputs_prefix='Jira.Ticket',
            outputs_key_field='ticket_id',
            outputs=tickets
        )

        assert results.to_context() == {
            'Type': EntryType.NOTE,
            'ContentsFormat': EntryFormat.JSON,
            'Contents': tickets,
            'HumanReadable': tableToMarkdown('Results', tickets),
            'EntryContext': {
                'Jira.Ticket(val.ticket_id == obj.ticket_id)': tickets
            },
            'IndicatorTimeline': []
        }

    def test_return_list_of_items_the_old_way(self):
        from CommonServerPython import CommandResults, EntryFormat, EntryType
        tickets = [
            {
                'ticket_id': 1,
                'title': 'foo'
            },
            {
                'ticket_id': 2,
                'title': 'goo'
            }
        ]
        results = CommandResults(
            outputs_prefix=None,
            outputs_key_field=None,
            outputs={
                'Jira.Ticket(val.ticket_id == obj.ticket_id)': tickets
            },
            raw_response=tickets
        )

        assert sorted(results.to_context()) == sorted({
            'Type': EntryType.NOTE,
            'ContentsFormat': EntryFormat.JSON,
            'Contents': tickets,
            'HumanReadable': None,
            'EntryContext': {
                'Jira.Ticket(val.ticket_id == obj.ticket_id)': tickets
            },
            'IndicatorTimeline': []
        })

    def test_create_dbot_score_with_invalid_score(self):
        from CommonServerPython import Common, DBotScoreType

        try:
            Common.DBotScore(
                indicator='8.8.8.8',
                integration_name='Virus Total',
                score=100,
                indicator_type=DBotScoreType.IP
            )

            assert False
        except TypeError:
            assert True

    def test_create_domain(self):
        from CommonServerPython import CommandResults, Common, EntryType, EntryFormat, DBotScoreType

        dbot_score = Common.DBotScore(
            indicator='somedomain.com',
            integration_name='Virus Total',
            indicator_type=DBotScoreType.DOMAIN,
            score=Common.DBotScore.GOOD
        )

        domain = Common.Domain(
            domain='somedomain.com',
            dbot_score=dbot_score,
            dns='dns.somedomain',
            detection_engines=10,
            positive_detections=5,
            organization='Some Organization',
            admin_phone='18000000',
            admin_email='admin@test.com',

            registrant_name='Mr Registrant',

            registrar_name='Mr Registrar',
            registrar_abuse_email='registrar@test.com',
            creation_date='2019-01-01T00:00:00',
            updated_date='2019-01-02T00:00:00',
            expiration_date=None,
            domain_status='ACTIVE',
            name_servers=[
                'PNS31.CLOUDNS.NET',
                'PNS32.CLOUDNS.NET'
            ],
            sub_domains=[
                'sub-domain1.somedomain.com',
                'sub-domain2.somedomain.com',
                'sub-domain3.somedomain.com'
            ]
        )

        results = CommandResults(
            outputs_key_field=None,
            outputs_prefix=None,
            outputs=None,
            indicators=[domain]
        )

        assert results.to_context() == {
            'Type': EntryType.NOTE,
            'ContentsFormat': EntryFormat.JSON,
            'Contents': None,
            'HumanReadable': None,
            'EntryContext': {
                'Domain(val.Name && val.Name == obj.Name)': [
                    {
                        "Name": "somedomain.com",
                        "DNS": "dns.somedomain",
                        "DetectionEngines": 10,
                        "PositiveDetections": 5,
                        "Registrar": {
                            "Name": "Mr Registrar",
                            "AbuseEmail": "registrar@test.com",
                            "AbusePhone": None
                        },
                        "Registrant": {
                            "Name": "Mr Registrant",
                            "Email": None,
                            "Phone": None,
                            "Country": None
                        },
                        "Admin": {
                            "Name": None,
                            "Email": "admin@test.com",
                            "Phone": "18000000",
                            "Country": None
                        },
                        "Organization": "Some Organization",
                        "Subdomains": [
                            "sub-domain1.somedomain.com",
                            "sub-domain2.somedomain.com",
                            "sub-domain3.somedomain.com"
                        ],
                        "DomainStatus": "ACTIVE",
                        "CreationDate": "2019-01-01T00:00:00",
                        "UpdatedDate": "2019-01-02T00:00:00",
                        "NameServers": [
                            "PNS31.CLOUDNS.NET",
                            "PNS32.CLOUDNS.NET"
                        ],
                        "WHOIS": {
                            "Registrar": {
                                "Name": "Mr Registrar",
                                "AbuseEmail": "registrar@test.com",
                                "AbusePhone": None
                            },
                            "Registrant": {
                                "Name": "Mr Registrant",
                                "Email": None,
                                "Phone": None,
                                "Country": None
                            },
                            "Admin": {
                                "Name": None,
                                "Email": "admin@test.com",
                                "Phone": "18000000",
                                "Country": None
                            },
                            "DomainStatus": "ACTIVE",
                            "CreationDate": "2019-01-01T00:00:00",
                            "UpdatedDate": "2019-01-02T00:00:00",
                            "NameServers": [
                                "PNS31.CLOUDNS.NET",
                                "PNS32.CLOUDNS.NET"
                            ]
                        }
                    }
                ],
                'DBotScore(val.Indicator && val.Indicator == obj.Indicator && '
                'val.Vendor == obj.Vendor && val.Type == obj.Type)': [
                    {
                        'Indicator': 'somedomain.com',
                        'Vendor': 'Virus Total',
                        'Score': 1,
                        'Type': 'domain'
                    }
                ]
            },
            'IndicatorTimeline': []
        }

    def test_indicator_timeline_with_list_of_indicators(self):
        """
       Given:
           -  a list of an indicator
       When
           - creating an IndicatorTimeline object
           - creating a CommandResults objects using the IndicatorTimeline object
       Then
           - the IndicatorTimeline receives the appropriate category and message
       """
        from CommonServerPython import CommandResults, IndicatorsTimeline

        indicators = ['8.8.8.8']
        timeline = IndicatorsTimeline(indicators=indicators, category='test', message='message')

        results = CommandResults(
            outputs_prefix=None,
            outputs_key_field=None,
            outputs=None,
            raw_response=indicators,
            indicators_timeline=timeline
        )

        assert sorted(results.to_context().get('IndicatorTimeline')) == sorted([
            {'Value': '8.8.8.8', 'Category': 'test', 'Message': 'message'}
        ])

    def test_indicator_timeline_running_from_an_integration(self, mocker):
        """
       Given:
           -  a list of an indicator
       When
           - mocking the demisto.params()
           - creating an IndicatorTimeline object
           - creating a CommandResults objects using the IndicatorTimeline object
       Then
           - the IndicatorTimeline receives the appropriate category and message
       """
        from CommonServerPython import CommandResults, IndicatorsTimeline
        mocker.patch.object(demisto, 'params', return_value={'insecure': True})
        indicators = ['8.8.8.8']
        timeline = IndicatorsTimeline(indicators=indicators)

        results = CommandResults(
            outputs_prefix=None,
            outputs_key_field=None,
            outputs=None,
            raw_response=indicators,
            indicators_timeline=timeline
        )

        assert sorted(results.to_context().get('IndicatorTimeline')) == sorted([
            {'Value': '8.8.8.8', 'Category': 'Integration Update'}
        ])

    def test_single_indicator(self, mocker):
        """
        Given:
            - a single indicator
        When
           - mocking the demisto.params()
           - creating an Common.IP object
           - creating a CommandResults objects using the indicator member
       Then
           - The CommandResults.to_context() returns single result of standard output IP and DBotScore
       """
        from CommonServerPython import CommandResults, Common, DBotScoreType
        mocker.patch.object(demisto, 'params', return_value={'insecure': True})
        dbot_score = Common.DBotScore(
            indicator='8.8.8.8',
            integration_name='Virus Total',
            indicator_type=DBotScoreType.IP,
            score=Common.DBotScore.GOOD
        )

        ip = Common.IP(
            ip='8.8.8.8',
            dbot_score=dbot_score
        )

        results = CommandResults(
            indicator=ip
        )

        assert results.to_context()['EntryContext'] == {
          'IP(val.Address && val.Address == obj.Address)': [
            {
              'Address': '8.8.8.8'
            }
          ],
          'DBotScore(val.Indicator && val.Indicator == '
          'obj.Indicator && val.Vendor == obj.Vendor && val.Type == obj.Type)': [
            {
              'Indicator': '8.8.8.8',
              'Type': 'ip',
              'Vendor': 'Virus Total',
              'Score': 1
            }
          ]
        }

    def test_single_indicator_with_indicators(self, mocker):
        """
        Given:
            - a single indicator and a list of indicators
        When
           - mocking the demisto.params()
           - creating an Common.IP object
           - creating a CommandResults objects using the indicator member AND indicators member
       Then
           - The CommandResults.__init__() should raise an ValueError with appropriate error
       """
        from CommonServerPython import CommandResults, Common, DBotScoreType
        mocker.patch.object(demisto, 'params', return_value={'insecure': True})
        dbot_score = Common.DBotScore(
            indicator='8.8.8.8',
            integration_name='Virus Total',
            indicator_type=DBotScoreType.IP,
            score=Common.DBotScore.GOOD
        )

        ip = Common.IP(
            ip='8.8.8.8',
            dbot_score=dbot_score
        )

        with pytest.raises(ValueError) as e:
            CommandResults(
                indicator=ip,
                indicators=[ip]
            )
        assert e.value.args[0] == 'indicators is DEPRECATED, use only indicator'


class TestBaseClient:
    from CommonServerPython import BaseClient
    text = {"status": "ok"}
    client = BaseClient('http://example.com/api/v2/', ok_codes=(200, 201))

    RETRIES_POSITIVE_TEST = [
        'get',
        'put',
        'post'
    ]

    @pytest.mark.skip(reason="Test - too long, only manual")
    @pytest.mark.parametrize('method', RETRIES_POSITIVE_TEST)
    def test_http_requests_with_retry_sanity(self, method):
        """
            Given
            - A base client

            When
            - Making http request call with retries configured to a number higher then 0

            Then
            -  Ensure a successful request return response as expected
        """
        url = 'http://httpbin.org/{}'.format(method)
        res = self.client._http_request(method,
                                        '',
                                        full_url=url,
                                        retries=1,
                                        status_list_to_retry=[401])
        assert res['url'] == url

    RETRIES_NEGATIVE_TESTS_INPUT = [
        ('get', 400), ('get', 401), ('get', 500),
        ('put', 400), ('put', 401), ('put', 500),
        ('post', 400), ('post', 401), ('post', 500),
    ]

    @pytest.mark.skip(reason="Test - too long, only manual")
    @pytest.mark.parametrize('method, status', RETRIES_NEGATIVE_TESTS_INPUT)
    def test_http_requests_with_retry_negative_sanity(self, method, status):
        """
            Given
            - A base client

            When
            - Making http request call with retries configured to a number higher then 0

            Then
            -  An unsuccessful request returns a DemistoException regardless the bad status code.
        """
        from CommonServerPython import DemistoException
        with raises(DemistoException, match='{}'.format(status)):
            self.client._http_request(method,
                                      '',
                                      full_url='http://httpbin.org/status/{}'.format(status),
                                      retries=3,
                                      status_list_to_retry=[400, 401, 500])

    def test_http_request_json(self, requests_mock):
        requests_mock.get('http://example.com/api/v2/event', text=json.dumps(self.text))
        res = self.client._http_request('get', 'event')
        assert res == self.text

    def test_http_request_json_negative(self, requests_mock):
        from CommonServerPython import DemistoException
        requests_mock.get('http://example.com/api/v2/event', text='notjson')
        with raises(DemistoException, match="Failed to parse json"):
            self.client._http_request('get', 'event')

    def test_http_request_text(self, requests_mock):
        requests_mock.get('http://example.com/api/v2/event', text=json.dumps(self.text))
        res = self.client._http_request('get', 'event', resp_type='text')
        assert res == json.dumps(self.text)

    def test_http_request_content(self, requests_mock):
        requests_mock.get('http://example.com/api/v2/event', content=str.encode(json.dumps(self.text)))
        res = self.client._http_request('get', 'event', resp_type='content')
        assert json.loads(res) == self.text

    def test_http_request_response(self, requests_mock):
        requests_mock.get('http://example.com/api/v2/event')
        res = self.client._http_request('get', 'event', resp_type='response')
        assert isinstance(res, requests.Response)

    def test_http_request_not_ok(self, requests_mock):
        from CommonServerPython import DemistoException
        requests_mock.get('http://example.com/api/v2/event', status_code=500)
        with raises(DemistoException, match="[500]"):
            self.client._http_request('get', 'event')

    def test_http_request_not_ok_but_ok(self, requests_mock):
        requests_mock.get('http://example.com/api/v2/event', status_code=500)
        res = self.client._http_request('get', 'event', resp_type='response', ok_codes=(500,))
        assert res.status_code == 500

    def test_http_request_not_ok_with_json(self, requests_mock):
        from CommonServerPython import DemistoException
        requests_mock.get('http://example.com/api/v2/event', status_code=500, content=str.encode(json.dumps(self.text)))
        with raises(DemistoException, match="Error in API call"):
            self.client._http_request('get', 'event')

    def test_http_request_not_ok_with_json_parsing(self, requests_mock):
        from CommonServerPython import DemistoException
        requests_mock.get('http://example.com/api/v2/event', status_code=500, content=str.encode(json.dumps(self.text)))
        with raises(DemistoException) as exception:
            self.client._http_request('get', 'event')
        message = str(exception.value)
        response_json_error = json.loads(message.split('\n')[1])
        assert response_json_error == self.text

    def test_http_request_timeout(self, requests_mock):
        from CommonServerPython import DemistoException
        requests_mock.get('http://example.com/api/v2/event', exc=requests.exceptions.ConnectTimeout)
        with raises(DemistoException, match="Connection Timeout Error"):
            self.client._http_request('get', 'event')

    def test_http_request_ssl_error(self, requests_mock):
        from CommonServerPython import DemistoException
        requests_mock.get('http://example.com/api/v2/event', exc=requests.exceptions.SSLError)
        with raises(DemistoException, match="SSL Certificate Verification Failed"):
            self.client._http_request('get', 'event', resp_type='response')

    def test_http_request_proxy_error(self, requests_mock):
        from CommonServerPython import DemistoException
        requests_mock.get('http://example.com/api/v2/event', exc=requests.exceptions.ProxyError)
        with raises(DemistoException, match="Proxy Error"):
            self.client._http_request('get', 'event', resp_type='response')

    def test_http_request_connection_error(self, requests_mock):
        from CommonServerPython import DemistoException
        requests_mock.get('http://example.com/api/v2/event', exc=requests.exceptions.ConnectionError)
        with raises(DemistoException, match="Verify that the server URL parameter"):
            self.client._http_request('get', 'event', resp_type='response')

    def test_text_exception_parsing(self, requests_mock):
        from CommonServerPython import DemistoException
        reason = 'Bad Request'
        text = 'additional text'
        requests_mock.get('http://example.com/api/v2/event',
                          status_code=400,
                          reason=reason,
                          text=text)
        with raises(DemistoException, match='- {}\n{}'.format(reason, text)):
            self.client._http_request('get', 'event', resp_type='text')

    def test_json_exception_parsing(self, requests_mock):
        from CommonServerPython import DemistoException
        reason = 'Bad Request'
        json_response = {'error': 'additional text'}
        requests_mock.get('http://example.com/api/v2/event',
                          status_code=400,
                          reason=reason,
                          json=json_response)
        with raises(DemistoException, match='- {}\n.*{}'.format(reason, json_response["error"])):
            self.client._http_request('get', 'event', resp_type='text')

    def test_exception_response_json_parsing_when_ok_code_is_invalid(self, requests_mock):
        from CommonServerPython import DemistoException
        reason = 'Bad Request'
        json_response = {'error': 'additional text'}
        requests_mock.get('http://example.com/api/v2/event',
                          status_code=400,
                          reason=reason,
                          json=json_response)
        try:
            self.client._http_request('get', 'event', resp_type='text', ok_codes=(200,))
        except DemistoException as e:
            assert e.res.get('error') == 'additional text'

    def test_exception_response_text_parsing_when_ok_code_is_invalid(self, requests_mock):
        from CommonServerPython import DemistoException
        reason = 'Bad Request'
        text_response = '{"error": "additional text"}'
        requests_mock.get('http://example.com/api/v2/event',
                          status_code=400,
                          reason=reason,
                          text=text_response)
        try:
            self.client._http_request('get', 'event', resp_type='text', ok_codes=(200,))
        except DemistoException as e:
            assert e.res.get('error') == 'additional text'

    def test_exception_response_parsing_fails_when_ok_code_is_invalid(self, requests_mock):
        from CommonServerPython import DemistoException
        reason = 'Bad Request'
        text_response = 'Bad Request'
        requests_mock.get('http://example.com/api/v2/event',
                          status_code=400,
                          reason=reason,
                          text=text_response)
        try:
            self.client._http_request('get', 'event', resp_type='text', ok_codes=(200,))
        except DemistoException as e:
            assert isinstance(e.res, dict) and not e.res

    def test_is_valid_ok_codes_empty(self):
        from requests import Response
        from CommonServerPython import BaseClient
        new_client = BaseClient('http://example.com/api/v2/')
        response = Response()
        response.status_code = 200
        assert new_client._is_status_code_valid(response, None)

    def test_is_valid_ok_codes_from_function(self):
        from requests import Response
        response = Response()
        response.status_code = 200
        assert self.client._is_status_code_valid(response, (200, 201))

    def test_is_valid_ok_codes_from_self(self):
        from requests import Response
        response = Response()
        response.status_code = 200
        assert self.client._is_status_code_valid(response, None)

    def test_is_valid_ok_codes_empty_false(self):
        from requests import Response
        response = Response()
        response.status_code = 400
        assert not self.client._is_status_code_valid(response, None)

    def test_is_valid_ok_codes_from_function_false(self):
        from requests import Response
        response = Response()
        response.status_code = 400
        assert not self.client._is_status_code_valid(response, (200, 201))

    def test_is_valid_ok_codes_from_self_false(self):
        from requests import Response
        response = Response()
        response.status_code = 400
        assert not self.client._is_status_code_valid(response)


def test_parse_date_string():
    # test unconverted data remains: Z
    assert parse_date_string('2019-09-17T06:16:39Z') == datetime(2019, 9, 17, 6, 16, 39)

    # test unconverted data remains: .22Z
    assert parse_date_string('2019-09-17T06:16:39.22Z') == datetime(2019, 9, 17, 6, 16, 39, 220000)

    # test time data without ms does not match format with ms
    assert parse_date_string('2019-09-17T06:16:39Z', '%Y-%m-%dT%H:%M:%S.%f') == datetime(2019, 9, 17, 6, 16, 39)

    # test time data with timezone Z does not match format with timezone +05:00
    assert parse_date_string('2019-09-17T06:16:39Z', '%Y-%m-%dT%H:%M:%S+05:00') == datetime(2019, 9, 17, 6, 16, 39)

    # test time data with timezone +05:00 does not match format with timezone Z
    assert parse_date_string('2019-09-17T06:16:39+05:00', '%Y-%m-%dT%H:%M:%SZ') == datetime(2019, 9, 17, 6, 16, 39)

    # test time data with timezone -05:00 and with ms does not match format with timezone +02:00 without ms
    assert parse_date_string(
        '2019-09-17T06:16:39.4040+05:00', '%Y-%m-%dT%H:%M:%S+02:00'
    ) == datetime(2019, 9, 17, 6, 16, 39, 404000)


def test_override_print(mocker):
    mocker.patch.object(demisto, 'info')
    int_logger = IntegrationLogger()
    int_logger.set_buffering(False)
    int_logger.print_override("test", "this")
    assert demisto.info.call_count == 1
    assert demisto.info.call_args[0][0] == "test this"
    demisto.info.reset_mock()
    int_logger.print_override("test", "this", file=sys.stderr)
    assert demisto.info.call_count == 1
    assert demisto.info.call_args[0][0] == "test this"
    buf = StringIO()
    # test writing to custom file (not stdout/stderr)
    int_logger.print_override("test", "this", file=buf)
    assert buf.getvalue() == 'test this\n'


def test_http_client_debug(mocker):
    if not IS_PY3:
        pytest.skip("test not supported in py2")
        return
    mocker.patch.object(demisto, 'info')
    debug_log = DebugLogger()
    from http.client import HTTPConnection
    HTTPConnection.debuglevel = 1
    con = HTTPConnection("google.com")
    con.request('GET', '/')
    r = con.getresponse()
    r.read()
    assert demisto.info.call_count > 5
    assert debug_log is not None


class TestParseDateRange:
    @staticmethod
    def test_utc_time_sanity():
        utc_now = datetime.utcnow()
        utc_start_time, utc_end_time = parse_date_range('2 days', utc=True)
        # testing UTC date time and range of 2 days
        assert utc_now.replace(microsecond=0) == utc_end_time.replace(microsecond=0)
        assert abs(utc_start_time - utc_end_time).days == 2

    @staticmethod
    def test_local_time_sanity():
        local_now = datetime.now()
        local_start_time, local_end_time = parse_date_range('73 minutes', utc=False)
        # testing local datetime and range of 73 minutes
        assert local_now.replace(microsecond=0) == local_end_time.replace(microsecond=0)
        assert abs(local_start_time - local_end_time).seconds / 60 == 73

    @staticmethod
    def test_with_trailing_spaces():
        utc_now = datetime.utcnow()
        utc_start_time, utc_end_time = parse_date_range('2 days   ', utc=True)
        # testing UTC date time and range of 2 days
        assert utc_now.replace(microsecond=0) == utc_end_time.replace(microsecond=0)
        assert abs(utc_start_time - utc_end_time).days == 2

    @staticmethod
    def test_case_insensitive():
        utc_now = datetime.utcnow()
        utc_start_time, utc_end_time = parse_date_range('2 Days', utc=True)
        # testing UTC date time and range of 2 days
        assert utc_now.replace(microsecond=0) == utc_end_time.replace(microsecond=0)
        assert abs(utc_start_time - utc_end_time).days == 2

    @staticmethod
    def test_error__invalid_input_format(mocker):
        mocker.patch.object(sys, 'exit', side_effect=Exception('mock exit'))
        demisto_results = mocker.spy(demisto, 'results')

        try:
            parse_date_range('2 Days ago', utc=True)
        except Exception as exp:
            assert str(exp) == 'mock exit'
        results = demisto.results.call_args[0][0]
        assert 'date_range must be "number date_range_unit"' in results['Contents']

    @staticmethod
    def test_error__invalid_time_value_not_a_number(mocker):
        mocker.patch.object(sys, 'exit', side_effect=Exception('mock exit'))
        demisto_results = mocker.spy(demisto, 'results')

        try:
            parse_date_range('ten Days', utc=True)
        except Exception as exp:
            assert str(exp) == 'mock exit'
        results = demisto.results.call_args[0][0]
        assert 'The time value is invalid' in results['Contents']

    @staticmethod
    def test_error__invalid_time_value_not_an_integer(mocker):
        mocker.patch.object(sys, 'exit', side_effect=Exception('mock exit'))
        demisto_results = mocker.spy(demisto, 'results')

        try:
            parse_date_range('1.5 Days', utc=True)
        except Exception as exp:
            assert str(exp) == 'mock exit'
        results = demisto.results.call_args[0][0]
        assert 'The time value is invalid' in results['Contents']

    @staticmethod
    def test_error__invalid_time_unit(mocker):
        mocker.patch.object(sys, 'exit', side_effect=Exception('mock exit'))
        demisto_results = mocker.spy(demisto, 'results')

        try:
            parse_date_range('2 nights', utc=True)
        except Exception as exp:
            assert str(exp) == 'mock exit'
        results = demisto.results.call_args[0][0]
        assert 'The unit of date_range is invalid' in results['Contents']


def test_encode_string_results():
    s = "test"
    assert s == encode_string_results(s)
    s2 = u"בדיקה"
    if IS_PY3:
        res = str(s2)
    else:
        res = s2.encode("utf8")
    assert encode_string_results(s2) == res
    not_string = [1, 2, 3]
    assert not_string == encode_string_results(not_string)


class TestReturnOutputs:
    def test_return_outputs(self, mocker):
        mocker.patch.object(demisto, 'results')
        md = 'md'
        outputs = {'Event': 1}
        raw_response = {'event': 1}
        return_outputs(md, outputs, raw_response)
        results = demisto.results.call_args[0][0]
        assert len(demisto.results.call_args[0]) == 1
        assert demisto.results.call_count == 1
        assert raw_response == results['Contents']
        assert 'json' == results['ContentsFormat']
        assert outputs == results['EntryContext']
        assert md == results['HumanReadable']

    def test_return_outputs_only_md(self, mocker):
        mocker.patch.object(demisto, 'results')
        md = 'md'
        return_outputs(md)
        results = demisto.results.call_args[0][0]
        assert len(demisto.results.call_args[0]) == 1
        assert demisto.results.call_count == 1
        assert md == results['HumanReadable']
        assert 'text' == results['ContentsFormat']

    def test_return_outputs_raw_none(self, mocker):
        mocker.patch.object(demisto, 'results')
        md = 'md'
        outputs = {'Event': 1}
        return_outputs(md, outputs, None)
        results = demisto.results.call_args[0][0]
        assert len(demisto.results.call_args[0]) == 1
        assert demisto.results.call_count == 1
        assert outputs == results['Contents']
        assert 'json' == results['ContentsFormat']
        assert outputs == results['EntryContext']
        assert md == results['HumanReadable']

    def test_return_outputs_timeline(self, mocker):
        mocker.patch.object(demisto, 'results')
        md = 'md'
        outputs = {'Event': 1}
        raw_response = {'event': 1}
        timeline = [{'Value': 'blah', 'Message': 'test', 'Category': 'test'}]
        return_outputs(md, outputs, raw_response, timeline)
        results = demisto.results.call_args[0][0]
        assert len(demisto.results.call_args[0]) == 1
        assert demisto.results.call_count == 1
        assert raw_response == results['Contents']
        assert 'json' == results['ContentsFormat']
        assert outputs == results['EntryContext']
        assert md == results['HumanReadable']
        assert timeline == results['IndicatorTimeline']

    def test_return_outputs_timeline_without_category(self, mocker):
        mocker.patch.object(demisto, 'results')
        md = 'md'
        outputs = {'Event': 1}
        raw_response = {'event': 1}
        timeline = [{'Value': 'blah', 'Message': 'test'}]
        return_outputs(md, outputs, raw_response, timeline)
        results = demisto.results.call_args[0][0]
        assert len(demisto.results.call_args[0]) == 1
        assert demisto.results.call_count == 1
        assert raw_response == results['Contents']
        assert 'json' == results['ContentsFormat']
        assert outputs == results['EntryContext']
        assert md == results['HumanReadable']
        assert 'Category' in results['IndicatorTimeline'][0].keys()
        assert results['IndicatorTimeline'][0]['Category'] == 'Integration Update'

    def test_return_outputs_ignore_auto_extract(self, mocker):
        mocker.patch.object(demisto, 'results')
        md = 'md'
        outputs = {'Event': 1}
        raw_response = {'event': 1}
        ignore_auto_extract = True
        return_outputs(md, outputs, raw_response, ignore_auto_extract=ignore_auto_extract)
        results = demisto.results.call_args[0][0]
        assert len(demisto.results.call_args[0]) == 1
        assert demisto.results.call_count == 1
        assert raw_response == results['Contents']
        assert 'json' == results['ContentsFormat']
        assert outputs == results['EntryContext']
        assert md == results['HumanReadable']
        assert ignore_auto_extract == results['IgnoreAutoExtract']

    def test_return_outputs_text_raw_response(self, mocker):
        mocker.patch.object(demisto, 'results')
        md = 'md'
        raw_response = 'string'
        return_outputs(md, raw_response=raw_response)
        results = demisto.results.call_args[0][0]
        assert len(demisto.results.call_args[0]) == 1
        assert demisto.results.call_count == 1
        assert raw_response == results['Contents']
        assert 'text' == results['ContentsFormat']


def test_argToBoolean():
    assert argToBoolean('true') is True
    assert argToBoolean('yes') is True
    assert argToBoolean('TrUe') is True
    assert argToBoolean(True) is True

    assert argToBoolean('false') is False
    assert argToBoolean('no') is False
    assert argToBoolean(False) is False


batch_params = [
    # full batch case
    ([1, 2, 3], 1, [[1], [2], [3]]),
    # empty case
    ([], 1, []),
    # out of index case
    ([1, 2, 3], 5, [[1, 2, 3]]),
    # out of index in end with batches
    ([1, 2, 3, 4, 5], 2, [[1, 2], [3, 4], [5]]),
    ([1] * 100, 2, [[1, 1]] * 50)
]


@pytest.mark.parametrize('iterable, sz, expected', batch_params)
def test_batch(iterable, sz, expected):
    for i, item in enumerate(batch(iterable, sz)):
        assert expected[i] == item


regexes_test = [
    (ipv4Regex, '192.168.1.1', True),
    (ipv4Regex, '192.168.1.1/24', False),
    (ipv4Regex, '192.168.a.1', False),
    (ipv4Regex, '192.168..1.1', False),
    (ipv4Regex, '192.256.1.1', False),
    (ipv4Regex, '192.256.1.1.1', False),
    (ipv4cidrRegex, '192.168.1.1/32', True),
    (ipv4cidrRegex, '192.168.1.1.1/30', False),
    (ipv4cidrRegex, '192.168.1.b/30', False),
    (ipv4cidrRegex, '192.168.1.12/381', False),
    (ipv6Regex, '2001:db8:a0b:12f0::1', True),
    (ipv6Regex, '2001:db8:a0b:12f0::1/11', False),
    (ipv6Regex, '2001:db8:a0b:12f0::1::1', False),
    (ipv6Regex, '2001:db8:a0b:12f0::98aa5', False),
    (ipv6cidrRegex, '2001:db8:a0b:12f0::1/64', True),
    (ipv6cidrRegex, '2001:db8:a0b:12f0::1/256', False),
    (ipv6cidrRegex, '2001:db8:a0b:12f0::1::1/25', False),
    (ipv6cidrRegex, '2001:db8:a0b:12f0::1aaasds::1/1', False)
]


@pytest.mark.parametrize('pattern, string, expected', regexes_test)
def test_regexes(pattern, string, expected):
    # (str, str, bool) -> None
    # emulates re.fullmatch from py3.4
    assert expected is bool(re.match("(?:" + pattern + r")\Z", string))


IP_TO_INDICATOR_TYPE_PACK = [
    ('192.168.1.1', FeedIndicatorType.IP),
    ('192.168.1.1/32', FeedIndicatorType.CIDR),
    ('2001:db8:a0b:12f0::1', FeedIndicatorType.IPv6),
    ('2001:db8:a0b:12f0::1/64', FeedIndicatorType.IPv6CIDR),
]


@pytest.mark.parametrize('ip, indicator_type', IP_TO_INDICATOR_TYPE_PACK)
def test_ip_to_indicator(ip, indicator_type):
    assert FeedIndicatorType.ip_to_indicator_type(ip) is indicator_type


data_test_b64_encode = [
    (u'test', 'dGVzdA=='),
    ('test', 'dGVzdA=='),
    (b'test', 'dGVzdA=='),
    ('', ''),
    ('%', 'JQ=='),
    (u'§', 'wqc='),
    (u'§t`e§s`t§', 'wqd0YGXCp3NgdMKn'),
]


@pytest.mark.parametrize('_input, expected_output', data_test_b64_encode)
def test_b64_encode(_input, expected_output):
    output = b64_encode(_input)
    assert output == expected_output, 'b64_encode({}) returns: {} instead: {}'.format(_input, output, expected_output)


def test_traceback_in_return_error_debug_mode_on(mocker):
    mocker.patch.object(demisto, 'command', return_value="test-command")
    mocker.spy(demisto, 'results')
    mocker.patch('CommonServerPython.is_debug_mode', return_value=True)
    from CommonServerPython import return_error

    try:
        raise Exception("This is a test string")
    except Exception:
        with pytest.raises(SystemExit):
            return_error("some text")

    assert "This is a test string" in str(demisto.results.call_args)
    assert "Traceback" in str(demisto.results.call_args)
    assert "some text" in str(demisto.results.call_args)


def test_traceback_in_return_error_debug_mode_off(mocker):
    mocker.patch.object(demisto, 'command', return_value="test-command")
    mocker.spy(demisto, 'results')
    mocker.patch('CommonServerPython.is_debug_mode', return_value=False)
    from CommonServerPython import return_error

    try:
        raise Exception("This is a test string")
    except Exception:
        with pytest.raises(SystemExit):
            return_error("some text")

    assert "This is a test string" not in str(demisto.results.call_args)
    assert "Traceback" not in str(demisto.results.call_args)
    assert "some text" in str(demisto.results.call_args)


# append_context unit test
CONTEXT_MOCK = {
    'str_key': 'str_value',
    'dict_key': {
        'key1': 'val1',
        'key2': 'val2'
    },
    'int_key': 1,
    'list_key_str': ['val1', 'val2'],
    'list_key_list': ['val1', 'val2'],
    'list_key_dict': ['val1', 'val2']
}

UPDATED_CONTEXT = {
    'str_key': 'str_data,str_value',
    'dict_key': {
        'key1': 'val1',
        'key2': 'val2',
        'data_key': 'data_val'
    },
    'int_key': [1, 2],
    'list_key_str': ['val1', 'val2', 'str_data'],
    'list_key_list': ['val1', 'val2', 'val1', 'val2'],
    'list_key_dict': ['val1', 'val2', {'data_key': 'data_val'}]
}

DATA_MOCK_STRING = "str_data"
DATA_MOCK_LIST = ['val1', 'val2']
DATA_MOCK_DICT = {
    'data_key': 'data_val'
}
DATA_MOCK_INT = 2

STR_KEY = "str_key"
DICT_KEY = "dict_key"

APPEND_CONTEXT_INPUT = [
    (CONTEXT_MOCK, DATA_MOCK_STRING, STR_KEY, "key = {}, val = {}".format(STR_KEY, UPDATED_CONTEXT[STR_KEY])),
    (CONTEXT_MOCK, DATA_MOCK_LIST, STR_KEY, "TypeError"),
    (CONTEXT_MOCK, DATA_MOCK_DICT, STR_KEY, "TypeError"),

    (CONTEXT_MOCK, DATA_MOCK_STRING, DICT_KEY, "TypeError"),
    (CONTEXT_MOCK, DATA_MOCK_LIST, DICT_KEY, "TypeError"),
    (CONTEXT_MOCK, DATA_MOCK_DICT, DICT_KEY, "key = {}, val = {}".format(DICT_KEY, UPDATED_CONTEXT[DICT_KEY])),

    (CONTEXT_MOCK, DATA_MOCK_STRING, 'list_key_str',
     "key = {}, val = {}".format('list_key_str', UPDATED_CONTEXT['list_key_str'])),
    (CONTEXT_MOCK, DATA_MOCK_LIST, 'list_key_list',
     "key = {}, val = {}".format('list_key_list', UPDATED_CONTEXT['list_key_list'])),
    (CONTEXT_MOCK, DATA_MOCK_DICT, 'list_key_dict',
     "key = {}, val = {}".format('list_key_dict', UPDATED_CONTEXT['list_key_dict'])),

    (CONTEXT_MOCK, DATA_MOCK_INT, 'int_key', "key = {}, val = {}".format('int_key', UPDATED_CONTEXT['int_key'])),
]


def get_set_context(key, val):
    from CommonServerPython import return_error
    return_error("key = {}, val = {}".format(key, val))


@pytest.mark.parametrize('context_mock, data_mock, key, expected_answer', APPEND_CONTEXT_INPUT)
def test_append_context(mocker, context_mock, data_mock, key, expected_answer):
    from CommonServerPython import demisto
    mocker.patch.object(demisto, 'get', return_value=context_mock.get(key))
    mocker.patch.object(demisto, 'setContext', side_effect=get_set_context)
    mocker.patch.object(demisto, 'results')

    if "TypeError" not in expected_answer:
        with raises(SystemExit, match='0'):
            appendContext(key, data_mock)
            assert expected_answer in demisto.results.call_args[0][0]['Contents']

    else:
        with raises(TypeError) as e:
            appendContext(key, data_mock)
            assert expected_answer in e.value


INDICATOR_VALUE_AND_TYPE = [
    ('3fec1b14cea32bbcd97fad4507b06888', "File"),
    ('1c8893f75089a27ca6a8d49801d7aa6b64ea0c6167fe8b1becfe9bc13f47bdc1', 'File'),
    ('castaneda-thornton.com', 'Domain'),
    ('192.0.0.1', 'IP'),
    ('test@gmail.com', 'Email'),
    ('e775eb1250137c0b83d4e7c4549c71d6f10cae4e708ebf0b5c4613cbd1e91087', 'File'),
    ('test@yahoo.com', 'Email'),
    ('http://test.com', 'URL'),
    ('11.111.11.11/11', 'CIDR'),
    ('CVE-0000-0000', 'CVE'),
    ('dbot@demisto.works', 'Email'),
    ('37b6d02m-63e0-495e-kk92-7c21511adc7a@SB2APC01FT091.outlook.com', 'Email'),
    ('dummy@recipient.com', 'Email'),
    ('image003.gif@01CF4D7F.1DF62650', 'Email'),
    ('bruce.wayne@pharmtech.zz', 'Email'),
    ('joe@gmail.com', 'Email'),
    ('koko@demisto.com', 'Email'),
    ('42a5e275559a1651b3df8e15d3f5912499f0f2d3d1523959c56fc5aea6371e59', 'File'),
    ('10676cf66244cfa91567fbc1a937f4cb19438338b35b69d4bcc2cf0d3a44af5e', 'File'),
    ('52483514f07eb14570142f6927b77deb7b4da99f', 'File'),
    ('c8092abd8d581750c0530fa1fc8d8318', 'File'),
    ('fe80:0000:0000:0000:91ba:7558:26d3:acde', 'IPv6'),
    ('fd60:e22:f1b9::2', 'IPv6'),
    ('2001:db8:0000:0000:0000:0000:0000:0000', 'IPv6'),
    ('112.126.94.107', 'IP'),
    ('a', None),
    ('*castaneda-thornton.com', 'DomainGlob'),
    ('53e6baa124f54462786f1122e98e38ff1be3de82fe2a96b1849a8637043fd847eec7e0f53307bddf7a066565292d500c36c941f1f3bb9dcac807b2f4a0bfce1b', 'File')
]


@pytest.mark.parametrize('indicator_value, indicatory_type', INDICATOR_VALUE_AND_TYPE)
def test_auto_detect_indicator_type(indicator_value, indicatory_type):
    """
        Given
            - Indicator value
            - Indicator type

        When
        - Trying to detect the type of an indicator.

        Then
        -  Run the auto_detect_indicator_type and validate that the indicator type the function returns is as expected.
    """
    if sys.version_info.major == 3 and sys.version_info.minor == 8:
        assert auto_detect_indicator_type(indicator_value) == indicatory_type
    else:
        try:
            auto_detect_indicator_type(indicator_value)
        except Exception as e:
            assert str(e) == "Missing tldextract module, In order to use the auto detect function please" \
                             " use a docker image with it installed such as: demisto/jmespath"


def test_handle_proxy(mocker):
    os.environ['REQUESTS_CA_BUNDLE'] = '/test1.pem'
    mocker.patch.object(demisto, 'params', return_value={'insecure': True})
    handle_proxy()
    assert os.getenv('REQUESTS_CA_BUNDLE') is None
    os.environ['REQUESTS_CA_BUNDLE'] = '/test2.pem'
    mocker.patch.object(demisto, 'params', return_value={})
    handle_proxy()
    assert os.environ['REQUESTS_CA_BUNDLE'] == '/test2.pem'  # make sure no change
    mocker.patch.object(demisto, 'params', return_value={'unsecure': True})
    handle_proxy()
    assert os.getenv('REQUESTS_CA_BUNDLE') is None


@pytest.mark.parametrize(argnames="dict_obj, keys, expected, default_return_value",
                         argvalues=[
                             ({'a': '1'}, ['a'], '1', None),
                             ({'a': {'b': '2'}}, ['a', 'b'], '2', None),
                             ({'a': {'b': '2'}}, ['a', 'c'], 'test', 'test'),
                         ])
def test_safe_get(dict_obj, keys, expected, default_return_value):
    from CommonServerPython import dict_safe_get
    assert expected == dict_safe_get(dict_object=dict_obj,
                                     keys=keys,
                                     default_return_value=default_return_value)


MIRRORS = '''
   [{
     "channel_id":"GKQ86DVPH",
     "channel_name": "incident-681",
     "channel_topic": "incident-681",
     "investigation_id":"681",
     "mirror_type":"all",
     "mirror_direction":"both",
     "mirror_to":"group",
     "auto_close":true,
     "mirrored":true
  },
  {
     "channel_id":"GKB19PA3V",
     "channel_name": "group2",
     "channel_topic": "cooltopic",
     "investigation_id":"684",
     "mirror_type":"all",
     "mirror_direction":"both",
     "mirror_to":"group",
     "auto_close":true,
     "mirrored":true
  },
  {
     "channel_id":"GKB19PA3V",
     "channel_name": "group2",
     "channel_topic": "cooltopic",
     "investigation_id":"692",
     "mirror_type":"all",
     "mirror_direction":"both",
     "mirror_to":"group",
     "auto_close":true,
     "mirrored":true
  },
  {
     "channel_id":"GKNEJU4P9",
     "channel_name": "group3",
     "channel_topic": "incident-713",
     "investigation_id":"713",
     "mirror_type":"all",
     "mirror_direction":"both",
     "mirror_to":"group",
     "auto_close":true,
     "mirrored":true
  },
  {
     "channel_id":"GL8GHC0LV",
     "channel_name": "group5",
     "channel_topic": "incident-734",
     "investigation_id":"734",
     "mirror_type":"all",
     "mirror_direction":"both",
     "mirror_to":"group",
     "auto_close":true,
     "mirrored":true
  }]
'''

CONVERSATIONS = '''[{
    "id": "C012AB3CD",
    "name": "general",
    "is_channel": true,
    "is_group": false,
    "is_im": false,
    "created": 1449252889,
    "creator": "U012A3CDE",
    "is_archived": false,
    "is_general": true,
    "unlinked": 0,
    "name_normalized": "general",
    "is_shared": false,
    "is_ext_shared": false,
    "is_org_shared": false,
    "pending_shared": [],
    "is_pending_ext_shared": false,
    "is_member": true,
    "is_private": false,
    "is_mpim": false,
    "topic": {
        "value": "Company-wide announcements and work-based matters",
        "creator": "",
        "last_set": 0
    },
    "purpose": {
        "value": "This channel is for team-wide communication and announcements. All team members are in this channel.",
        "creator": "",
        "last_set": 0
    },
    "previous_names": [],
    "num_members": 4
},
{
    "id": "C061EG9T2",
    "name": "random",
    "is_channel": true,
    "is_group": false,
    "is_im": false,
    "created": 1449252889,
    "creator": "U061F7AUR",
    "is_archived": false,
    "is_general": false,
    "unlinked": 0,
    "name_normalized": "random",
    "is_shared": false,
    "is_ext_shared": false,
    "is_org_shared": false,
    "pending_shared": [],
    "is_pending_ext_shared": false,
    "is_member": true,
    "is_private": false,
    "is_mpim": false,
    "topic": {
        "value": "Non-work banter and water cooler conversation",
        "creator": "",
        "last_set": 0
    },
    "purpose": {
        "value": "A place for non-work-related flimflam.",
        "creator": "",
        "last_set": 0
    },
    "previous_names": [],
    "num_members": 4
}]'''

OBJECTS_TO_KEYS = {
    'mirrors': 'investigation_id',
    'questions': 'entitlement',
    'users': 'id'
}


def set_integration_context_versioned(integration_context, version=-1, sync=False):
    global INTEGRATION_CONTEXT_VERSIONED

    try:
        if not INTEGRATION_CONTEXT_VERSIONED:
            INTEGRATION_CONTEXT_VERSIONED = {'context': '{}', 'version': 0}
    except NameError:
        INTEGRATION_CONTEXT_VERSIONED = {'context': '{}', 'version': 0}

    current_version = INTEGRATION_CONTEXT_VERSIONED['version']
    if version != -1 and version <= current_version:
        raise ValueError('DB Insert version {} does not match version {}'.format(current_version, version))

    INTEGRATION_CONTEXT_VERSIONED = {'context': integration_context, 'version': current_version + 1}


def get_integration_context_versioned(refresh=False):
    return INTEGRATION_CONTEXT_VERSIONED


def test_merge_lists():
    from CommonServerPython import merge_lists

    # Set
    original = [{'id': '1', 'updated': 'n'}, {'id': '2', 'updated': 'n'}, {'id': '11', 'updated': 'n'}]
    updated = [{'id': '1', 'updated': 'y'}, {'id': '3', 'updated': 'y'}, {'id': '11', 'updated': 'n', 'remove': True}]
    expected = [{'id': '1', 'updated': 'y'}, {'id': '2', 'updated': 'n'}, {'id': '3', 'updated': 'y'}]

    # Arrange
    result = merge_lists(original, updated, 'id')

    # Assert
    assert len(result) == len(expected)
    for obj in result:
        assert obj in expected


@pytest.mark.parametrize('version, expected',
                         [
                             ({'version': '5.5.0'}, False),
                             ({'version': '6.0.0'}, True),
                         ]
                         )
def test_is_versioned_context_available(mocker, version, expected):
    from CommonServerPython import is_versioned_context_available
    # Set
    mocker.patch.object(demisto, 'demistoVersion', return_value=version)

    # Arrange
    result = is_versioned_context_available()
    get_demisto_version._version = None

    # Assert
    assert expected == result


def test_update_context_merge(mocker):
    import CommonServerPython

    # Set
    set_integration_context_versioned({
        'mirrors': MIRRORS,
        'conversations': CONVERSATIONS
    })

    mocker.patch.object(demisto, 'getIntegrationContextVersioned', return_value=get_integration_context_versioned())
    mocker.patch.object(demisto, 'setIntegrationContextVersioned', side_effecet=set_integration_context_versioned)
    mocker.patch.object(CommonServerPython, 'is_versioned_context_available', return_value=True)

    new_mirror = {
        'channel_id': 'new_group',
        'channel_name': 'incident-999',
        'channel_topic': 'incident-999',
        'investigation_id': '999',
        'mirror_type': 'all',
        'mirror_direction': 'both',
        'mirror_to': 'group',
        'auto_close': True,
        'mirrored': False
    }

    mirrors = json.loads(MIRRORS)
    mirrors.extend([new_mirror])

    # Arrange
    context, version = CommonServerPython.update_integration_context({'mirrors': [new_mirror]}, OBJECTS_TO_KEYS, True)
    new_mirrors = json.loads(context['mirrors'])

    # Assert
    assert len(mirrors) == len(new_mirrors)
    for mirror in mirrors:
        assert mirror in new_mirrors

    assert version == get_integration_context_versioned()['version']


def test_update_context_no_merge(mocker):
    import CommonServerPython

    # Set
    set_integration_context_versioned({
        'mirrors': MIRRORS,
        'conversations': CONVERSATIONS
    })

    mocker.patch.object(demisto, 'getIntegrationContextVersioned', return_value=get_integration_context_versioned())
    mocker.patch.object(demisto, 'setIntegrationContextVersioned', side_effecet=set_integration_context_versioned)
    mocker.patch.object(CommonServerPython, 'is_versioned_context_available', return_value=True)

    new_conversation = {
        'id': 'A0123456',
        'name': 'general'
    }

    conversations = json.loads(CONVERSATIONS)
    conversations.extend([new_conversation])

    # Arrange
    context, version = CommonServerPython.update_integration_context({'conversations': conversations}, OBJECTS_TO_KEYS, True)
    new_conversations = json.loads(context['conversations'])

    # Assert
    assert conversations == new_conversations
    assert version == get_integration_context_versioned()['version']


@pytest.mark.parametrize('versioned_available', [True, False])
def test_get_latest_integration_context(mocker, versioned_available):
    import CommonServerPython

    # Set
    set_integration_context_versioned({
        'mirrors': MIRRORS,
        'conversations': CONVERSATIONS
    })

    mocker.patch.object(demisto, 'getIntegrationContextVersioned', return_value=get_integration_context_versioned())
    mocker.patch.object(demisto, 'setIntegrationContextVersioned', side_effecet=set_integration_context_versioned)
    mocker.patch.object(CommonServerPython, 'is_versioned_context_available', return_value=versioned_available)
    mocker.patch.object(demisto, 'getIntegrationContext',
                        return_value={'mirrors': MIRRORS, 'conversations': CONVERSATIONS})

    # Arrange
    context, ver = CommonServerPython.get_integration_context_with_version(True)

    # Assert
    assert context == get_integration_context_versioned()['context']
    assert ver == get_integration_context_versioned()['version'] if versioned_available else -1


def test_set_latest_integration_context(mocker):
    import CommonServerPython

    # Set
    set_integration_context_versioned({
        'mirrors': MIRRORS,
        'conversations': CONVERSATIONS,
    })

    mocker.patch.object(demisto, 'getIntegrationContextVersioned', return_value=get_integration_context_versioned())
    mocker.patch.object(demisto, 'setIntegrationContextVersioned', side_effecet=set_integration_context_versioned)
    int_context = get_integration_context_versioned()
    mocker.patch.object(CommonServerPython, 'update_integration_context',
                        side_effect=[(int_context['context'], int_context['version']),
                                     (int_context['context'], int_context['version'] + 1)])
    mocker.patch.object(CommonServerPython, 'set_integration_context', side_effect=[ValueError, int_context['context']])

    # Arrange
    CommonServerPython.set_to_integration_context_with_retries({}, OBJECTS_TO_KEYS)
    int_context_calls = CommonServerPython.set_integration_context.call_count
    int_context_args_1 = CommonServerPython.set_integration_context.call_args_list[0][0]
    int_context_args_2 = CommonServerPython.set_integration_context.call_args_list[1][0]

    # Assert
    assert int_context_calls == 2
    assert int_context_args_1 == (int_context['context'], True, int_context['version'])
    assert int_context_args_2 == (int_context['context'], True, int_context['version'] + 1)


def test_set_latest_integration_context_es(mocker):
    import CommonServerPython

    # Set
    mocker.patch.object(demisto, 'getIntegrationContextVersioned', return_value=get_integration_context_versioned())
    mocker.patch.object(demisto, 'setIntegrationContextVersioned', side_effecet=set_integration_context_versioned)
    es_inv_context_version_first = {'version': 5, 'sequenceNumber': 807, 'primaryTerm': 1}
    es_inv_context_version_second = {'version': 7, 'sequenceNumber': 831, 'primaryTerm': 1}
    mocker.patch.object(CommonServerPython, 'update_integration_context',
                        side_effect=[({}, es_inv_context_version_first),
                                     ({}, es_inv_context_version_second)])
    mocker.patch.object(CommonServerPython, 'set_integration_context', side_effect=[ValueError, {}])

    # Arrange
    CommonServerPython.set_to_integration_context_with_retries({})
    int_context_calls = CommonServerPython.set_integration_context.call_count
    int_context_args_1 = CommonServerPython.set_integration_context.call_args_list[0][0]
    int_context_args_2 = CommonServerPython.set_integration_context.call_args_list[1][0]

    # Assert
    assert int_context_calls == 2
    assert int_context_args_1[1:] == (True, es_inv_context_version_first)
    assert int_context_args_2[1:] == (True, es_inv_context_version_second)


def test_set_latest_integration_context_fail(mocker):
    import CommonServerPython

    # Set
    set_integration_context_versioned({
        'mirrors': MIRRORS,
        'conversations': CONVERSATIONS,
    })

    mocker.patch.object(demisto, 'getIntegrationContextVersioned', return_value=get_integration_context_versioned())
    mocker.patch.object(demisto, 'setIntegrationContextVersioned', side_effecet=set_integration_context_versioned)
    int_context = get_integration_context_versioned()
    mocker.patch.object(CommonServerPython, 'update_integration_context', return_value=(
        int_context['context'], int_context['version']
    ))
    mocker.patch.object(CommonServerPython, 'set_integration_context', side_effect=ValueError)

    # Arrange
    with pytest.raises(Exception):
        CommonServerPython.set_to_integration_context_with_retries({}, OBJECTS_TO_KEYS)

    int_context_calls = CommonServerPython.set_integration_context.call_count

    # Assert
    assert int_context_calls == CommonServerPython.CONTEXT_UPDATE_RETRY_TIMES


def test_get_x_content_info_headers(mocker):
    test_license = 'TEST_LICENSE_ID'
    test_brand = 'TEST_BRAND'
    mocker.patch.object(
        demisto,
        'getLicenseID',
        return_value=test_license
    )
    mocker.patch.object(
        demisto,
        'callingContext',
        new_callable=mocker.PropertyMock(return_value={'context': {
            'IntegrationBrand': test_brand,
            'IntegrationInstance': 'TEST_INSTANCE',
        }})
    )
    headers = get_x_content_info_headers()
    assert headers['X-Content-LicenseID'] == test_license
    assert headers['X-Content-Name'] == test_brand


def test_return_results_multiple_command_results(mocker):
    """
    Given:
      - List of 2 CommandResult
    When:
      - Calling return_results()
    Then:
      - demisto.results() is called 2 times (with the list items)
    """
    from CommonServerPython import CommandResults, return_results
    demisto_results_mock = mocker.patch.object(demisto, 'results')
    mock_command_results = []
    for i in range(2):
        mock_output = {'MockContext': i}
        mock_command_results.append(CommandResults(outputs_prefix='Mock', outputs=mock_output))
    return_results(mock_command_results)
    assert demisto_results_mock.call_count == 2


def test_return_results_multiple_dict_results(mocker):
    """
    Given:
      - List of 2 dictionaries
    When:
      - Calling return_results()
    Then:
      - demisto.results() is called 1 time (with the list as an argument)
    """
    from CommonServerPython import return_results
    demisto_results_mock = mocker.patch.object(demisto, 'results')
    mock_command_results = [{'MockContext': 0}, {'MockContext': 1}]
    return_results(mock_command_results)
    assert demisto_results_mock.call_count == 1
