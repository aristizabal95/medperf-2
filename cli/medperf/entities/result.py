import yaml
import typer

from medperf.utils import approval_prompt, dict_pretty_print
from medperf.config import config
from medperf.entities import Server


class Result:
    def __init__(
        self, result_path: str, benchmark_uid: int, dataset_uid: int, model_uid: int
    ):
        """Creates a new result instance

        Args:
            result_path (str): Location of the reuslts.yaml file.
            benchmark_uid (str): UID of the executed benchmark.
            dataset_uid (str): UID of the dataset used.
            model_uid (str): UID of the model used.
        """
        self.path = result_path
        self.benchmark_uid = benchmark_uid
        self.dataset_uid = dataset_uid
        self.model_uid = model_uid
        self.status = "PENDING"

    def todict(self):
        with open(self.path, "r") as f:
            results = yaml.full_load(f)

        result_dict = {
            "name": f"{self.benchmark_uid}_{self.model_uid}_{self.dataset_uid}",
            "results": results,
            "metadata": {},
            "approval_status": self.status,
            "benchmark": self.benchmark_uid,
            "model": self.model_uid,
            "dataset": self.dataset_uid,
        }
        return result_dict

    def request_approval(self) -> bool:
        """Prompts the user for approval concerning uploading the results to the server

        Returns:
            bool: Wether the user gave consent or not
        """
        if self.status == "APPROVED":
            return True

        dict_pretty_print(self.todict())
        typer.echo("Above are the results generated by the model")

        approved = approval_prompt(
            "Do you approve uploading the presented results to the MLCommons server? [Y/n]"
        )

        return approved

    def upload(self, server: Server):
        """Uploads the results to the server

        Args:
            server (Server): Instance of the server interface.
        """
        server.upload_results(self.todict())