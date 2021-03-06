# Copyright 2018 The Cirq Developers
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Linear combination represented as mapping of things to coefficients."""

from typing import (Any, Dict, ItemsView, Iterable, Iterator,
                    KeysView, Mapping, overload, Tuple, TypeVar, Union,
                    ValuesView)

Scalar = Union[complex, float]
TVector = TypeVar('TVector')

_TDefault = TypeVar('_TDefault')


class LinearDict(Dict[TVector, Scalar]):
    """Represents linear combination of things.

    LinearDict implements the basic linear algebraic operations of vector
    addition and scalar multiplication for linear combinations of abstract
    vectors. Keys represent the vectors, values represent their coefficients.
    The only requirement on the keys is that they be hashable (i.e. are
    immutable and implement __hash__ and __eq__ with equal objects hashing
    to equal values).

    A consequence of treating keys as opaque is that all relationships between
    the keys other than equality are ignored. In particular, keys are allowed
    to be linearly dependent.
    """
    def __init__(self, terms: Mapping[TVector, Scalar]) -> None:
        """Initializes linear combination from a collection of terms.

        Args:
            terms: Mapping of abstract vectors to coefficients in the linear
                combination being initialized.
        """
        super().__init__()
        self.update(terms)

    @classmethod
    def fromkeys(cls, vectors, coefficient=0):
        return LinearDict(dict.fromkeys(vectors, complex(coefficient)))

    def clean(self, *, atol: float=1e-9) -> 'LinearDict':
        """Remove terms with coefficients of absolute value atol or less."""
        negligible = [v for v, c in super().items() if abs(c) <= atol]
        for v in negligible:
            del self[v]
        return self

    def copy(self) -> 'LinearDict':
        return LinearDict(super().copy())

    def keys(self) -> KeysView[TVector]:
        snapshot = self.copy().clean(atol=0)
        return super(LinearDict, snapshot).keys()

    def values(self) -> ValuesView[Scalar]:
        snapshot = self.copy().clean(atol=0)
        return super(LinearDict, snapshot).values()

    def items(self) -> ItemsView[TVector, Scalar]:
        snapshot = self.copy().clean(atol=0)
        return super(LinearDict, snapshot).items()

    # pylint: disable=function-redefined
    @overload
    def update(self, other: Mapping[TVector, Scalar], **kwargs: Scalar) -> None:
        pass

    @overload
    def update(self,
               other: Iterable[Tuple[TVector, Scalar]],
               **kwargs: Scalar) -> None:
        pass

    @overload
    def update(self, *args: Any, **kwargs: Scalar) -> None:
        pass

    def update(self, *args, **kwargs):
        super().update(*args, **kwargs)
        self.clean(atol=0)

    @overload
    def get(self, vector: TVector) -> Scalar:
        pass

    @overload
    def get(self, vector: TVector, default: _TDefault
            ) -> Union[Scalar, _TDefault]:
        pass

    def get(self, vector, default=0):
        if super().get(vector, 0) == 0:
            return default
        return super().get(vector)
    # pylint: enable=function-redefined

    def __contains__(self, vector: Any) -> bool:
        return super().__contains__(vector) and super().__getitem__(vector) != 0

    def __getitem__(self, vector: TVector) -> Scalar:
        return super().get(vector, 0)

    def __setitem__(self, vector: TVector, coefficient: Scalar) -> None:
        if coefficient != 0:
            super().__setitem__(vector, coefficient)
            return
        if super().__contains__(vector):
            super().__delitem__(vector)

    def __iter__(self) -> Iterator[TVector]:
        snapshot = self.copy().clean(atol=0)
        return super(LinearDict, snapshot).__iter__()

    def __len__(self) -> int:
        return len([v for v, c in self.items() if c != 0])

    def __iadd__(self, other: 'LinearDict') -> 'LinearDict':
        for vector, other_coefficient in other.items():
            old_coefficient = super().get(vector, 0)
            new_coefficient = old_coefficient + other_coefficient
            super().__setitem__(vector, new_coefficient)
        self.clean(atol=0)
        return self

    def __add__(self, other: 'LinearDict') -> 'LinearDict':
        result = self.copy()
        result += other
        return result

    def __isub__(self, other: 'LinearDict') -> 'LinearDict':
        for vector, other_coefficient in other.items():
            old_coefficient = super().get(vector, 0)
            new_coefficient = old_coefficient - other_coefficient
            super().__setitem__(vector, new_coefficient)
        self.clean(atol=0)
        return self

    def __sub__(self, other: 'LinearDict') -> 'LinearDict':
        result = self.copy()
        result -= other
        return result

    def __neg__(self) -> 'LinearDict':
        return LinearDict({v: -c for v, c in self.items()})

    def __imul__(self, a: Scalar) -> 'LinearDict':
        for vector in self:
            self[vector] *= a
        self.clean(atol=0)
        return self

    def __mul__(self, a: Scalar) -> 'LinearDict':
        result = self.copy()
        result *= a
        return result

    def __rmul__(self, a: Scalar) -> 'LinearDict':
        return self.__mul__(a)

    def __truediv__(self, a: Scalar) -> 'LinearDict':
        return self.__mul__(1 / a)

    def __bool__(self) -> bool:
        return not all(c == 0 for c in self.values())

    def __eq__(self, other: Any) -> bool:
        """Checks whether two linear combinations are exactly equal.

        Presence or absence of terms with coefficients exactly equal to
        zero does not affect outcome.

        Not appropriate for most practical purposes due to sensitivity to
        numerical error in floating point coefficients. Use cirq.approx_eq()
        instead.
        """
        if not isinstance(other, LinearDict):
            return NotImplemented

        all_vs = set(self.keys()) | set(other.keys())
        return all(self[v] == other[v] for v in all_vs)

    def __ne__(self, other: Any) -> bool:
        """Checks whether two linear combinations are not exactly equal.

        See __eq__().
        """
        if not isinstance(other, LinearDict):
            return NotImplemented

        return not self == other

    def _approx_eq_(self, other: Any, atol: float) -> bool:
        """Checks whether two linear combinations are approximately equal."""
        if not isinstance(other, LinearDict):
            return NotImplemented

        all_vs = set(self.keys()) | set(other.keys())
        return all(abs(self[v] - other[v]) < atol for v in all_vs)

    @staticmethod
    def _format_coefficient(format_spec: str, coefficient: Scalar) -> str:
        coefficient = complex(coefficient)
        real_str = '{:{fmt}}'.format(coefficient.real, fmt=format_spec)
        imag_str = '{:{fmt}}'.format(coefficient.imag, fmt=format_spec)
        if float(real_str) == 0 and float(imag_str) == 0:
            return ''
        if float(imag_str) == 0:
            return real_str
        if float(real_str) == 0:
            return imag_str + 'j'
        if real_str[0] == '-' and imag_str[0] == '-':
            return '-({}+{}j)'.format(real_str[1:], imag_str[1:])
        if imag_str[0] in ['+', '-']:
            return '({}{}j)'.format(real_str, imag_str)
        return '({}+{}j)'.format(real_str, imag_str)

    @staticmethod
    def _format_term(format_spec: str,
                     vector: TVector,
                     coefficient: Scalar) -> str:
        coefficient_str = LinearDict._format_coefficient(
                format_spec, coefficient)
        if not coefficient_str:
            return coefficient_str
        result = '{}*{!s}'.format(coefficient_str, vector)
        if result[0] in ['+', '-']:
            return result
        return '+' + result

    def __format__(self, format_spec: str) -> str:
        formatted_terms = [self._format_term(format_spec, v, self[v])
                           for v in sorted(self.keys())]
        s = ''.join(formatted_terms)
        if not s:
            return '{:{fmt}}'.format(0, fmt=format_spec)
        if s[0] == '+':
            return s[1:]
        return s

    def __repr__(self) -> str:
        coefficients = dict(self)
        return 'cirq.LinearDict({!r})'.format(coefficients)

    def __str__(self):
        return self.__format__('.3f')

    def _repr_pretty_(self, p: Any, cycle: bool) -> None:
        if cycle:
            p.text('LinearDict(...)')
        else:
            p.text(str(self))

