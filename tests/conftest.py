import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from common.singleton import Singleton


def _singleton_classes(cls=Singleton):
  for sub in cls.__subclasses__():
    yield sub
    yield from _singleton_classes(sub)


def _clear_singletons():
  # SingletonMeta caches on each class's own _instance. Deleting it (rather than setting None)
  # leaves the class exactly as it was before first construction.
  for cls in _singleton_classes():
    if '_instance' in cls.__dict__:
      delattr(cls, '_instance')


@pytest.fixture(autouse=True)
def reset_singletons():
  """Every test starts with fresh singletons. Without this, the first test to build Emailer,
  DynamoDB, etc. pins that instance -- and the mocks it was built with -- for the whole run."""
  _clear_singletons()
  yield
  _clear_singletons()
