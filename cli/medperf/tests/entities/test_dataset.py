from medperf.enums import Status
from medperf.tests.mocks.requests import dataset_dict
import pytest
from unittest.mock import MagicMock, mock_open

import medperf.config as config
from medperf.entities.dataset import Dataset


REGISTRATION_MOCK = {
    "name": "name",
    "description": "description",
    "location": "location",
    "data_preparation_mlcube": "data_preparation_mlcube",
    "split_seed": "split_seed",
    "generated_metadata": {"metadata_key": "metadata_value"},
    "generated_uid": "generated_uid",
    "input_data_hash": "input_data_hash",
    "status": Status.PENDING.value,  # not in the server
    "id": "uid",
    "state": "state",
}
REGISTRATION_MOCK = dataset_dict(REGISTRATION_MOCK)

PATCH_DATASET = "medperf.entities.dataset.{}"
TMP_PREFIX = config.tmp_prefix


@pytest.fixture
def basic_arrange(mocker):
    m = mock_open()
    mocker.patch("builtins.open", m, create=True)
    mocker.patch(PATCH_DATASET.format("yaml.safe_load"), return_value=REGISTRATION_MOCK)
    mocker.patch(PATCH_DATASET.format("os.path.exists"), return_value=True)
    return m


@pytest.fixture
def all_uids(mocker, basic_arrange, request):
    uids = request.param
    walk_out = iter([("", uids, [])])

    def mock_reg_file(ff):
        # Extract the uid of the opened registration file through the mocked object
        call_args = basic_arrange.call_args[0]
        # call args returns a tuple with the arguments called. Get the path
        path = call_args[0]
        # Get the uid by extracting second-to-last path element
        uid = path.split("/")[-2]
        # Assign the uid to the mocked registration dictionary
        reg = REGISTRATION_MOCK.copy()
        reg["generated_uid"] = uid
        return reg

    mocker.patch(PATCH_DATASET.format("yaml.safe_load"), side_effect=mock_reg_file)
    mocker.patch(PATCH_DATASET.format("os.walk"), return_value=walk_out)
    return uids


def test_dataset_metadata_is_backwards_compatible(mocker, ui):
    # Arrange
    outdated_reg = REGISTRATION_MOCK.copy()
    del outdated_reg["generated_metadata"]
    outdated_reg["metadata"] = "metaa"

    # Act
    dset = Dataset(outdated_reg)

    # Assert
    assert dset.generated_metadata == outdated_reg["metadata"]


@pytest.mark.parametrize("all_uids", [["1"]], indirect=True)
@pytest.mark.parametrize("filepath", ["filepath"])
def test_write_writes_to_desired_file(mocker, all_uids, filepath):
    # Arrange
    mocker.patch("os.path.join", return_value=filepath)
    open_spy = mocker.patch("builtins.open", MagicMock())
    mocker.patch("yaml.dump", MagicMock())
    mocker.patch("os.makedirs")
    mocker.patch(PATCH_DATASET.format("Dataset.todict"), return_value={})
    dset = Dataset(REGISTRATION_MOCK)
    # Act
    dset.write()

    # Assert
    open_spy.assert_called_once_with(filepath, "w")
