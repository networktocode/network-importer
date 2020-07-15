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

from .diff import Diff, DiffElement
from .utils import intersection

logger = logging.getLogger(__name__)


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

    # Add mapping to object here

    top_level = []

    def __init__(self, db="sqlite:///:memory:"):

        from sqlalchemy.pool import StaticPool
        self.engine = create_engine(db, poolclass=StaticPool)
        self.base.metadata.bind = self.engine
        self.base.metadata.create_all(self.engine)
        self.__sm__ = sessionmaker(bind=self.engine)

    def init(self):
        raise NotImplementedError

    def clean(self):
        pass

    def start_session(self):
        return self.__sm__()

    def sync(self, source):
        """Syncronize the current DSync object with the source

        Args:
            source: DSync object to sync with this one
        """

        diff = self.diff(source)

        session = self.start_session()

        for child in diff.get_childs():
            self.sync_element(child, session)

        logger.info("Saving Changes")
        session.commit()

    # def sync_objects(self, source, dest, session):
    #     """

    #     Args:
    #         source: NetMod object to sync with this one
    #     """

    #     if type(source) != type(dest):
    #         logger.warning(f"Attribute {source} are of different types")
    #         return False

    #     if isinstance(source, list):
    #         dict_src = {str(item): item for item in source}
    #         dict_dst = {str(item): item for item in dest}

    #         same_keys = intersection(dict_src.keys(), dict_dst.keys())

    #         diff1 = list(set(dict_src.keys()) - set(same_keys))
    #         diff2 = list(set(dict_dst.keys()) - set(same_keys))

    #         for i in diff1:
    #             logger.info(f"{i} is missing, need to Add it")
    #             # import pdb;pdb.set_trace()
    #             self.create_object(
    #                 object_type=dict_src[i].get_type(),
    #                 keys=dict_src[i].get_keys(),
    #                 params=dict_src[i].get_attrs(),
    #                 session=session,
    #             )
    #             # TODO Continue the tree here

    #         for i in diff2:
    #             logger.info(f"{i} is missing in Source, need to Delete")
    #             self.delete_object(
    #                 object_type=dict_dst[i].get_type(),
    #                 keys=dict_dst[i].get_keys(),
    #                 params=dict_dst[i].get_attrs(),
    #                 session=session,
    #             )

    #         # logger.debug(f"Same Keys: {same_keys}")
    #         for i in same_keys:
    #             if dict_src[i].get_attrs() != dict_dst[i].get_attrs():
    #                 logger.info(
    #                     f"{dict_src[i].get_type()} {dict_dst[i]} | SRC and DST are not in sync, updating"
    #                 )
    #                 self.update_object(
    #                     object_type=dict_src[i].get_type(),
    #                     keys=dict_dst[i].get_keys(),
    #                     params=dict_src[i].get_attrs(),
    #                     session=session,
    #                 )

    #             logger.debug(
    #                 f"{dict_src[i].get_type()} {dict_dst[i]} | following the path for {dict_src[i].childs}"
    #             )
    #             for child in dict_src[i].childs:
    #                 self.sync_objects(
    #                     session=session,
    #                     source=getattr(dict_src[i], child),
    #                     dest=getattr(dict_dst[i], child),
    #                 )

    #     else:
    #         print(f"Type {type(source)} is not supported for now")

    #     return True

    def sync_element(self, element: DiffElement, session):

        if not element.has_diffs():
            return False

        if element.source_attrs == None:
            self.delete_object(
                object_type=element.type,
                keys=element.keys,
                params=element.dest_attrs,
                session=session,
            )
        elif element.dest_attrs == None:
            self.create_object(
                object_type=element.type,
                keys=element.keys,
                params=element.source_attrs,
                session=session,
            )
        elif element.source_attrs != element.dest_attrs:

            self.update_object(
                object_type=element.type,
                keys=element.keys,
                params=element.source_attrs,
                session=session,
            )

        for child in element.get_childs():
            self.sync_element(child, session)

    def diff(self, source):
        """
        Generate a Diff object between 2 DSync objects
        """
        source_session = source.start_session()
        local_session = self.start_session()

        diff = Diff()

        for obj in intersection(self.top_level, source.top_level):

            diff_elements = self.diff_objects(
                source=source_session.query(getattr(source, obj)).all(),
                dest=local_session.query(getattr(source, obj)).all(),
                session=local_session,
            )

            for element in diff_elements:
                diff.add(obj, element)

        return diff

    def diff_objects(self, source, dest, session):
        """ """
        if type(source) != type(dest):
            logger.warning(f"Attribute {source} are of different types")
            return False

        diffs = []

        if isinstance(source, list):

            # Convert both list into a Dict and using the str representation as Key
            # in the future consider using a dedicated function as key
            dict_src = {str(item): item for item in source}
            dict_dst = {str(item): item for item in dest}

            # Identify the shared keys between SRC and DST DSync
            # The keys missing in DST Dsync
            # The keys missing in SRT DSync
            same_keys = intersection(dict_src.keys(), dict_dst.keys())
            missing_dst = list(set(dict_src.keys()) - set(same_keys))
            missing_src = list(set(dict_dst.keys()) - set(same_keys))

            for key in missing_dst:
                de = DiffElement(
                    obj_type=dict_src[key].get_type(),
                    name=str(dict_src[key]),
                    keys=dict_src[key].get_keys(),
                )
                de.add_attrs(source=dict_src[key].get_attrs(), dest=None)
                diffs.append(de)
                # TODO Continue the tree here

            for key in missing_src:
                de = DiffElement(
                    obj_type=dict_dst[key].get_type(),
                    name=str(dict_dst[key]),
                    keys=dict_dst[key].get_keys(),
                )
                de.add_attrs(source=None, dest=dict_dst[key].get_attrs())
                diffs.append(de)
                # TODO Continue the tree here

            for key in same_keys:

                de = DiffElement(
                    obj_type=dict_dst[key].get_type(),
                    name=str(dict_dst[key]),
                    keys=dict_dst[key].get_keys(),
                )

                de.add_attrs(
                    source=dict_src[key].get_attrs(), dest=dict_dst[key].get_attrs(),
                )

                # logger.debug(
                #     f"{dict_src[i].get_type()} {dict_dst[i]} | {i}"
                # )

                # if dict_src[i].get_attrs() != dict_dst[i].get_attrs():
                #     attrs = dict_src[i].get_attrs()
                #     for k, v in attrs.items():
                #         diff.add_item(k, v, getattr(dict_dst[i], k))

                # logger.debug(
                #     f"{dict_src[i].get_type()} {dict_dst[i]} | following the path for {dict_src[i].childs}"
                # )

                for child in dict_src[key].childs:
                    childs = self.diff_objects(
                        session=session,
                        source=getattr(dict_src[key], child),
                        dest=getattr(dict_dst[key], child),
                    )

                    for c in childs:
                        de.add_child(c)

                diffs.append(de)

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
        item = session.query(obj).filter_by(**keys).first()
        item.update(**params)
        return item

    def default_delete(self, object_type, keys, params, session):
        obj = getattr(self, object_type)
        item = session.query(obj).filter_by(**keys).first()
        session.delete(item)
        return item
