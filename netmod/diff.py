import logging

logger = logging.getLogger("network-importer")

def intersection(lst1, lst2): 
    lst3 = [value for value in lst1 if value in lst2] 
    return lst3


# def diff_attrs(attr1, attr2):
#     """

#     """

#     if type(attr1) != type(attr2):
#         logger.warning(f"Attribute {attr1} are of different types")
#         return False

#     if isinstance(attr1, str):
#         if attr1 != attr2:
#             logger.warning(f"Attribute {attr1} have different values")
#             return False

#         return True

#     if isinstance(attr1, list):
#         dict1 = {item.name: item for item in attr1}
#         dict2 = {item.name: item for item in attr2}

#         same_keys = intersection(dict1.keys(), dict2.keys())

#         diff1 = list(set(dict1.keys())-set(same_keys))
#         diff2 = list(set(dict2.keys())-set(same_keys))

#         for i in diff1:
#             print(f"{i} is missing in ONE")

#         for i in diff2:
#             print(f"{i} is missing in TWO")

#         for i in same_keys:
#             for attrs in dict1[i].diffs:
#                 diff_attrs(getattr(dict1[i], attrs), getattr(dict2[i], attrs))

#         return True

#     print(f"Type {type(attr1)} is not supported for now")

def update_src_dst(mod_src, mod_dst, ses_src=None, ses_dst=None, attr_src=None, attr_dst=None):
    """

    """0

    local_session = False
    if not ses_src and not ses_dst:
        ses_src = mod_src.start_session()
        ses_dst = mod_dst.start_session()
        attr_src = ses_src.query(mod_src.device).all()
        attr_dst = ses_dst.query(mod_dst.device).all()
        local_session = True

    if type(attr_src) != type(attr_dst):
        logger.warning(f"Attribute {attr_src} are of different types")
        return False

    if isinstance(attr_src, str):
        if attr_src != attr_dst:
            logger.warning(f"Attribute {attr_src} have different values")
            return False

        logger.debug(f"{attr_src} is of type String")

    elif isinstance(attr_src, list):
        dict_src = {str(item): item for item in attr_src}
        dict_dst = {str(item): item for item in attr_dst}

        same_keys = intersection(dict_src.keys(), dict_dst.keys())

        diff1 = list(set(dict_src.keys())-set(same_keys))
        diff2 = list(set(dict_dst.keys())-set(same_keys))

        for i in diff1:
            logger.info(f"{i} is missing in Dest, need to Add it in Dest")
            # import pdb;pdb.set_trace()
            mod_dst.create(
                object_type=dict_src[i].get_type(),
                keys=dict_src[i].get_keys(),
                params=dict_src[i].get_attrs(),
                session=ses_dst
            )
            # TODO Continue the tree here

        for i in diff2:
            logger.info(f"{i} is missing in Source, need to Delete it in Dest")
            mod_dst.delete(
                object_type=dict_src[i].get_type(),
                keys=dict_src[i].get_keys(),
                params=dict_src[i].get_attrs(),
                session=ses_dst
            )

        # logger.debug(f"Same Keys: {same_keys}")
        for i in same_keys:
            if dict_src[i].get_attrs() != dict_dst[i].get_attrs():
                logger.info(f"{dict_src[i].get_type()} {dict_dst[i]} | SRC and DST are not in sync, updating")
                mod_dst.update(
                    object_type=dict_src[i].get_type(),
                    keys=dict_dst[i].get_keys(),
                    params=dict_src[i].get_attrs(),
                    session=ses_dst
                )

            logger.debug(f"{dict_src[i].get_type()} {dict_dst[i]} | following the path for {dict_src[i].childs}")
            for child in dict_src[i].childs:
                update_src_dst(
                    mod_src=mod_src,
                    mod_dst=mod_dst,
                    ses_src=ses_src,
                    ses_dst=ses_dst,
                    attr_src=getattr(dict_src[i], child),
                    attr_dst=getattr(dict_dst[i], child)
                )

    else:
        print(f"Type {type(attr_src)} is not supported for now")

    if local_session:
        logger.info("Saving Changes to Source and Dest NetMod")
        ses_src.commit()
        ses_dst.commit()

    return True


# def diff_nets(nb, foo):
#     session1 = nb.start_session()
#     session2 = foo.start_session()

#     dev1 = session1.query(nb.network).get(1)
#     nw2 = nb.get(session1)

#     for item in nb.diffs:

#         i1 = getattr(nw1, item)
#         i2 = getattr(nw2, item)

