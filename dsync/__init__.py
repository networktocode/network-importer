"""
(c) 2020 Network To Code

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at
  http://www.apache.org/licenses/LICENSE-2.0
Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
import logging
from os import path

from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

from .diff import Diff

logger = logging.getLogger("network-importer")


def intersection(lst1, lst2):
    lst3 = [value for value in lst1 if value in lst2]
    return lst3


class DSyncMixin:
    def __iter__(self):
        for v in self.values:
            yield v, getattr(self, v)

    def get_type(self):
        return self.__tablename__

    def get_keys(self):
        return {pk.name: getattr(self, pk.name) for pk in self.__table__.primary_key}

    def get_attrs(self):
        return {attr: getattr(self, attr) for attr in self.attributes}


class DSync:

    # site = Site
    # device = Device
    # interface = Interface
    # ip_address = IPAddress
    # cable = Cable

    # top_level = ["device", "cable"]

    def __init__(self, db="sqlite:///:memory:"):

        self.engine = create_engine(db)
        Base.metadata.bind = self.engine
        Base.metadata.create_all(self.engine)
        self.__sm__ = sessionmaker(bind=self.engine)

    def init(self):
        raise NotImplementedError

    def clean(self):
        pass

    def start_session(self):
        return self.__sm__()

    def sync(self, source):
        """Syncronize the current NetMod object with the source

        Args:
            source: NetMod object to sync with this one
        """
        source_session = source.start_session()
        local_session = self.start_session()

        for obj in intersection(self.top_level, source.top_level):
            self.sync_objects(
                source=source_session.query(getattr(source, obj)).all(),
                dest=local_session.query(getattr(source, obj)).all(),
                session=local_session,
            )

        logger.info("Saving Changes")
        source_session.commit()

    def sync_objects(self, source, dest, session):
        """

        Args:
            source: NetMod object to sync with this one
        """

        if type(source) != type(dest):
            logger.warning(f"Attribute {source} are of different types")
            return False

        if isinstance(source, list):
            dict_src = {str(item): item for item in source}
            dict_dst = {str(item): item for item in dest}

            same_keys = intersection(dict_src.keys(), dict_dst.keys())

            diff1 = list(set(dict_src.keys()) - set(same_keys))
            diff2 = list(set(dict_dst.keys()) - set(same_keys))

            for i in diff1:
                logger.info(f"{i} is missing, need to Add it")
                # import pdb;pdb.set_trace()
                self.create_object(
                    object_type=dict_src[i].get_type(),
                    keys=dict_src[i].get_keys(),
                    params=dict_src[i].get_attrs(),
                    session=session,
                )
                # TODO Continue the tree here

            for i in diff2:
                logger.info(f"{i} is missing in Source, need to Delete")
                self.delete_object(
                    object_type=dict_dst[i].get_type(),
                    keys=dict_dst[i].get_keys(),
                    params=dict_dst[i].get_attrs(),
                    session=session,
                )

            # logger.debug(f"Same Keys: {same_keys}")
            for i in same_keys:
                if dict_src[i].get_attrs() != dict_dst[i].get_attrs():
                    logger.info(
                        f"{dict_src[i].get_type()} {dict_dst[i]} | SRC and DST are not in sync, updating"
                    )
                    self.update_object(
                        object_type=dict_src[i].get_type(),
                        keys=dict_dst[i].get_keys(),
                        params=dict_src[i].get_attrs(),
                        session=session,
                    )

                logger.debug(
                    f"{dict_src[i].get_type()} {dict_dst[i]} | following the path for {dict_src[i].childs}"
                )
                for child in dict_src[i].childs:
                    self.sync_objects(
                        session=session,
                        source=getattr(dict_src[i], child),
                        dest=getattr(dict_dst[i], child),
                    )

        else:
            print(f"Type {type(source)} is not supported for now")

        return True

    def print_diff(self, source):

        diff = self.diff(source)
        for key, items in diff.items():
            print(key.upper())
            for item in items:
                if item.has_diffs():
                    item.print_detailed()

    def diff(self, source):
        source_session = source.start_session()
        local_session = self.start_session()
        diffs = {}
        for obj in intersection(self.top_level, source.top_level):

            diffs[obj] = self.diff_objects(
                source=source_session.query(getattr(source, obj)).all(),
                dest=local_session.query(getattr(source, obj)).all(),
                session=local_session,
            )

        return diffs

    def diff_objects(self, source, dest, session):
        """ """
        if type(source) != type(dest):
            logger.warning(f"Attribute {source} are of different types")
            return False

        diffs = []

        if isinstance(source, list):
            dict_src = {str(item): item for item in source}
            dict_dst = {str(item): item for item in dest}

            same_keys = intersection(dict_src.keys(), dict_dst.keys())

            diff1 = list(set(dict_src.keys()) - set(same_keys))
            diff2 = list(set(dict_dst.keys()) - set(same_keys))

            for i in diff1:
                diff = Diff(obj_type=dict_src[i].get_type(), name=str(dict_src[i]))
                diff.missing_local = True
                # TODO Continue the tree here
                diffs.append(diff)

            for i in diff2:
                diff = Diff(obj_type=dict_dst[i].get_type(), name=str(dict_dst[i]))
                diff.missing_remote = True
                diffs.append(diff)
            for i in same_keys:

                diff = Diff(obj_type=dict_dst[i].get_type(), name=str(dict_dst[i]))

                if dict_src[i].get_attrs() != dict_dst[i].get_attrs():
                    for k, v in dict_src[i].get_attrs():
                        diff.add_item(k, v, getattr(dict_dst[i], k))

                # logger.debug(
                #     f"{dict_src[i].get_type()} {dict_dst[i]} | following the path for {dict_src[i].childs}"
                # )
                for child in dict_src[i].childs:
                    childs = self.diff_objects(
                        session=session,
                        source=getattr(dict_src[i], child),
                        dest=getattr(dict_dst[i], child),
                    )

                    for c in childs:
                        diff.add_child(c)

                diffs.append(diff)

        else:
            logger.warning(f"Type {type(source)} is not supported for now")

        return diffs

    def create_object(self, object_type, keys, params, session=None):
        self._crud_change(
            action="create",
            keys=keys,
            object_type=object_type,
            params=params,
            session=session,
        )

    def update_object(self, object_type, keys, params, session=None):
        self._crud_change(
            action="update",
            object_type=object_type,
            keys=keys,
            params=params,
            session=session,
        )

    def delete_object(self, object_type, keys, params, session=None):
        self._crud_change(
            action="delete",
            object_type=object_type,
            keys=keys,
            params=params,
            session=session,
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
                keys=keys, params=params, session=session
            )
            logger.debug(f"{action}d {object_type} - {params}")
        else:
            item = getattr(self, f"default_{action}")(
                object_type=object_type, keys=keys, params=params, session=session
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
        item = session.query(obj).filter_by(**keys).first()
        session.delete(item)
        return item
