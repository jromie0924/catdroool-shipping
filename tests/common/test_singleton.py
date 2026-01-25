import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

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
  
  def test_singleton_shared_state(self):
    """Test that state is shared across singleton instances"""
    class TestClass(Singleton):
      def __init__(self):
        if not hasattr(self, '_initialized'):
          self._initialized = True
          self.counter = 0
      
      def increment(self):
        self.counter += 1
    
    instance1 = TestClass()
    instance1.increment()
    instance1.increment()
    
    instance2 = TestClass()
    assert instance2.counter == 2
