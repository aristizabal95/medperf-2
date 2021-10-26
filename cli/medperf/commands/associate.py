import typer

from medperf.entities import Server, Dataset, Benchmark
from medperf.utils import pretty_error
from medperf.config import config


class DatasetBenchmarkAssociation:
    @staticmethod
    def run(data_uid: int, benchmark_uid: int):
        """Associates a registered dataset with a benchmark

        Args:
            data_uid (int): UID of the registered dataset to associate
            benchmark_uid (int): UID of the benchmark to associate with
        """
        server = Server(config["server"])
        server.login("testdataowner", "test")
        dset = Dataset(data_uid)
        benchmark = Benchmark.get(benchmark_uid, server)

        if dset.preparation_cube_uid != benchmark.data_preparation:
            pretty_error("The specified dataset wasn't prepared for this benchmark")
        approval = dset.request_association_approval(benchmark)

        if approval:
            typer.echo("Generating dataset benchmark association")
            server.associate_dset_benchmark(data_uid, benchmark_uid)