import os
import subprocess
import sys
import textwrap
import threading
import time

import pytest

SRC = os.path.join(os.path.dirname(__file__), '..', '..', 'src')
sys.path.insert(0, SRC)

from common.singleton import Singleton


class TestSingleton:
  def test_singleton_same_instance(self):
    """Test that Singleton returns the same instance"""
    class TestClass(Singleton):
      def __init__(self):
        self.value = 42

    instance1 = TestClass()
    instance2 = TestClass()

    assert instance1 is instance2
    assert instance1.value == instance2.value

  def test_singleton_different_classes(self):
    """Test that different Singleton subclasses have different instances"""
    class TestClass1(Singleton):
      pass

    class TestClass2(Singleton):
      pass

    instance1 = TestClass1()
    instance2 = TestClass2()

    assert instance1 is not instance2
    assert type(instance1) != type(instance2)

  def test_init_runs_only_once(self):
    """The services dropped their `_initialized` guards on the strength of this: a second
    construction must not re-run __init__ and wipe the state the first one built."""
    class TestClass(Singleton):
      def __init__(self):
        self.counter = 0

      def increment(self):
        self.counter += 1

    instance1 = TestClass()
    instance1.increment()
    instance1.increment()

    instance2 = TestClass()
    assert instance2.counter == 2

  def test_subclass_of_a_singleton_gets_its_own_instance(self):
    class Parent(Singleton):
      pass

    class Child(Parent):
      pass

    parent = Parent()

    assert Child() is not parent
    assert type(Child()) is Child

  def test_singleton_built_inside_another_singletons_init(self):
    """Trending builds DynamoDB, which builds Aws, all while the outer construction holds the
    lock. That only works because it is reentrant; a plain Lock deadlocks.

    Runs in a child process: a deadlock leaves the shared lock held forever, which would hang
    every later test that builds a singleton instead of failing just this one."""
    script = textwrap.dedent("""
      from common.singleton import Singleton

      class Inner(Singleton):
        pass

      class Outer(Singleton):
        def __init__(self):
          self.inner = Inner()

      assert Outer().inner is Inner()
    """)
    try:
      result = subprocess.run([sys.executable, '-c', script], cwd=SRC, timeout=10,
                              capture_output=True, text=True)
    except subprocess.TimeoutExpired:
      pytest.fail('nested singleton construction deadlocked -- SingletonMeta._lock must be an RLock')

    assert result.returncode == 0, result.stderr

  def test_concurrent_first_construction_builds_one_instance(self):
    init_calls = []

    class Slow(Singleton):
      def __init__(self):
        init_calls.append(1)
        time.sleep(0.05)  # widen the window two unlocked threads would both slip through

    instances = []
    start = threading.Barrier(8)

    def build():
      start.wait()
      instances.append(Slow())

    threads = [threading.Thread(target=build) for _ in range(8)]
    for t in threads:
      t.start()
    for t in threads:
      t.join()

    assert len(init_calls) == 1
    assert all(i is instances[0] for i in instances)
