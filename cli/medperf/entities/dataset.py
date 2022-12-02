import os
from medperf.enums import Status
import yaml
import logging
from typing import List

from medperf.utils import storage_path
from medperf.entities.interface import Entity
from medperf.exceptions import InvalidArgumentError, MedperfException, CommunicationRetrievalError
import medperf.config as config


class Dataset(Entity):
    """
    Class representing a Dataset

    Datasets are stored locally in the Data Owner's machine. They contain
    information regarding the prepared dataset, such as name and description,
    general statistics and an UID generated by hashing the contents of the
    data preparation output.
    """

    def __init__(self, dataset_dict: dict):
        """Creates a new dataset instance

        Args:
            data_uid (int): The dataset UID as found inside ~/medperf/data/

        Raises:
            NameError: If the dataset with the given UID can't be found, this is thrown.
        """

        self.generated_uid = dataset_dict["generated_uid"]
        self.name = dataset_dict["name"]
        self.description = dataset_dict["description"]
        self.location = dataset_dict["location"]
        self.preparation_cube_uid = dataset_dict["data_preparation_mlcube"]
        self.input_data_hash = dataset_dict["input_data_hash"]
        self.separate_labels = dataset_dict.get(
            "separate_labels", None
        )  # not in the server
        self.split_seed = dataset_dict["split_seed"]
        if "metadata" in dataset_dict:
            # Make sure it is backwards-compatible
            self.generated_metadata = dataset_dict["metadata"]
        else:
            self.generated_metadata = dataset_dict["generated_metadata"]
        if "status" in dataset_dict:
            self.status = Status(dataset_dict["status"])  # not in the server
        else:
            self.status = (
                Status.PENDING if dataset_dict["id"] is None else Status.APPROVED
            )
        self.state = dataset_dict["state"]
        self.is_valid = dataset_dict["is_valid"]
        self.user_metadata = dataset_dict["user_metadata"]

        self.uid = dataset_dict["id"]
        self.created_at = dataset_dict["created_at"]
        self.modified_at = dataset_dict["modified_at"]
        self.owner = dataset_dict["owner"]

        path = storage_path(config.data_storage)
        if self.uid:
            path = os.path.join(path, str(self.uid))
        else:
            path = os.path.join(path, str(self.generated_uid))

        self.path = path
        self.data_path = os.path.join(self.path, "data")
        self.labels_path = self.data_path
        if self.separate_labels:
            self.labels_path = os.path.join(self.path, "labels")

    def todict(self):
        return {
            "id": self.uid,
            "name": self.name,
            "description": self.description,
            "location": self.location,
            "data_preparation_mlcube": self.preparation_cube_uid,
            "input_data_hash": self.input_data_hash,
            "generated_uid": self.generated_uid,
            "split_seed": self.split_seed,
            "generated_metadata": self.generated_metadata,
            "status": self.status.value,  # not in the server
            "state": self.state,
            "separate_labels": self.separate_labels,  # not in the server
            "is_valid": self.is_valid,
            "user_metadata": self.user_metadata,
            "created_at": self.created_at,
            "modified_at": self.modified_at,
            "owner": self.owner,
        }

    @classmethod
    def all(cls, local_only: bool = False, mine_only: bool = False) -> List["Dataset"]:
        """Gets and creates instances of all the locally prepared datasets

        Args:
            local_only (bool, optional): Wether to retrieve only local entities. Defaults to False.
            mine_only (bool, optional): Wether to retrieve only current-user entities. Defaults to False.

        Returns:
            List[Dataset]: a list of Dataset instances.
        """
        logging.info("Retrieving all datasets")
        dsets = []
        if not local_only:
            dsets = cls.__remote_all(mine_only=mine_only)

        remote_uids = set([dset.uid for dset in dsets])

        local_dsets = cls.__local_all()

        dsets += [dset for dset in local_dsets if dset.uid not in remote_uids]

        return dsets

    @classmethod
    def __remote_all(cls, mine_only: bool = False) -> List["Dataset"]:
        dsets = []
        remote_func = config.comms.get_datasets
        if mine_only:
            remote_func = config.comms.get_user_datasets

        try:
            dsets_meta = remote_func()
            dsets = [cls(meta) for meta in dsets_meta]
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
            dset = cls(local_meta)
            dsets.append(dset)

        return dsets

    @classmethod
    def get(cls, dset_uid: str) -> "Dataset":
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
            dataset = cls(meta)
        except CommunicationRetrievalError:
            # Get from local cache
            logging.warning(f"Getting Dataset {dset_uid} from comms failed")
            logging.info(f"Looking for dataset {dset_uid} locally")
            local_meta = cls.__get_local_dict(dset_uid)
            dataset = cls(local_meta)

        dataset.write()
        return dataset

    def write(self):
        logging.info(f"Updating registration information for dataset: {self.uid}")
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
    def __get_local_dict(cls, generated_uid):
        dataset_path = os.path.join(
            storage_path(config.data_storage), str(generated_uid)
        )
        regfile = os.path.join(dataset_path, config.reg_file)
        if not os.path.exists(regfile):
            raise InvalidArgumentError(
                "The requested dataset information could not be found locally"
            )
        with open(regfile, "r") as f:
            reg = yaml.safe_load(f)
        return reg
