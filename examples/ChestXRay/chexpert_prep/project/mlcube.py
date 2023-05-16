"""MLCube handler file"""
import os
import yaml
import typer
import shutil

from preprocess import Preprocessor
from check import Checker
from statistics import Stats

app = typer.Typer()


class PreprocessTask(object):
    """
    Task for preprocessing the data

    Arguments:
    - data_path: data location.
    """

    @staticmethod
    def run(
        data_path: str, labels_path: str, params_file: str, output_path: str
    ) -> None:
        files = next(os.walk(labels_path))[2]
        csvs = [file for file in files if file.endswith(".csv")]
        assert len(csvs) == 1, "Data path must contain only one csv file"
        labels_file = os.path.join(labels_path, csvs[0])
        preprocessor = Preprocessor(data_path, labels_file, params_file, output_path)
        preprocessor.run()


class SanityCheckTask(object):
    """
    Task for checking that the resulting data follows the standard

    Arguments:
    - data_path: data location.
    - params_file: location of parameters.yaml file
    """

    @staticmethod
    def run(data_path: str, params_file: str) -> None:
        with open(params_file, "r") as f:
            params = yaml.full_load(f)

        checker = Checker(data_path, params["output_datafile"])
        checker.run()


class StatisticsTask(object):
    """
    Task for generating and storing statistics about the prepared data

    Arguments:
    - data_path: data location.
    - params_file: location of parameters.yaml file
    """

    @staticmethod
    def run(data_path: str, params_file: str, out_path: str) -> None:
        with open(params_file, "r") as f:
            params = yaml.full_load(f)
        checker = Stats(data_path, out_path, params)
        checker.run()


class CleanupTask(object):
    """
    Task for returning the workspace to its initial state. It removes
    any files created by the cube, as well as the parameters file.

    Args:
    - params_file: yaml file with configuration parameters.
    - output_path: path where the cube's output is stored.
    """

    @staticmethod
    def run(params_file: str, output_path: str) -> None:
        for root, dirs, files in os.walk(output_path):
            for file in files:
                os.remove(os.path.join(root, file))
            for dir in dirs:
                shutil.rmtree(os.path.join(root, dir))
        os.remove(params_file)


@app.command("prepare")
def prepare(
    data_path: str = typer.Option(..., "--data_path"),
    labels_path: str = typer.Option(..., "--labels_path"),
    parameters_file: str = typer.Option(..., "--parameters_file"),
    output_path: str = typer.Option(..., "--output_path"),
):
    PreprocessTask.run(data_path, labels_path, parameters_file, output_path)


@app.command("sanity_check")
def sanity_check(
    data_path: str = typer.Option(..., "--data_path"),
    parameters_file: str = typer.Option(..., "--parameters_file"),
):
    SanityCheckTask.run(data_path, parameters_file)


@app.command("statistics")
def statistics(
    data_path: str = typer.Option(..., "--data_path"),
    parameters_file: str = typer.Option(..., "--parameters_file"),
    out_path: str = typer.Option(..., "--output_path"),
):
    StatisticsTask.run(data_path, parameters_file, out_path)


@app.command("cleanup")
def cleanup(
    parameters_file: str = typer.Option(..., "--parameters_file"),
    output_path: str = typer.Option(..., "--output_path"),
):
    CleanupTask.run(parameters_file, output_path)


if __name__ == "__main__":
    app()
