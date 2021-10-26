def xpath_endswith(src, target):
    """
    :param src:
    :param target:
    :return: an xpath expression to emulate ends-with functionality
    """
    target_len = len(target)
    return f"substring({src}, string-length({src}) - {target_len} +1) = '{target}'"
