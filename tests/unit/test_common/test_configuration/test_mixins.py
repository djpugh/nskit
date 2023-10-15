import unittest

from pydantic import BaseModel

from nskit.common.configuration.mixins import PropertyDumpMixin


class PropertyDumpMixinTestCase(unittest.TestCase):

    def test_no_properties(self):

        class TestModel(PropertyDumpMixin, BaseModel):
            a: str = 'a'
            b: int = 1

        t = TestModel()
        self.assertEqual(t.model_dump(), {'a': 'a', 'b': 1 })

    def test_no_properties_exclude(self):

        class TestModel(PropertyDumpMixin, BaseModel):
            a: str = 'a'
            b: int = 1

        t = TestModel()
        self.assertEqual(t.model_dump(exclude=['a']), {'b': 1 })
        self.assertEqual(t.model_dump(exclude={'a'}), {'b': 1 })

    def test_properties(self):

        class TestModel(PropertyDumpMixin, BaseModel):
            a: str = 'a'
            b: int = 1

            @property
            def c(self):
                return 1.2

        t = TestModel()
        self.assertEqual(t.model_dump(), {'a': 'a', 'b': 1, 'c': 1.2})

    def test_properties_exclude(self):

        class TestModel(PropertyDumpMixin, BaseModel):
            a: str = 'a'
            b: int = 1

            @property
            def c(self):
                return 1.2

        t = TestModel()
        self.assertEqual(t.model_dump(exclude=['a', 'c']), {'b': 1 })
        self.assertEqual(t.model_dump(exclude={'a'}), {'b': 1 , 'c': 1.2})

    def test_properties_excluded(self):

        class TestModel(PropertyDumpMixin, BaseModel):
            a: str = 'a'
            b: int = 1
            _excluded_properties = ['d']

            @property
            def c(self):
                return 1.2

            @property
            def d(self):
                return True

        t = TestModel()
        self.assertEqual(t._excluded_properties, ['d'])
        self.assertEqual(t.model_dump(exclude=['a', 'c']), {'b': 1 })
        self.assertEqual(t.model_dump(exclude={'a'}), {'b': 1 , 'c': 1.2})
        self.assertEqual(t.model_dump(), {'a': 'a', 'b': 1 , 'c': 1.2})
        self.assertEqual(t.model_dump(include={'a', 'd'}), {'a': 'a' , 'd': True})