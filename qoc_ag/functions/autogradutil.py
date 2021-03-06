"""
autogutil.py - This module provides utilities for interfacing with autograd. grads function in autograd just returns
               gradients. This can return both cost values and gradients.
"""

from autograd.core import make_vjp as _make_vjp
from autograd.extend import vspace
from autograd.wrap_util import unary_to_nary
import numpy as np
from typing import Callable

@unary_to_nary
def value_and_grad(function: Callable, argnum: int) -> Callable:
    """
    Get the value and the jacobian of a function.
    This differential operator follows autograd's jacobian implementation:
    https://github.com/HIPS/autograd/blob/master/autograd/differential_operators.py
    ans_jacobian any -> tuple(any :: any, jacobian :: ndarray) - a function
        that returns the value of `function` and the jacobian
        of `function` evaluated at a given argument of `function`
    Parameters
    ----------
    function:
        any -> any - the function to differentiate
    argnum:
        int - the argument number to differentiate with respect to

    Returns
    -------
    a function that returns the value of `function` and the jacobian
    """

    vjp, ans = _make_vjp(function, argnum)
    ans_vspace = vspace(ans)
    jacobian_shape = ans_vspace.shape + vspace(argnum).shape
    grads = list(map(vjp, ans_vspace.standard_basis()))
    jacobian = np.reshape(np.stack(grads), jacobian_shape)
    return ans, jacobian
