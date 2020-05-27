

import logging
from os import path

from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

from .models import *

logger = logging.getLogger("network-importer")

class NetMod:

    site = Site
    device = Device
    interface = Interface
    ip_address = IPAddress
    cable = Cable

    diffs = ["sites", "devices"]

    def __init__(self):

        self.engine = create_engine(f"sqlite:///:memory:")
        Base.metadata.bind = self.engine
        Base.metadata.create_all(self.engine)
        self.__sm__ = sessionmaker(bind=self.engine)

    def init(self):
        raise NotImplementedError

    def start_session(self):
        return self.__sm__()

    def create(self, object_type, keys, params, session=None):

        self._crud_change(
            action="create",
            keys=keys,
            object_type=object_type,
            params=params,
            session=session
        )

    def update(self, object_type, keys, params, session=None):
        self._crud_change(
            action="update",
            object_type=object_type,
            keys=keys,
            params=params,
            session=session
        )

    def delete(self, object_type, keys, params, session=None):
        self._crud_change(
            action="delete",
            object_type=object_type,
            keys=keys,
            params=params,
            session=session
        )

    def _crud_change(self, action, object_type, keys, params, session=None):
        local_session = False
        if not session:
            session = self.start_session()
            local_session = True

        if not hasattr(self, object_type):
            raise Exception("Unable to find this object type")

        # Check if a specific crud function is available
        #   update_interface or create_device etc ...
        # If not apply the default one
        if hasattr(self, f"{action}_{object_type}"):
            item = getattr(self, f"{action}_{object_type}")(
                keys=keys,
                params=params,
                session=session
            )
            logger.debug(f"{action}d {object_type} - {params}")
        else:
            item = getattr(self, f"default_{action}")(
                object_type=object_type,
                keys=keys,
                params=params,
                session=session
            )
            logger.debug(f"{action}d {object_type} = {keys} - {params} (default)")

        if local_session:
            session.commit()

        return item

    def default_create(self, object_type, keys, params, session):
        """ """
        obj = getattr(self, object_type)
        item = obj(**keys, **params)
        session.add(item)
        return item

    def default_update(self, object_type, keys, params, session):
        obj = getattr(self, object_type)
        item = session.query(obj).get(**keys)
        item.update(**params)
        return item

    def default_delete(self, object_type, keys, params, session):
        obj = getattr(self, object_type)
        item = session.query(obj).get(**keys)
        session.delete(item)
        return item
