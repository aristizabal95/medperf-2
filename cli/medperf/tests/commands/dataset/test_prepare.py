from medperf.exceptions import InvalidArgumentError
import pytest

from medperf.tests.mocks.dataset import TestDataset
from medperf.tests.mocks.cube import TestCube
from medperf.commands.dataset.prepare import DataPreparation

PATCH_REGISTER = "medperf.commands.dataset.prepare.{}"


# def test_run_cube_tasks_runs_required_tasks(self, mocker, preparation):
#     # Arrange
#     spy = mocker.patch.object(preparation.cube, "run")

#     prepare = call(
#         task="prepare",
#         timeout=None,
#         data_path=DATA_PATH,
#         labels_path=LABELS_PATH,
#         output_path=OUT_DATAPATH,
#         output_labels_path=OUT_LABELSPATH,
#     )
#     check = call(
#         task="sanity_check",
#         timeout=None,
#         data_path=OUT_DATAPATH,
#         labels_path=OUT_LABELSPATH,
#     )
#     stats = call(
#         task="statistics",
#         timeout=None,
#         data_path=OUT_DATAPATH,
#         labels_path=OUT_LABELSPATH,
#         output_path=STATISTICS_PATH,
#     )
#     calls = [prepare, check, stats]

#     # Act
#     preparation.run_prepare()
#     preparation.run_sanity_check()
#     preparation.run_statistics()

#     # Assert
#     spy.assert_has_calls(calls)

# def test_run_executes_expected_flow(self, mocker, comms, ui, fs):
#     # Arrange
#     validate_spy = mocker.patch(PATCH_DATAPREP.format("DataPreparation.validate"))
#     get_cube_spy = mocker.spy(DataPreparation, "validate_prep_cube")
#     mocker.patch(
#         PATCH_DATAPREP.format("Cube.get"),
#         side_effect=lambda id: TestCube(is_valid=True, id=id),
#     )
#     run_prepare_spy = mocker.patch(
#         PATCH_DATAPREP.format("DataPreparation.run_prepare")
#     )
#     run_sanity_check_spy = mocker.patch(
#         PATCH_DATAPREP.format("DataPreparation.run_sanity_check")
#     )
#     run_statistics_spy = mocker.patch(
#         PATCH_DATAPREP.format("DataPreparation.run_statistics")
#     )
#     get_stat_spy = mocker.patch(
#         PATCH_DATAPREP.format("DataPreparation.get_statistics"),
#     )
#     generate_uids_spy = mocker.patch(
#         PATCH_DATAPREP.format("DataPreparation.generate_uids"),
#     )
#     to_permanent_path_spy = mocker.patch(
#         PATCH_DATAPREP.format("DataPreparation.to_permanent_path"),
#     )
#     write_spy = mocker.patch(
#         PATCH_DATAPREP.format("DataPreparation.write"),
#     )

#     # Act
#     DataPreparation.run("", "", "", "")

#     # Assert
#     validate_spy.assert_called_once()
#     get_cube_spy.assert_called_once()
#     run_prepare_spy.assert_called_once()
#     run_sanity_check_spy.assert_called_once()
#     run_statistics_spy.assert_called_once()
#     get_stat_spy.assert_called_once()
#     generate_uids_spy.assert_called_once()
#     to_permanent_path_spy.assert_called_once()
#     write_spy.assert_called_once()


@pytest.fixture
def dataset(mocker, ):
    dset = TestDataset(id=None, generated_uid="generated_uid", state="DEVELOPMENT")
    mocker.patch(PATCH_REGISTER.format("Dataset.get"), return_value=dset)
    mocker.patch(PATCH_REGISTER.format("Dataset.upload"), return_value=dset.todict())
    mocker.patch.object(
        dset, "get_raw_paths", return_value=("raw/data/path", "/raw/labels/path")
    )
    mocker.patch.object(dset, "mark_as_ready")
    return dset


@pytest.fixture
def cube(mocker):
    mCube = mocker.create_autospec(TestCube)
    cube = mCube(is_valid=True)
    mocker.patch(PATCH_REGISTER.format("Cube.get"), return_value=cube)
    return cube


@pytest.fixture
def no_remote(mocker, comms):
    mocker.patch.object(comms, "get_user_datasets", return_value=[])


@pytest.mark.parametrize("data_uid", [287, 49, 1793])
def test_run_retrieves_specified_dataset(
    mocker, comms, ui, dataset, cube, data_uid, no_remote
):
    # Arrange
    mocker.patch(PATCH_REGISTER.format("ReportSender.start"))
    mocker.patch(PATCH_REGISTER.format("ReportSender.stop"))
    mocker.patch(
        PATCH_REGISTER.format("approval_prompt"),
        return_value=True,
    )
    mocker.patch(PATCH_REGISTER.format("Cube"), side_effect=lambda x: TestCube(id=x))
    spy = mocker.patch(PATCH_REGISTER.format("Dataset.get"), return_value=dataset)
    mocker.patch(PATCH_REGISTER.format("Dataset.write"))
    mocker.patch("os.rename")

    # Act
    DataPreparation.run(data_uid)

    # Assert
    spy.assert_called_once_with(data_uid)


@pytest.mark.parametrize("uid", [3720, 1465, 4033])
def test_run_fails_if_dataset_already_in_operation(
    mocker, comms, ui, dataset, cube, uid, no_remote
):
    # Arrange
    dataset.id = uid
    dataset.state = "OPERATION"

    # Act & Assert
    with pytest.raises(InvalidArgumentError):
        DataPreparation.run(uid)


@pytest.mark.parametrize("submitted_as_prepared", [False, True])
@pytest.mark.parametrize("is_ready", [False, True])
def test_run_executes_prepare_when_needed(
    mocker, comms, ui, dataset, cube, no_remote, submitted_as_prepared, is_ready
):
    # Arrange
    spy = mocker.patch(PATCH_REGISTER.format("DataPreparation.run_prepare"))
    mocker.patch(
        PATCH_REGISTER.format("approval_prompt"),
        return_value=True,
    )
    mocker.patch(PATCH_REGISTER.format("Dataset.write"))
    mocker.patch("os.rename")
    mocker.patch.object(dataset, "is_ready", return_value=is_ready)
    dataset.submitted_as_prepared = submitted_as_prepared

    # Act
    DataPreparation.run(1)

    # Assert
    should_run = not submitted_as_prepared and not is_ready
    if should_run:
        spy.assert_called_once()
    else:
        spy.assert_not_called()


@pytest.mark.parametrize("submitted_as_prepared", [False, True])
@pytest.mark.parametrize("is_ready", [False, True])
@pytest.mark.parametrize("approve_sending_reports", [False, True])
@pytest.mark.parametrize("for_test", [False, True])
@pytest.mark.parametrize("report_specified", [False, True])
def test_run_prompts_for_report_when_needed(
    mocker,
    comms,
    ui,
    dataset,
    cube,
    no_remote,
    submitted_as_prepared,
    is_ready,
    approve_sending_reports,
    for_test,
    report_specified,
):
    # Arrange
    mocker.patch(PATCH_REGISTER.format("ReportSender.start"))
    mocker.patch(PATCH_REGISTER.format("ReportSender.stop"))
    spy = mocker.patch(PATCH_REGISTER.format("dict_pretty_print"))
    mocker.patch(
        PATCH_REGISTER.format("approval_prompt"),
        return_value=True,
    )
    mocker.patch(PATCH_REGISTER.format("Dataset.write"))
    mocker.patch("os.rename")
    mocker.patch.object(dataset, "is_ready", return_value=is_ready)
    dataset.submitted_as_prepared = submitted_as_prepared
    dataset.for_test = for_test
    mocker.patch.object(
        cube, "get_default_output", return_value="path" if report_specified else None
    )
    should_run = (
        not submitted_as_prepared
        and not is_ready
        and not approve_sending_reports
        and not for_test
        and report_specified
    )

    # Act
    DataPreparation.run(1, approve_sending_reports=approve_sending_reports)

    # Assert
    if should_run:
        spy.assert_called_once()
    else:
        spy.assert_not_called()
