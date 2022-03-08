import os
import yaml
import logging
from time import time
from typing import List

from medperf.ui.interface import UI
import medperf.config as config
from medperf.comms.interface import Comms
from medperf.entities.result import Result
from medperf.entities.dataset import Dataset
from medperf.entities.benchmark import Benchmark
from medperf.commands.dataset.create import DataPreparation
from medperf.utils import pretty_error, untar, get_file_sha1
from medperf.commands.result.create import BenchmarkExecution


class CompatibilityTestExecution:
    @classmethod
    def run(
        cls,
        benchmark_uid: int,
        comms: Comms,
        ui: UI,
        data_uid: str = None,
        data_prep: str = None,
        model: str = None,
        evaluator: str = None,
    ) -> List:
        """Execute a test workflow for a specific benchmark

        Args:
            benchmark_uid (int): Benchmark to run the test workflow for
            data_uid (str, optional): registered dataset uid. 
                If none provided, it defaults to benchmark test dataset.
            data_prep (str, optional): data prep mlcube uid or local path. 
                If none provided, it defaults to benchmark data prep mlcube.
            model (str, optional): model mlcube uid or local path. 
                If none provided, it defaults to benchmark reference model.
            evaluator (str, optional): evaluator mlcube uid or local path.
                If none provided, it defaults to benchmark evaluator mlcube.
        Returns:
            (str): Benchmark UID used for the test. Could be the one provided or a generated one.
            (str): Dataset UID used for the test. Could be the one provided or a generated one.
            (str): Model UID used for the test. Could be the one provided or a generated one.
            (Result): Results generated by the test.
        """
        logging.info("Starting test execution")
        test_exec = cls(benchmark_uid, data_uid, data_prep, model, evaluator, comms, ui)
        test_exec.validate()
        test_exec.prepare_test()
        test_exec.set_data_uid()
        result = test_exec.execute_benchmark()
        return test_exec.benchmark_uid, test_exec.data_uid, test_exec.model, result

    def __init__(
        self,
        benchmark_uid: int,
        data_uid: str,
        data_prep: str,
        model: str,
        evaluator: str,
        comms: Comms,
        ui: UI,
    ):
        self.benchmark_uid = benchmark_uid
        self.benchmark = None
        self.data_uid = data_uid
        self.data_prep = data_prep
        self.model = model
        self.evaluator = evaluator
        self.comms = comms
        self.ui = ui

    def validate(self):
        """Ensures test has been passed a valid combination of parameters.
        Specifically, a benchmark must be passed if any other workflow 
        parameter is not passed.
        """
        params = [self.data_uid, self.data_prep, self.model, self.evaluator]
        none_params = [param is None for param in params]
        if self.benchmark_uid is None and any(none_params):
            pretty_error(
                "Invalid combination of arguments to test. Ensure you pass a benchmark or a complete mlcube flow",
                self.ui,
            )

    def prepare_test(self):
        """Prepares all parameters so a test can be executed. Paths to cubes are
        transformed to cube uids and benchmark is mocked/obtained.
        """
        if self.benchmark_uid:
            self.benchmark = Benchmark.get(self.benchmark_uid, self.comms)
            self.set_cube_uid("data_prep", self.benchmark.data_preparation)
            self.set_cube_uid("model", self.benchmark.reference_model)
            self.set_cube_uid("evaluator", self.benchmark.evaluator)
        else:
            self.set_cube_uid("data_prep")
            self.set_cube_uid("model")
            self.set_cube_uid("evaluator")
            self.benchmark = Benchmark.tmp(self.data_prep, self.model, self.evaluator)
            self.benchmark_uid = self.benchmark.uid

    def execute_benchmark(self):
        """Runs the benchmark execution flow given the specified testing parameters
        """
        BenchmarkExecution.run(
            self.benchmark_uid,
            self.data_uid,
            self.model,
            self.comms,
            self.ui,
            run_test=True,
        )
        return Result(self.benchmark_uid, self.data_uid, self.model)

    def set_cube_uid(self, attr: str, fallback: any = None):
        """Assigns the attr used for testing according to the initialization parameters.
        If the value is a path, it will create a temporary uid and link the cube path to
        the medperf storage path.
        
        Arguments:
            attr (str): Attribute to check and/or reassign.
            fallback (any): Value to assign if attribute is empty. Defaults to None.
        """
        logging.info("Establishing model_uid for test execution")
        val = getattr(self, attr)
        if val is None:
            logging.info(f"Empty attribute: {attr}. Assigning fallback: {fallback}")
            setattr(self, attr, fallback)
            return

        # Check if value is a server UID
        if os.path.exists(val):
            logging.info("local path provided. Creating symbolic link")
            self.cube_uid = config.test_cube_prefix + str(int(time()))
            dst = os.path.join(config.cubes_storage, self.cube_uid)
            os.symlink(val, dst)
            logging.info(f"local cube will linked to path: {dst}")

    def set_data_uid(self):
        """Assigns the data_uid used for testing according to the initialization parameters.
        If no data_uid is provided, it will retrieve the demo data and execute the data 
        preparation flow.
        """
        logging.info("Establishing data_uid for test execution")
        if self.data_uid is None:
            logging.info("Data uid not provided. Using benchmark demo dataset")
            data_path, labels_path = self.download_demo_data()
            self.data_uid = DataPreparation.run(
                self.benchmark_uid,
                data_path,
                labels_path,
                self.comms,
                self.ui,
                run_test=True,
            )
            # Dataset will not be registered, so we must mock its uid
            logging.info("Defining local data uid")
            dset = Dataset(self.data_uid, self.ui)
            dset.uid = self.data_uid
            dset.set_registration()

    def download_demo_data(self):
        """Retrieves the demo dataset associated to the specified benchmark

        Returns:
            data_path (str): Location of the downloaded data
            labels_path (str): Location of the downloaded labels
        """
        dset_url = self.benchmark.demo_dataset_url
        dset_hash = self.benchmark.demo_dataset_hash
        file_path = self.comms.get_benchmark_demo_dataset(dset_url, dset_hash)

        # Check demo dataset integrity
        file_hash = get_file_sha1(file_path)
        # Alllow for empty datset hashes for benchmark registration purposes
        if dset_hash and file_hash != dset_hash:
            pretty_error("Demo dataset hash doesn't match expected hash", self.ui)

        untar_path = untar(file_path, remove=False)

        # It is assumed that all demo datasets contain a file
        # which specifies the input of the data preparation step
        paths_file = os.path.join(untar_path, config.demo_dset_paths_file)
        with open(paths_file, "r") as f:
            paths = yaml.safe_load(f)

        data_path = os.path.join(untar_path, paths["data_path"])
        labels_path = os.path.join(untar_path, paths["labels_path"])
        return data_path, labels_path
