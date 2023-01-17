from typing import List
from medperf.enums import Status
from medperf.entities.benchmark import Benchmark


class TestBenchmark(Benchmark):
    id: int = 1
    name: str = "name"
    demo_dataset_tarball_hash: str = "tarball_hash"
    data_preparation_mlcube: int = 1
    reference_model_mlcube: int = 2
    data_evaluator_mlcube: int = 3
    models: List[int] = [2]
    approval_status: Status = Status.APPROVED
