"""Historical defaults still imported by migrations for the retired module."""
from uuid import uuid4


def resource_category_key():
    return 'c_' + uuid4().hex[:18]
