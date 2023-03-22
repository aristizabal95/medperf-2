import os
import yaml
import logging
from pydantic import Field, validator
from typing import List, Optional, Union

from medperf.utils import storage_path
from medperf.enums import Status
from medperf.entities.interface import Entity
from medperf.entities.schemas import MedperfSchema, DeployableSchema
from medperf.exceptions import (
    InvalidArgumentError,
    MedperfException,
    CommunicationRetrievalError,
)
import medperf.config as config


class Dataset(Entity, MedperfSchema, DeployableSchema):
    """
    Class representing a Dataset

    Datasets are stored locally in the Data Owner's machine. They contain
    information regarding the prepared dataset, such as name and description,
    general statistics and an UID generated by hashing the contents of the
    data preparation output.
    """

    description: Optional[str] = Field(None, max_length=20)
    location: str = Field(..., max_length=20)
    data_preparation_mlcube: int
    input_data_hash: str
    generated_uid: str
    split_seed: Optional[int]
    generated_metadata: dict = Field(..., alias="metadata")
    status: Status = None
    separate_labels: Optional[bool]
    user_metadata: dict = {}

    @validator("status", pre=True, always=True)
    def default_status(cls, v, *, values, **kwargs):
        default = Status.PENDING
        if values["id"] is not None:
            default = Status.APPROVED
        if v is None:
            return default
        return Status(v)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        path = storage_path(config.data_storage)
        if self.id:
            path = os.path.join(path, str(self.id))
        else:
            path = os.path.join(path, self.generated_uid)

        self.path = path
        self.data_path = os.path.join(self.path, "data")
        self.labels_path = self.data_path
        if self.separate_labels:
            self.labels_path = os.path.join(self.path, "labels")

    def todict(self):
        return self.extended_dict()

    @classmethod
    def all(
        cls, local_only: bool = False, comms_func: callable = None
    ) -> List["Dataset"]:
        """Gets and creates instances of all the locally prepared datasets

        Args:
            local_only (bool, optional): Wether to retrieve only local entities. Defaults to False.
            comms_func (callable, optional): Function to use to retrieve remote entities. 
                If not provided, will use the default entrypoint.

        Returns:
            List[Dataset]: a list of Dataset instances.
        """
        logging.info("Retrieving all datasets")
        dsets = []
        if not local_only:
            dsets = cls.__remote_all(comms_func=comms_func)

        remote_uids = set([dset.id for dset in dsets])

        local_dsets = cls.__local_all()

        dsets += [dset for dset in local_dsets if dset.id not in remote_uids]

        return dsets

    @classmethod
    def __remote_all(cls, comms_func) -> List["Dataset"]:
        dsets = []
        if comms_func is None:
            comms_func = config.comms.get_datasets

        try:
            dsets_meta = comms_func()
            dsets = [cls(**meta) for meta in dsets_meta]
        except CommunicationRetrievalError:
            msg = "Couldn't retrieve all datasets from the server"
            logging.warning(msg)

        return dsets

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
    def get(cls, dset_uid: Union[str, int]) -> "Dataset":
        """Retrieves and creates a Dataset instance from the comms instance.
        If the dataset is present in the user's machine then it retrieves it from there.

        Args:
            dset_uid (str): server UID of the dataset

        Returns:
            Dataset: Specified Dataset Instance
        """
        logging.debug(f"Retrieving dataset {dset_uid}")
        comms = config.comms

        # Try first downloading the data
        try:
            meta = comms.get_dataset(dset_uid)
            dataset = cls(**meta)
        except CommunicationRetrievalError:
            # Get from local cache
            logging.warning(f"Getting Dataset {dset_uid} from comms failed")
            logging.info(f"Looking for dataset {dset_uid} locally")
            local_meta = cls.__get_local_dict(dset_uid)
            dataset = cls(**local_meta)

        dataset.write()
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
        dataset_dict = self.todict()
        updated_dataset_dict = config.comms.upload_dataset(dataset_dict)
        updated_dataset_dict["status"] = dataset_dict["status"]
        updated_dataset_dict["separate_labels"] = dataset_dict["separate_labels"]
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
            "Status": self.status,
            "State": self.state,
            "Created At": self.created_at,
            "Registered": self.is_registered,
        }
