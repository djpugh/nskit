import unittest

from pydantic import TypeAdapter, ValidationError

from nskit.vcs.namespace_validator import (
    _DELIMITERS,
    NamespaceOptionsType,
    NamespaceValidator,
    REPO_SEPARATOR,
)


class NamespaceOptionsTypeTestCase(unittest.TestCase):

    def setUp(self):
        self.ta = TypeAdapter(NamespaceOptionsType)

    def test_simple(self):
        self.assertEqual(self.ta.validate_python([{'a': ['b', 'c']}]), [{'a': ['b', 'c']}])

    def test_nested(self):
        self.assertEqual(self.ta.validate_python([{'a': [{'b': ['c']}]}]), [{'a': [{'b': ['c']}]}])

    def test_complex(self):
        self.assertEqual(
            self.ta.validate_python(
                [{'a': [{'b': ['c', 'd']}, 'e']}, 'f']
            ),
                [{'a': [{'b': ['c', 'd']}, 'e']}, 'f']
        )

    def test_wrong_types(self):
        with self.assertRaises(ValidationError):
            self.ta.validate_python(
                [{'a': [{'b': ['c', 'd', 3]}, 'e']}, 'f']
            )
        with self.assertRaises(ValidationError):
            self.ta.validate_python(
                {'a': [{'b': ['c', 'd']}, 'e']}
            )

        with self.assertRaises(ValidationError):
            self.ta.validate_python(
                [{'a': [{'b': ['c', ['d']]}, 'e']}, 'f']
            )


class NamespaceValidatorTestCase(unittest.TestCase):

    def setUp(self):
        self.ns_options = [
            {'a':
                [
                    {'b':
                        ['c', 'd']
                    },
                    'e'
                ]
            },
            'f'
        ]

    def test_init(self):
        nsv = NamespaceValidator(options=self.ns_options)
        self.assertEqual(nsv.options, self.ns_options)
        self.assertEqual(nsv.repo_separator, REPO_SEPARATOR)
        self.assertEqual(nsv.delimiters, _DELIMITERS)

    def test_init_wrong_options(self):
        with self.assertRaises(ValidationError):
            NamespaceValidator(
                options = [{'a': [{'b': ['c', 'd', 3]}, 'e']}, 'f']
            )
        with self.assertRaises(ValidationError):
            NamespaceValidator(
                options = {'a': [{'b': ['c', 'd']}, 'e']}
            )

        with self.assertRaises(ValidationError):
            NamespaceValidator(
                options = [{'a': [{'b': ['c', ['d']]}, 'e']}, 'f']
            )

    def test_init_custom(self):
        nsv = NamespaceValidator(options=self.ns_options, repo_separator='/', delimiters=['.'])
        self.assertEqual(nsv.options, self.ns_options)
        self.assertNotEqual(nsv.repo_separator, REPO_SEPARATOR)
        self.assertNotEqual(nsv.delimiters, _DELIMITERS)
        self.assertEqual(nsv.repo_separator, '/')
        self.assertEqual(nsv.delimiters, ['.', '/'])

    def test_validate_name_ok(self):
        nsv = NamespaceValidator(options=self.ns_options)
        self.assertEqual(nsv.validate_name('a.b.c'), (True, 'ok'))
        self.assertEqual(nsv.validate_name('a.b.c.x'), (True, 'ok'))
        self.assertEqual(nsv.validate_name('a.b.d'), (True, 'ok'))
        self.assertEqual(nsv.validate_name('a.b.d.z'), (True, 'ok'))
        self.assertEqual(nsv.validate_name('a.e'), (True, 'ok'))
        self.assertEqual(nsv.validate_name('a.e.x'), (True, 'ok'))
        self.assertEqual(nsv.validate_name('f'), (True, 'ok'))
        self.assertEqual(nsv.validate_name('f.x'), (True, 'ok'))

    def test_validate_name_wrong(self):
        nsv = NamespaceValidator(options=self.ns_options)
        self.assertEqual(nsv.validate_name('a.b.g'), (False, "Does not match valid names for b: c, d, with delimiters: ['.', ',', '-']"))
        self.assertEqual(nsv.validate_name('a.b.g.x'), (False, "Does not match valid names for b: c, d, with delimiters: ['.', ',', '-']"))
        self.assertEqual(nsv.validate_name('a.b.f'), (False, "Does not match valid names for b: c, d, with delimiters: ['.', ',', '-']"))
        self.assertEqual(nsv.validate_name('a.b.f.z'), (False, "Does not match valid names for b: c, d, with delimiters: ['.', ',', '-']"))
        self.assertEqual(nsv.validate_name('a.c'), (False, "Does not match valid names for a: b, e, with delimiters: ['.', ',', '-']"))
        self.assertEqual(nsv.validate_name('a.c.x'), (False, "Does not match valid names for a: b, e, with delimiters: ['.', ',', '-']"))
        self.assertEqual(nsv.validate_name('g'), (False, "Does not match valid names for <root>: a, f, with delimiters: ['.', ',', '-']"))

    def test_validate_name_no_constraints(self):
        nsv = NamespaceValidator(options=None)
        self.assertEqual(nsv.validate_name('a.b.c'), (True, 'no constraints set'))
        self.assertEqual(nsv.validate_name('a.b.c.x'), (True, 'no constraints set'))
        self.assertEqual(nsv.validate_name('a.b.d'), (True, 'no constraints set'))
        self.assertEqual(nsv.validate_name('a.b.d.z'), (True, 'no constraints set'))
        self.assertEqual(nsv.validate_name('a.e'), (True, 'no constraints set'))
        self.assertEqual(nsv.validate_name('a.e.x'), (True, 'no constraints set'))
        self.assertEqual(nsv.validate_name('f'), (True, 'no constraints set'))
        self.assertEqual(nsv.validate_name('f.x'), (True, 'no constraints set'))
        self.assertEqual(nsv.validate_name('a.b.g'), (True, 'no constraints set'))
        self.assertEqual(nsv.validate_name('a.b.g.x'), (True, 'no constraints set'))
        self.assertEqual(nsv.validate_name('a.b.f'), (True, 'no constraints set'))
        self.assertEqual(nsv.validate_name('a.b.f.z'), (True, 'no constraints set'))
        self.assertEqual(nsv.validate_name('a.c'), (True, 'no constraints set'))
        self.assertEqual(nsv.validate_name('a.c.x'), (True, 'no constraints set'))
        self.assertEqual(nsv.validate_name('g'), (True, 'no constraints set'))

    def test_validate_name_delimiters_ok(self):
        nsv = NamespaceValidator(options=self.ns_options)
        name = 'a.b.c'
        for delim in nsv.delimiters:
            self.assertEqual(nsv.validate_name(name.replace('.', delim)), (True, 'ok'))

    def test_validate_name_delimiters_wrong(self):
        nsv = NamespaceValidator(options=self.ns_options, repo_separator='/', delimiters=['.'])
        name = 'a-b-c'
        self.assertEqual(nsv.validate_name(name), (False, "Does not match valid names for <root>: a, f, with delimiters: ['.', '/']"))

    def test_to_parts(self):
        nsv = NamespaceValidator(options=self.ns_options, delimiters=['.'])
        self.assertEqual(nsv.to_parts('a.b.c'), ['a', 'b', 'c'])
        self.assertEqual(nsv.to_parts('a/b/c'), ['a/b/c',])

    def test_to_parts_no_options(self):
        nsv = NamespaceValidator(options=None, delimiters=['.'])
        self.assertEqual(nsv.to_parts('a.b.c'), ['a.b.c'])
        self.assertEqual(nsv.to_parts('a/b/c'), ['a/b/c',])

    def test_to_repo_name(self):
        nsv = NamespaceValidator(options=self.ns_options, delimiters=['.'], repo_separator='-')
        self.assertEqual(nsv.to_repo_name('a.b.c'), 'a-b-c')
        self.assertEqual(nsv.to_repo_name('a/b/c'), 'a/b/c')

    def test_to_repo_name_no_options(self):
        nsv = NamespaceValidator(options=None, delimiters=['.'], repo_separator='-')
        self.assertEqual(nsv.to_repo_name('a.b.c'), 'a.b.c')
        self.assertEqual(nsv.to_repo_name('a/b/c'), 'a/b/c')
