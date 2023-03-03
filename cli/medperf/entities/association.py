import os
import logging
from typing import List

from medperf import config
from medperf.entities.interface import Entity
from medperf.entities.schemas import MedperfSchema, ApprovableSchema
from medperf.exceptions import CommunicationRetrievalError


class Association(Entity, ApprovableSchema):
    """
    Class representing associations

    An association represents an interaction between
    benchmarks and model mlcubes/datasets. An association instance
    can be created by either a benchmark owner or mlcube/dataset owner,
    and must be approved by the opposing party. 
    """

    @classmethod
    def all(
        cls, local_only: bool = False, mine_only: bool = False
    ) -> List["Association"]:
        """Gets and creates instances of all associations
        
        Args:
            local_only (bool, optional): Wether to retrieve only local entities. Defaults to False.
            mine_only (bool, optional): Wether to retrieve only current-user entities. Defaults to False.

        Returns:
            List[Association]: A list of Association instances.
        """
        logging.info("Retrieving all associations")
        associations = []

        if not local_only:
            associations = cls.__remote_all(mine_only=mine_only)

        remote_uids = set([assoc.id for assoc in associations])

        local_associations = cls.__local_all()
        associations += [
            assoc for assoc in local_associations if assoc.id not in remote_uids
        ]

        return associations

    @classmethod
    def __remote_all(cls, mine_only: bool = False) -> List["Association"]:
        associations = []
        if not mine_only:
            raise NotImplementedError(
                "Only current-user remote associations can be retrieved"
            )

        assocs_meta = []
        try:
            assocs_meta += config.comms.get_user_dataset_associations()
            assocs_meta += config.comms.get_user_mlcube_associations()
        except CommunicationRetrievalError:
            msg = "Couldn't retrieve all benchmarks from the server"
            logging.warning(msg)

        associations = [cls(**meta) for meta in assocs_meta]
        return associations

    @classmethod
    def __remote_all(cls) -> List["Association"]:
        # NOOP. We don't store associations locally at the moment
        return []

