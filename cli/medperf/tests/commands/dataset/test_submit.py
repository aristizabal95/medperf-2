from medperf.exceptions import InvalidArgumentError, CleanExit
import pytest

from medperf.tests.mocks import TestCube
from medperf.tests.mocks.benchmark import TestBenchmark
from medperf.tests.mocks.dataset import TestDataset
from medperf.commands.dataset.submit import DataCreation
from medperf.entities.dataset import Dataset

PATCH_DATAPREP = "medperf.commands.dataset.submit.{}"
OUT_PATH = "out_path"
STATISTICS_PATH = "statistics_path"
OUT_DATAPATH = "out_path/data"
OUT_LABELSPATH = "out_path/labels"
BENCHMARK_UID = "benchmark_uid"
DATA_PATH = "data_path"
LABELS_PATH = "labels_path"
METADATA_PATH = "metadata"
NAME = "name"
DESCRIPTION = "description"
LOCATION = "location"
SUMMARY_PATH = "summary"
REPORT_PATH = "report"
IS_PREPARED = False


@pytest.fixture
def preparation(mocker, comms, ui):
    mocker.patch("os.path.abspath", side_effect=lambda x: x)
    # mocker.patch(
    #     PATCH_DATAPREP.format("generate_tmp_path"), return_value=STATISTICS_PATH
    # )
    mocker.patch(PATCH_DATAPREP.format("Benchmark.get"), return_value=TestBenchmark())
    preparation = DataCreation(
        BENCHMARK_UID,
        None,
        DATA_PATH,
        LABELS_PATH,
        None,
        NAME,
        DESCRIPTION,
        LOCATION,
        False,
        IS_PREPARED,
    )
    mocker.patch(
        PATCH_DATAPREP.format("Cube.get"), return_value=TestCube(is_valid=True)
    )
    preparation.data_path = DATA_PATH
    preparation.labels_path = LABELS_PATH
    preparation.out_datapath = OUT_DATAPATH
    preparation.out_labelspath = OUT_LABELSPATH
    preparation.report_path = REPORT_PATH
    preparation.report_specified = False
    preparation.labels_specified = True
    return preparation


class TestWithDefaultUID:
    @pytest.mark.parametrize("data_exists", [True, False])
    @pytest.mark.parametrize("labels_exist", [True, False])
    def test_validate_fails_when_paths_dont_exist(
        self, mocker, preparation, data_exists, labels_exist
    ):
        # Arrange
        def exists(path):
            if path == DATA_PATH:
                return data_exists
            elif path == LABELS_PATH:
                return labels_exist
            return False

        mocker.patch("os.path.exists", side_effect=exists)
        should_fail = not data_exists or not labels_exist

        # Act & Assert
        if should_fail:
            with pytest.raises(InvalidArgumentError):
                preparation.validate()
        else:
            preparation.validate()

    @pytest.mark.parametrize("cube_uid", [1776, 4342, 573])
    def test_validate_prep_cube_gets_prep_cube_if_provided(
        self, mocker, cube_uid, comms, ui, fs
    ):
        # Arrange
        spy = mocker.patch(
            PATCH_DATAPREP.format("Cube.get"), return_value=TestCube(is_valid=True)
        )

        # Act
        preparation = DataCreation(None, cube_uid, *[""] * 7, False)
        preparation.validate_prep_cube()

        # Assert
        spy.assert_called_once_with(cube_uid)

    @pytest.mark.parametrize("cube_uid", [998, 68, 109])
    def test_validate_prep_cube_gets_benchmark_cube_if_provided(
        self, mocker, cube_uid, comms, ui, fs
    ):
        # Arrange
        benchmark = TestBenchmark(data_preparation_mlcube=cube_uid)
        mocker.patch(PATCH_DATAPREP.format("Benchmark.get"), return_value=benchmark)
        spy = mocker.patch(
            PATCH_DATAPREP.format("Cube.get"), return_value=TestCube(is_valid=True)
        )

        # Act
        preparation = DataCreation(cube_uid, None, *[""] * 7, False)
        preparation.validate_prep_cube()

        # Assert
        spy.assert_called_once_with(cube_uid)

    @pytest.mark.parametrize("benchmark_uid", [None, 1])
    @pytest.mark.parametrize("cube_uid", [None, 1])
    def test_fails_if_invalid_params(self, mocker, benchmark_uid, cube_uid, comms, ui):
        # Arrange
        num_arguments = int(benchmark_uid is None) + int(cube_uid is None)

        # Act
        preparation = DataCreation(benchmark_uid, cube_uid, *[""] * 7, False)
        # Assert

        if num_arguments != 1:
            with pytest.raises(InvalidArgumentError):
                preparation.validate()

        else:
            preparation.validate()

    def test_write_calls_dataset_write(self, mocker, preparation):
        # Arrange
        data_dict = TestDataset().todict()
        spy = mocker.patch(PATCH_DATAPREP.format("Dataset.write"))
        # Act
        preparation.write(data_dict)

        # Assert
        spy.assert_called_once()

    @pytest.mark.parametrize("exists", [True, False])
    @pytest.mark.parametrize("uid", [858, 2770, 2052])
    @pytest.mark.parametrize("old_uid", ["generated_uid", "3749badff"])
    def test_to_permanent_path_renames_folder_correctly(
        self, mocker, preparation, exists, old_uid, uid
    ):
        # Arrange
        old_dset = TestDataset(id=None, generated_uid=old_uid)
        new_dset = TestDataset(id=uid)
        rename_spy = mocker.patch("os.rename")
        cleanup_spy = mocker.patch(PATCH_DATAPREP.format("remove_path"))
        mocker.patch("os.path.exists", return_value=exists)
        preparation.dataset = old_dset
        old_path = Dataset(**old_dset.todict()).path
        new_path = Dataset(**new_dset.todict()).path

        # Act
        preparation.to_permanent_path(new_dset.todict())

        # Assert
        cleanup_spy.assert_called_once_with(new_path)
        rename_spy.assert_called_once_with(old_path, new_path)


@pytest.mark.parametrize("uid", [67342, 236, 1570])
def test_run_returns_generated_uid(mocker, comms, ui, uid):
    # Arrange
    mocker.patch(PATCH_DATAPREP.format("DataCreation.validate"))
    mocker.patch(PATCH_DATAPREP.format("DataCreation.validate_prep_cube"))
    mocker.patch(PATCH_DATAPREP.format("DataCreation.create_dataset_object"))
    mocker.patch(PATCH_DATAPREP.format("DataCreation.upload"), return_value={"id": uid})
    mocker.patch(
        PATCH_DATAPREP.format("DataCreation.to_permanent_path"),
    )
    mocker.patch(
        PATCH_DATAPREP.format("DataCreation.write"),
    )
    mocker.patch(
        PATCH_DATAPREP.format("Cube.get"),
        side_effect=lambda id: TestCube(is_valid=True, id=id),
    )

    # Act
    returned_uid = DataCreation.run("", 1, *[""] * 7, False)

    # Assert
    assert returned_uid == uid


@pytest.mark.parametrize("approved", [True, False])
class TestWithApproval:
    def test_run_uploads_dataset_if_approved(
        self, mocker, comms, ui, preparation, approved
    ):
        # Arrange
        mocker.patch(
            PATCH_DATAPREP.format("approval_prompt"),
            return_value=approved,
        )
        dataset = TestDataset()
        mocker.patch(PATCH_DATAPREP.format("Dataset"), return_value=dataset)
        mocker.patch(PATCH_DATAPREP.format("Dataset.write"))
        spy = mocker.patch.object(dataset, "upload")
        mocker.patch("os.rename")

        # Act
        if approved:
            DataCreation.run("", 1, *[""] * 7, False)

            # Assert
            spy.assert_called_once()
        else:
            with pytest.raises(CleanExit):
                DataCreation.run("", 1, *[""] * 2)

            spy.assert_not_called()

    def test_skips_request_approval_if_preapproved(self, mocker, comms, ui, approved):
        # Arrange
        spy = mocker.patch(
            PATCH_DATAPREP.format("approval_prompt"),
            return_value=True,
        )
        mocker.patch(PATCH_DATAPREP.format("Dataset.write"))
        mocker.patch("os.rename")
        dataset = TestDataset()
        mocker.patch.object(dataset, "set_raw_paths")
        mocker.patch(PATCH_DATAPREP.format("Dataset"), return_value=dataset)
        mocker.patch(
            PATCH_DATAPREP.format("Cube.get"),
            side_effect=lambda id: TestCube(is_valid=True, id=id),
        )

        # Act
        DataCreation.run("", 1, *[""] * 2, approved=approved)

        # Assert
        if approved:
            spy.assert_not_called()
        else:
            spy.assert_called_once()
