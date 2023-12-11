import os
import yaml
import logging
from pydantic import Field, validator
from typing import List, Optional, Union

from medperf.utils import storage_path, remove_path
from medperf.entities.interface import Entity, Uploadable
from medperf.entities.schemas import MedperfSchema, DeployableSchema
from medperf.exceptions import (
    InvalidArgumentError,
    MedperfException,
    CommunicationRetrievalError,
)
import medperf.config as config
from medperf.account_management import get_medperf_user_data


class Dataset(Entity, Uploadable, MedperfSchema, DeployableSchema):
    """
    Class representing a Dataset

    Datasets are stored locally in the Data Owner's machine. They contain
    information regarding the prepared dataset, such as name and description,
    general statistics and an UID generated by hashing the contents of the
    data preparation output.
    """

    description: Optional[str] = Field(None, max_length=20)
    location: str = Field(..., max_length=20)
    input_data_hash: str
    generated_uid: str
    data_preparation_mlcube: Union[int, str]
    split_seed: Optional[int]
    generated_metadata: dict = Field(..., alias="metadata")
    user_metadata: dict = {}
    report: dict = {}

    @validator("data_preparation_mlcube", pre=True, always=True)
    def check_data_preparation_mlcube(cls, v, *, values, **kwargs):
        if not isinstance(v, int) and not values["for_test"]:
            raise ValueError(
                "data_preparation_mlcube must be an integer if not running a compatibility test"
            )
        return v

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        path = storage_path(config.data_storage)
        if self.id:
            path = os.path.join(path, str(self.id))
        else:
            path = os.path.join(path, self.generated_uid)

        self.path = path
        self.data_path = os.path.join(self.path, "data")
        self.labels_path = os.path.join(self.path, "labels")
        self.report_path = os.path.join(self.path, config.report_file)
        self.metadata_path = os.path.join(self.path, config.metadata_folder)
        self.statistics_path = os.path.join(self.path, config.statistics_filename)

    def set_raw_paths(self, raw_data_path: str, raw_labels_path: str):
        raw_paths_file = os.path.join(self.path, config.dataset_raw_paths_file)
        data = {"data_path": raw_data_path, "labels_path": raw_labels_path}
        with open(raw_paths_file, "w") as f:
            yaml.dump(data, f)

    def get_raw_paths(self):
        raw_paths_file = os.path.join(self.path, config.dataset_raw_paths_file)
        with open(raw_paths_file) as f:
            data = yaml.safe_load(f)
        return data["data_path"], data["labels_path"]

    def mark_as_ready(self):
        flag_file = os.path.join(self.path, config.ready_flag_file)
        with open(flag_file, "w"):
            pass

    def unmark_as_ready(self):
        flag_file = os.path.join(self.path, config.ready_flag_file)
        remove_path(flag_file)

    def is_ready(self):
        flag_file = os.path.join(self.path, config.ready_flag_file)
        return os.path.exists(flag_file)

    def mark_as_submitted_as_prepared(self):
        flag_file = os.path.join(self.path, config.submitted_as_prepared_flag_file)
        with open(flag_file, "w"):
            pass

    def is_submitted_as_prepared(self):
        flag_file = os.path.join(self.path, config.submitted_as_prepared_flag_file)
        return os.path.exists(flag_file)

    def todict(self):
        return self.extended_dict()

    @classmethod
    def all(cls, local_only: bool = False, filters: dict = {}) -> List["Dataset"]:
        """Gets and creates instances of all the locally prepared datasets

        Args:
            local_only (bool, optional): Wether to retrieve only local entities. Defaults to False.
            filters (dict, optional): key-value pairs specifying filters to apply to the list of entities.

        Returns:
            List[Dataset]: a list of Dataset instances.
        """
        logging.info("Retrieving all datasets")
        dsets = []
        if not local_only:
            dsets = cls.__remote_all(filters=filters)

        remote_uids = set([dset.id for dset in dsets])

        local_dsets = cls.__local_all()

        dsets += [dset for dset in local_dsets if dset.id not in remote_uids]

        return dsets

    @classmethod
    def __remote_all(cls, filters: dict) -> List["Dataset"]:
        dsets = []
        try:
            comms_fn = cls.__remote_prefilter(filters)
            dsets_meta = comms_fn()
            dsets = [cls(**meta) for meta in dsets_meta]
        except CommunicationRetrievalError:
            msg = "Couldn't retrieve all datasets from the server"
            logging.warning(msg)

        return dsets

    @classmethod
    def __remote_prefilter(cls, filters: dict) -> callable:
        """Applies filtering logic that must be done before retrieving remote entities

        Args:
            filters (dict): filters to apply

        Returns:
            callable: A function for retrieving remote entities with the applied prefilters
        """
        comms_fn = config.comms.get_datasets
        if "owner" in filters and filters["owner"] == get_medperf_user_data()["id"]:
            comms_fn = config.comms.get_user_datasets

        if "mlcube" in filters:

            def func():
                return config.comms.get_mlcube_datasets(filters["mlcube"])

            comms_fn = func

        return comms_fn

    @classmethod
    def __local_all(cls) -> List["Dataset"]:
        dsets = []
        data_storage = storage_path(config.data_storage)
        try:
            uids = next(os.walk(data_storage))[1]
        except StopIteration:
            msg = "Couldn't iterate over the dataset directory"
            logging.warning(msg)
            raise MedperfException(msg)

        for uid in uids:
            local_meta = cls.__get_local_dict(uid)
            dset = cls(**local_meta)
            dsets.append(dset)

        return dsets

    @classmethod
    def get(cls, dset_uid: Union[str, int], local_only: bool = False) -> "Dataset":
        """Retrieves and creates a Dataset instance from the comms instance.
        If the dataset is present in the user's machine then it retrieves it from there.

        Args:
            dset_uid (str): server UID of the dataset

        Returns:
            Dataset: Specified Dataset Instance
        """
        if not str(dset_uid).isdigit() or local_only:
            return cls.__local_get(dset_uid)

        try:
            return cls.__remote_get(dset_uid)
        except CommunicationRetrievalError:
            logging.warning(f"Getting Dataset {dset_uid} from comms failed")
            logging.info(f"Looking for dataset {dset_uid} locally")
            return cls.__local_get(dset_uid)

    @classmethod
    def __remote_get(cls, dset_uid: int) -> "Dataset":
        """Retrieves and creates a Dataset instance from the comms instance.
        If the dataset is present in the user's machine then it retrieves it from there.

        Args:
            dset_uid (str): server UID of the dataset

        Returns:
            Dataset: Specified Dataset Instance
        """
        logging.debug(f"Retrieving dataset {dset_uid} remotely")
        meta = config.comms.get_dataset(dset_uid)
        dataset = cls(**meta)
        dataset.write()
        return dataset

    @classmethod
    def __local_get(cls, dset_uid: Union[str, int]) -> "Dataset":
        """Retrieves and creates a Dataset instance from the comms instance.
        If the dataset is present in the user's machine then it retrieves it from there.

        Args:
            dset_uid (str): server UID of the dataset

        Returns:
            Dataset: Specified Dataset Instance
        """
        logging.debug(f"Retrieving dataset {dset_uid} locally")
        local_meta = cls.__get_local_dict(dset_uid)
        dataset = cls(**local_meta)
        return dataset

    def write(self):
        logging.info(f"Updating registration information for dataset: {self.id}")
        logging.debug(f"registration information: {self.todict()}")
        regfile = os.path.join(self.path, config.reg_file)
        os.makedirs(self.path, exist_ok=True)
        with open(regfile, "w") as f:
            yaml.dump(self.todict(), f)
        return regfile

    def upload(self):
        """Uploads the registration information to the comms.

        Args:
            comms (Comms): Instance of the comms interface.
        """
        if self.for_test:
            raise InvalidArgumentError("Cannot upload test datasets.")
        dataset_dict = self.todict()
        updated_dataset_dict = config.comms.upload_dataset(dataset_dict)
        return updated_dataset_dict

    @classmethod
    def __get_local_dict(cls, data_uid):
        dataset_path = os.path.join(storage_path(config.data_storage), str(data_uid))
        regfile = os.path.join(dataset_path, config.reg_file)
        if not os.path.exists(regfile):
            raise InvalidArgumentError(
                "The requested dataset information could not be found locally"
            )
        with open(regfile, "r") as f:
            reg = yaml.safe_load(f)
        return reg

    def display_dict(self):
        return {
            "UID": self.identifier,
            "Name": self.name,
            "Description": self.description,
            "Location": self.location,
            "Data Preparation Cube UID": self.data_preparation_mlcube,
            "Generated Hash": self.generated_uid,
            "State": self.state,
            "Created At": self.created_at,
            "Registered": self.is_registered,
            "Status": "\n".join([f"{k}: {v}" for k, v in self.report.items()]),
        }
