import os
from medperf.enums import Status
from medperf.exceptions import MedperfException
import yaml
import logging
from typing import List

import medperf.config as config
from medperf.entities.interface import Entity
from medperf.utils import storage_path
from medperf.exceptions import CommunicationRetrievalError, InvalidArgumentError
from medperf.entities.models import BenchmarkModel


class Benchmark(Entity):
    """
    Class representing a Benchmark

    a benchmark is a bundle of assets that enables quantitative
    measurement of the performance of AI models for a specific
    clinical problem. A Benchmark instance contains information
    regarding how to prepare datasets for execution, as well as
    what models to run and how to evaluate them.
    """

    def __init__(self, bmk_model: BenchmarkModel):
        """Creates a new benchmark instance

        Args:
            bmk_model (BenchmarkModel): Model representation of a Benchmark
        """
        self.model = bmk_model

    @classmethod
    def all(cls) -> List["Benchmark"]:
        """Gets and creates instances of all locally present benchmarks

        Returns:
            List[Benchmark]: a list of Benchmark instances.
        """
        logging.info("Retrieving all benchmarks")
        bmks_storage = storage_path(config.benchmarks_storage)
        try:
            uids = next(os.walk(bmks_storage))[1]
        except StopIteration:
            msg = "Couldn't iterate over benchmarks directory"
            logging.warning(msg)
            raise MedperfException(msg)

        benchmarks = [cls.get(uid) for uid in uids]

        return benchmarks

    @classmethod
    def get(cls, benchmark_uid: str) -> "Benchmark":
        """Retrieves and creates a Benchmark instance from the server.
        If benchmark already exists in the platform then retrieve that
        version.

        Args:
            benchmark_uid (str): UID of the benchmark.
            comms (Comms): Instance of a communication interface.

        Returns:
            Benchmark: a Benchmark instance with the retrieved data.
        """
        comms = config.comms
        # Try to download first
        try:
            benchmark_dict = comms.get_benchmark(benchmark_uid)
            ref_model = benchmark_dict["reference_model_mlcube"]
            add_models = cls.get_models_uids(benchmark_uid)
            benchmark_dict["models"] = [ref_model] + add_models
        except CommunicationRetrievalError:
            # Get local benchmarks
            logging.warning(f"Getting benchmark {benchmark_uid} from comms failed")
            logging.info(f"Looking for benchmark {benchmark_uid} locally")
            bmk_storage = storage_path(config.benchmarks_storage)
            local_bmks = os.listdir(bmk_storage)
            if str(benchmark_uid) in local_bmks:
                benchmark_dict = cls.__get_local_dict(benchmark_uid)
            else:
                raise InvalidArgumentError(
                    "No benchmark with the given uid could be found"
                )
        bmk_model = BenchmarkModel(**benchmark_dict)
        benchmark = cls(bmk_model)
        benchmark.write()
        return benchmark

    @classmethod
    def __get_local_dict(cls, benchmark_uid: str) -> dict:
        """Retrieves a local benchmark information

        Args:
            benchmark_uid (str): uid of the local benchmark

        Returns:
            dict: information of the benchmark
        """
        logging.info(f"Retrieving benchmark {benchmark_uid} from local storage")
        storage = storage_path(config.benchmarks_storage)
        bmk_storage = os.path.join(storage, str(benchmark_uid))
        bmk_file = os.path.join(bmk_storage, config.benchmarks_filename)
        with open(bmk_file, "r") as f:
            data = yaml.safe_load(f)

        return data

    @classmethod
    def tmp(
        cls,
        data_preparator: str,
        model: str,
        evaluator: str,
        demo_url: str = None,
        demo_hash: str = None,
    ) -> "Benchmark":
        """Creates a temporary instance of the benchmark

        Args:
            data_preparator (str): UID of the data preparator cube to use.
            model (str): UID of the model cube to use.
            evaluator (str): UID of the evaluator cube to use.
            demo_url (str, optional): URL to obtain the demo dataset. Defaults to None.
            demo_hash (str, optional): Hash of the demo dataset tarball file. Defaults to None.

        Returns:
            Benchmark: a benchmark instance
        """
        benchmark_uid = f"{config.tmp_prefix}{data_preparator}_{model}_{evaluator}"
        bmk_model = BenchmarkModel(
            id=benchmark_uid,
            name=benchmark_uid,
            data_preparation_mlcube=data_preparator,
            reference_model_mlcube=model,
            data_evaluator_mlcube=evaluator,
            demo_dataset_tarball_url=demo_url,
            demo_dataset_tarball_hash=demo_hash,
            models=[model],
        )
        benchmark = cls(bmk_model)
        benchmark.write()
        return benchmark

    @classmethod
    def get_models_uids(cls, benchmark_uid: str) -> List[str]:
        """Retrieves the list of models associated to the benchmark

        Args:
            benchmark_uid (str): UID of the benchmark.
            comms (Comms): Instance of the communications interface.

        Returns:
            List[str]: List of mlcube uids
        """
        return config.comms.get_benchmark_models(benchmark_uid)

    def todict(self) -> dict:
        """Dictionary representation of the benchmark instance

        Returns:
        dict: Dictionary containing benchmark information
        """
        return self.model.dict()

    def write(self) -> str:
        """Writes the benchmark into disk

        Args:
            filename (str, optional): name of the file. Defaults to config.benchmarks_filename.

        Returns:
            str: path to the created benchmark file
        """
        data = self.todict()
        storage = storage_path(config.benchmarks_storage)
        bmk_path = os.path.join(storage, str(self.model.id))
        if not os.path.exists(bmk_path):
            os.makedirs(bmk_path, exist_ok=True)
        filepath = os.path.join(bmk_path, config.benchmarks_filename)
        with open(filepath, "w") as f:
            yaml.dump(data, f)
        return filepath

    def upload(self):
        """Uploads a benchmark to the server

        Args:
            comms (Comms): communications entity to submit through
        """
        body = self.todict()
        updated_body = config.comms.upload_benchmark(body)
        updated_body["models"] = body["models"]
        return updated_body
