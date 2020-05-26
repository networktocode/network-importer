

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

    def start_session(self):
        return self.__sm__()

    # def get(self, session):
    #     return session.query(self.network).get(1)

    def create(self, object_type, params, session=None):

        local_session = False
        if not session:
            session = self.start_session()
            local_session = True

        if not hasattr(self, object_type):
            raise Exception("Unable to find this object type")
        
        if hasattr(self, f"create_{object_type}"):
            item = getattr(self, f"create_{object_type}")(
                params=params,
                session=session
            )
        else:
            # TODO add more checks
            # TODO check of all params are valid
            obj = getattr(self, object_type)
            item = obj(**params)
        
        session.add(item)
        logger.debug(f"Created {object_type} - {params}")

        if local_session:
            session.commit()

        return item

    # def update(self, object_type, params, session=None):

    # def get_devices(self):
    #     session = self.start_session()
    #     return session.query(self.device).all()

