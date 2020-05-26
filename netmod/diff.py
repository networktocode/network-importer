import logging

logger = logging.getLogger("network-importer")

def intersection(lst1, lst2): 
    lst3 = [value for value in lst1 if value in lst2] 
    return lst3


def diff_attrs(attr1, attr2):
    """

    """

    if type(attr1) != type(attr2):
        logger.warning(f"Attribute {attr1} are of different types")
        return False

    if isinstance(attr1, str):
        if attr1 != attr2:
            logger.warning(f"Attribute {attr1} have different values")
            return False

        return True

    if isinstance(attr1, list):
        dict1 = {item.name: item for item in attr1}
        dict2 = {item.name: item for item in attr2}

        same_keys = intersection(dict1.keys(), dict2.keys())

        diff1 = list(set(dict1.keys())-set(same_keys))
        diff2 = list(set(dict2.keys())-set(same_keys))

        for i in diff1:
            print(f"{i} is missing in ONE")

        for i in diff2:
            print(f"{i} is missing in TWO")

        for i in same_keys:
            for attrs in dict1[i].diffs:
                diff_attrs(getattr(dict1[i], attrs), getattr(dict2[i], attrs))

        return True

    print("not supported type for now")

def update_src_dst(mod_src, mod_dst, ses_src=None, ses_dst=None, attr_src=None, attr_dst=None):
    """

    """

    top_level = False
    if not ses_src and not ses_dst:
        ses_src = mod_src.start_session()
        ses_dst = mod_dst.start_session()

    if not attr_src and not attr_dst:
        attr_src = ses_src.query(mod_src.device).all()
        attr_dst = ses_dst.query(mod_dst.device).all()

    if type(attr_src) != type(attr_dst):
        logger.warning(f"Attribute {attr_src} are of different types")
        return False

    if isinstance(attr_src, str):
        if attr_src != attr_dst:
            logger.warning(f"Attribute {attr_src} have different values")
            return False

        logger.debug(f"{attr_src} is of type String")
        return True

    if isinstance(attr_src, list):
        dict_src = {item.name: item for item in attr_src}
        dict_dst = {item.name: item for item in attr_dst}

        same_keys = intersection(dict_src.keys(), dict_dst.keys())

        diff1 = list(set(dict_src.keys())-set(same_keys))
        diff2 = list(set(dict_dst.keys())-set(same_keys))

        for i in diff1:
            logger.info(f"{i} is missing in Dest, need to Add it in Dest")
            
            # import pdb;pdb.set_trace()

        for i in diff2:
            logger.info(f"{i} is missing in Source, need to Delete it in Dest")

        for i in same_keys:
            logger.info(f"{i} is present in both, following the path for {dict_src[i].diffs}")
            for attr in dict_src[i].diffs:
                update_src_dst(
                    mod_src=mod_src,
                    mod_dst=mod_dst,
                    ses_src=ses_src,
                    ses_dst=ses_dst,
                    attr_src=getattr(dict_src[i], attr),
                    attr_dst=getattr(dict_dst[i], attr)
                )

        return True

    logger.warning("not supported type for now")



# def diff_nets(nb, foo):
#     session1 = nb.start_session()
#     session2 = foo.start_session()

#     dev1 = session1.query(nb.network).get(1)
#     nw2 = nb.get(session1)

#     for item in nb.diffs:

#         i1 = getattr(nw1, item)
#         i2 = getattr(nw2, item)

