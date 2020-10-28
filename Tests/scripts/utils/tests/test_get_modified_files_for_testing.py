import pytest

from Tests.scripts.utils.collect_helpers import COMMON_YML_LIST
from Tests.scripts.utils.get_modified_files_for_testing import get_modified_files_for_testing


def mock_get_dict_from_yaml(mocker, _dict: dict, ext: str):
    mocker.patch('demisto_sdk.commands.common.tools.get_dict_from_file', return_value=(_dict, ext))


class TestGetModifiedFilesForTesting:
    """"
    Given: A git-diff output.

    When: Collecting tests

    Then: Validate the output contains or not the given files
    """

    def test_python_file(self, mocker):
        diff_line = "M       Packs/HelloWorld/Integrations/HelloWorld/HelloWorld.py"
        yml_file = "Packs/HelloWorld/Integrations/HelloWorld/HelloWorld.yml"
        mocker.patch(
            "Tests.scripts.utils.get_modified_files_for_testing.glob.glob",
            return_value=[yml_file],
        )
        mock_get_dict_from_yaml(mocker, {"category": "cat"}, "yml")
        (
            modified_files_list,
            modified_tests_list,
            changed_common,
            is_conf_json,
            sample_tests,
            modified_metadata_list,
            is_reputations_json,
            is_indicator_json,
        ) = get_modified_files_for_testing(diff_line)
        assert modified_files_list == [yml_file]
        assert modified_tests_list == []
        assert changed_common == []
        assert is_conf_json is False
        assert sample_tests == []
        assert modified_metadata_list == set()
        assert is_reputations_json is False
        assert is_indicator_json is False

    def test_yaml_file(self, mocker):
        diff_line = "M      Packs/HelloWorld/Integrations/HelloWorld/HelloWorld.yml"
        mock_get_dict_from_yaml(mocker, {"category": "c"
                                         }, "yml")
        (
            modified_files_list,
            modified_tests_list,
            changed_common,
            is_conf_json,
            sample_tests,
            modified_metadata_list,
            is_reputations_json,
            is_indicator_json,
        ) = get_modified_files_for_testing(diff_line)
        assert modified_files_list == [
            "Packs/HelloWorld/Integrations/HelloWorld/HelloWorld.yml"
        ]
        assert modified_tests_list == []
        assert changed_common == []
        assert is_conf_json is False
        assert sample_tests == []
        assert modified_metadata_list == set()
        assert is_reputations_json is False
        assert is_indicator_json is False

    def test_non_relevant_file(self):
        diff_line = "A       Packs/HelloWorld/Integrations/HelloWorld/cert.pem"
        (
            modified_files_list,
            modified_tests_list,
            changed_common,
            is_conf_json,
            sample_tests,
            modified_metadata_list,
            is_reputations_json,
            is_indicator_json,
        ) = get_modified_files_for_testing(diff_line)
        assert modified_files_list == []
        assert modified_tests_list == []
        assert changed_common == []
        assert is_conf_json is False
        assert sample_tests == []
        assert modified_metadata_list == set()
        assert is_reputations_json is False
        assert is_indicator_json is False

    def test_test_file(self):
        diff_line = (
            "M       Packs/HelloWorld/Integrations/HelloWorld/connection_test.py"
        )
        (
            modified_files_list,
            modified_tests_list,
            changed_common,
            is_conf_json,
            sample_tests,
            modified_metadata_list,
            is_reputations_json,
            is_indicator_json,
        ) = get_modified_files_for_testing(diff_line)
        assert modified_files_list == []
        assert modified_tests_list == []
        assert changed_common == []
        assert is_conf_json is False
        assert sample_tests == []
        assert modified_metadata_list == set()
        assert is_reputations_json is False
        assert is_indicator_json is False

    def test_renamed_file(self, mocker):
        diff_line = (
            "R100	Packs/HelloWorld/Integrations/HelloWorld/HelloWorld.yml	"
            "Packs/NewHelloWorld/Integrations/HelloWorld/NewHelloWorld.yml"
        )
        mock_get_dict_from_yaml(mocker, {"category": "c"
                                         }, "yml")
        (
            modified_files_list,
            modified_tests_list,
            changed_common,
            is_conf_json,
            sample_tests,
            modified_metadata_list,
            is_reputations_json,
            is_indicator_json,
        ) = get_modified_files_for_testing(diff_line)
        assert modified_files_list == ["Packs/NewHelloWorld/Integrations/HelloWorld/NewHelloWorld.yml"]
        assert modified_tests_list == []
        assert changed_common == []
        assert is_conf_json is False
        assert sample_tests == []
        assert modified_metadata_list == set()
        assert is_reputations_json is False
        assert is_indicator_json is False

    def test_test_playbook(self, mocker):
        diff_line = "M Packs/HelloWorld/TestPlaybooks/HelloWorld.yml"
        mock_get_dict_from_yaml(mocker, {"tasks": "c"
                                         }, "yml")
        (
            modified_files_list,
            modified_tests_list,
            changed_common,
            is_conf_json,
            sample_tests,
            modified_metadata_list,
            is_reputations_json,
            is_indicator_json,
        ) = get_modified_files_for_testing(diff_line)
        assert modified_files_list == []
        assert modified_tests_list == ["Packs/HelloWorld/TestPlaybooks/HelloWorld.yml"]
        assert changed_common == []
        assert is_conf_json is False
        assert sample_tests == []
        assert modified_metadata_list == set()
        assert is_reputations_json is False
        assert is_indicator_json is False

    def test_no_file_path(self):
        diff_line = ""
        (
            modified_files_list,
            modified_tests_list,
            changed_common,
            is_conf_json,
            sample_tests,
            modified_metadata_list,
            is_reputations_json,
            is_indicator_json,
        ) = get_modified_files_for_testing(diff_line)
        assert modified_files_list == []
        assert modified_tests_list == []
        assert changed_common == []
        assert is_conf_json is False
        assert sample_tests == []
        assert modified_metadata_list == set()
        assert is_reputations_json is False
        assert is_indicator_json is False

    def test_common_file_list(self, mocker):
        diff_line = f"M    {COMMON_YML_LIST[0]}"
        mock_get_dict_from_yaml(mocker, {"category": "cat"}, "yml")
        (
            modified_files_list,
            modified_tests_list,
            changed_common,
            is_conf_json,
            sample_tests,
            modified_metadata_list,
            is_reputations_json,
            is_indicator_json,
        ) = get_modified_files_for_testing(diff_line)
        assert modified_files_list == []
        assert modified_tests_list == []
        assert changed_common == ["scripts/script-CommonIntegration.yml"]
        assert is_conf_json is False
        assert sample_tests == []
        assert modified_metadata_list == set()
        assert is_reputations_json is False
        assert is_indicator_json is False

    @pytest.mark.parametrize(
        "path",
        (
            "Packs/HelloWorld/IndicatorTypes/reputation-cidr.json",
            "Packs/HelloWorld/IndicatorTypes/reputations.json",
        ),
    )
    def test_reputations_list(self, path: str, mocker):
        diff_line = f"M {path}"
        mock_get_dict_from_yaml(mocker, {"regex": "bla"}, "json")
        (
            modified_files_list,
            modified_tests_list,
            changed_common,
            is_conf_json,
            sample_tests,
            modified_metadata_list,
            is_reputations_json,
            is_indicator_json,
        ) = get_modified_files_for_testing(diff_line)
        assert modified_files_list == []
        assert modified_tests_list == []
        assert changed_common == []
        assert is_conf_json is False
        assert sample_tests == []
        assert modified_metadata_list == set()
        assert is_reputations_json is True
        assert is_indicator_json is False

    def test_conf(self, mocker):
        diff_line = "M Tests/conf.json"
        mock_get_dict_from_yaml(mocker, {}, "json")
        (
            modified_files_list,
            modified_tests_list,
            changed_common,
            is_conf_json,
            sample_tests,
            modified_metadata_list,
            is_reputations_json,
            is_indicator_json,
        ) = get_modified_files_for_testing(diff_line)
        assert modified_files_list == []
        assert modified_tests_list == []
        assert changed_common == []
        assert is_conf_json is True
        assert sample_tests == []
        assert modified_metadata_list == set()
        assert is_reputations_json is False
        assert is_indicator_json is False

    def test_docs(self):
        diff_line = "A Packs/HelloWorld/README.md"
        (
            modified_files_list,
            modified_tests_list,
            changed_common,
            is_conf_json,
            sample_tests,
            modified_metadata_list,
            is_reputations_json,
            is_indicator_json,
        ) = get_modified_files_for_testing(diff_line)
        assert modified_files_list == []
        assert modified_tests_list == []
        assert changed_common == []
        assert is_conf_json is False
        assert sample_tests == []
        assert modified_metadata_list == set()
        assert is_reputations_json is False
        assert is_indicator_json is False

    def test_metadata(self, mocker):
        diff_line = "M Packs/HelloWorld/pack_metadata.json"
        mock_get_dict_from_yaml(mocker, {}, "json")
        (
            modified_files_list,
            modified_tests_list,
            changed_common,
            is_conf_json,
            sample_tests,
            modified_metadata_list,
            is_reputations_json,
            is_indicator_json,
        ) = get_modified_files_for_testing(diff_line)
        assert modified_files_list == []
        assert modified_tests_list == []
        assert changed_common == []
        assert is_conf_json is False
        assert sample_tests == []
        assert modified_metadata_list == {"HelloWorld"}
        assert is_reputations_json is False
        assert is_indicator_json is False

    def test_indicator_fields(self, mocker):
        diff_line = "M Packs/HelloWorld/IndicatorFields/sample-field.json"
        mock_get_dict_from_yaml(mocker, {"id": "indicator-sample-field"}, 'json')
        (
            modified_files_list,
            modified_tests_list,
            changed_common,
            is_conf_json,
            sample_tests,
            modified_metadata_list,
            is_reputations_json,
            is_indicator_json,
        ) = get_modified_files_for_testing(diff_line)
        assert modified_files_list == []
        assert modified_tests_list == []
        assert changed_common == []
        assert is_conf_json is False
        assert sample_tests == []
        assert modified_metadata_list == set()
        assert is_reputations_json is False
        assert is_indicator_json is True

    def test_secrets_whitelist(self, mocker):
        mock_get_dict_from_yaml(mocker, {"files": []}, "json")
        diff_line = "M Tests/secrets_white_list.json"
        (
            modified_files_list,
            modified_tests_list,
            changed_common,
            is_conf_json,
            sample_tests,
            modified_metadata_list,
            is_reputations_json,
            is_indicator_json,
        ) = get_modified_files_for_testing(diff_line)
        assert modified_files_list == []
        assert modified_tests_list == []
        assert changed_common == []
        assert is_conf_json is False
        assert sample_tests == []
        assert modified_metadata_list == set()
        assert is_reputations_json is False
        assert is_indicator_json is False

    @pytest.mark.parametrize("file_path", (
        "Tests/scripts/integration-test.yml",
        "Tests/Util/Scripts/new_script.py"
    ))
    def test_sample(self, file_path):
        diff_line = "M Tests/Util/Scripts/new_script.py"
        py_file = "Tests/Util/Scripts/new_script.py"
        (
            modified_files_list,
            modified_tests_list,
            changed_common,
            is_conf_json,
            sample_tests,
            modified_metadata_list,
            is_reputations_json,
            is_indicator_json,
        ) = get_modified_files_for_testing(diff_line)
        assert modified_files_list == []
        assert modified_tests_list == []
        assert changed_common == []
        assert is_conf_json is False
        assert sample_tests == [py_file]
        assert modified_metadata_list == set()
        assert is_reputations_json is False
        assert is_indicator_json is False

    def test_name_not_same_as_folder(self, mocker):
        diff_line = "M       Packs/HelloWorld/Integrations/HelloWorld/HelloWorld.py"
        yml_file = "Packs/HelloWorld/Integrations/HelloWorld/NewHelloWorld.yml"
        mocker.patch(
            "Tests.scripts.utils.get_modified_files_for_testing.glob.glob",
            return_value=[yml_file],
        )
        mock_get_dict_from_yaml(mocker, {"category": "cat"}, "yml")
        (
            modified_files_list,
            modified_tests_list,
            changed_common,
            is_conf_json,
            sample_tests,
            modified_metadata_list,
            is_reputations_json,
            is_indicator_json,
        ) = get_modified_files_for_testing(diff_line)
        assert modified_files_list == [yml_file]
        assert modified_tests_list == []
        assert changed_common == []
        assert is_conf_json is False
        assert sample_tests == []
        assert modified_metadata_list == set()
        assert is_reputations_json is False
        assert is_indicator_json is False
