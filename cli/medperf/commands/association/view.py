from typing import Union

from medperf import config


class ViewAssociation:
    @staticmethod
    def run(
        benchmark_id: Union[int, str],
        mlcube_id: Union[int, str] = None,
        dataset_id: Union[int, str] = None,
        format: str = "yaml",
        output: str = None,
    ):
        """Displays the contents of a single association

		Args:
			benchmark_id (Union[int, str]): Benchmark ID
			mlcube_id (Union[int, str], optional): MLCube ID. Defaults to None.
			dataset_id (Union[int, str], optional): Dataset ID. Defaults to None.
			format (str, optional): What format to use to display the contents. Valid formats: [yaml, json]. Defaults to "yaml".
			output (str, optional): Path to a file for storing the association contents. If not provided, the contents are printed.
		"""
