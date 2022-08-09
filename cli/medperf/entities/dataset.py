import os
import yaml
import logging
from typing import List

from medperf.utils import (
    get_uids,
    approval_prompt,
    pretty_error,
    storage_path,
    dict_pretty_print,
)
from medperf.ui.interface import UI
import medperf.config as config
from medperf.comms.interface import Comms


class Dataset:
    """
    Class representing a Dataset

    Datasets are stored locally in the Data Owner's machine. They contain
    information regarding the prepared dataset, such as name and description,
    general statistics and an UID generated by hashing the contents of the
    data preparation output.
    """

    def __init__(self, data_uid: int):
        """Creates a new dataset instance

        Args:
            data_uid (int): The dataset UID as found inside ~/medperf/data/

        Raises:
            NameError: If the dataset with the given UID can't be found, this is thrown.
        """
        data_uid = self.__full_uid(data_uid, config.ui)
        self.data_uid = data_uid
        self.dataset_path = os.path.join(
            storage_path(config.data_storage), str(data_uid)
        )
        self.data_path = os.path.join(self.dataset_path, "data")
        registration = self.get_registration()
        self.uid = registration["uid"]
        self.name = registration["name"]
        self.description = registration["description"]
        self.location = registration["location"]
        self.preparation_cube_uid = registration["data_preparation_mlcube"]
        self.generated_uid = registration["generated_uid"]
        self.input_data_hash = registration["input_data_hash"]
        self.separate_labels = registration.get("separate_labels", False)
        self.split_seed = registration["split_seed"]
        if "metadata" in registration:
            # Make sure it is backwards-compatible
            self.generated_metadata = registration["metadata"]
        else:
            self.generated_metadata = registration["generated_metadata"]
        self.status = registration["status"]
        self.state = registration["state"]

        self.labels_path = self.data_path
        if self.separate_labels:
            self.labels_path = os.path.join(self.dataset_path, "labels")

    @property
    def registration(self):
        return {
            "uid": self.uid,
            "name": self.name,
            "description": self.description,
            "location": self.location,
            "data_preparation_mlcube": self.preparation_cube_uid,
            "input_data_hash": self.input_data_hash,
            "generated_uid": self.generated_uid,
            "split_seed": self.split_seed,
            "generated_metadata": self.generated_metadata,
            "status": self.status,
            "state": self.state,
            "separate_labels": self.separate_labels,
        }

    @classmethod
    def all(cls) -> List["Dataset"]:
        """Gets and creates instances of all the locally prepared datasets

        Returns:
            List[Dataset]: a list of Dataset instances.
        """
        logging.info("Retrieving all datasets")
        data_storage = storage_path(config.data_storage)
        try:
            uids = next(os.walk(data_storage))[1]
        except StopIteration:
            logging.warning("Couldn't iterate over the dataset directory")
            pretty_error("Couldn't iterate over the dataset directory", ui)
        tmp_prefix = config.tmp_prefix
        dsets = []
        for uid in uids:
            not_tmp = not uid.startswith(tmp_prefix)
            reg_path = os.path.join(data_storage, uid, config.reg_file)
            registered = os.path.exists(reg_path)
            if not_tmp and registered:
                dsets.append(cls(uid))
        return dsets

    def __full_uid(self, uid_hint: str, ui: UI) -> str:
        """Returns the found UID that starts with the provided UID hint

        Args:
            uid_hint (int): a small initial portion of an existing local dataset UID

        Raises:
            NameError: If no dataset is found starting with the given hint, this is thrown.
            NameError: If multiple datasets are found starting with the given hint, this is thrown.

        Returns:
            str: the complete UID
        """
        data_storage = storage_path(config.data_storage)
        dsets = get_uids(data_storage)
        match = [uid for uid in dsets if uid.startswith(str(uid_hint))]
        if len(match) == 0:
            pretty_error(f"No dataset was found with uid hint {uid_hint}.", ui)
        elif len(match) > 1:
            pretty_error(f"Multiple datasets were found with uid hint {uid_hint}.", ui)
        else:
            return match[0]

    def get_registration(self) -> dict:
        """Retrieves the registration information.

        Returns:
            dict: registration information as key-value pairs.
        """
        regfile = os.path.join(self.dataset_path, config.reg_file)
        with open(regfile, "r") as f:
            reg = yaml.safe_load(f)
        return reg

    def set_registration(self):
        logging.info(f"Updating registration information for dataset: {self.uid}")
        logging.debug(f"registration information: {self.registration}")
        regfile = os.path.join(self.dataset_path, config.reg_file)
        with open(regfile, "w") as f:
            yaml.dump(self.registration, f)

    def upload(self, comms: Comms):
        """Uploads the registration information to the comms.

        Args:
            comms (Comms): Instance of the comms interface.
        """
        dataset_uid = comms.upload_dataset(self.registration)
        self.uid = dataset_uid
        return self.uid
