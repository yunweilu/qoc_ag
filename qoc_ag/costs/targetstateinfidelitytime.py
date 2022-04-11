"""
targetstateinfidelitytime.py - This module defins a cost function that
penalizes the infidelity of evolved states and their respective target states
at each cost evaluation step.
"""

import numpy as np
from qoc_ag.functions.common import conjugate_transpose_ad
import autograd.numpy as anp
from qoc_ag.functions import expmat_der_vec_mul


class TargetStateInfidelityTime():
    """
    This cost penalizes the infidelity of evolved states
    and their respective target states at each cost evaluation step.
    The intended result is that a lower infidelity is
    achieved earlier in the system evolution.

    Fields:
    cost_eval_count
    cost_multiplier
    name
    requires_step_evaluation
    state_count
    target_states_dagger
    """
    name = "TargetStateInfidelityTime"
    requires_step_evaluation = True

    def __init__(self, target_states,
                 cost_multiplier=1., ):
        """
        See class fields for arguments not listed here.

        Arguments:
        target_states
        """
        if len(target_states.shape) is 2:
            self.state_transfer = False
            self.state_count = target_states.shape[0]
            self.target_states = target_states
        else:
            self.state_transfer = True
            self.state_count = 1
            self.target_states = np.array([target_states])
        self.cost_multiplier = cost_multiplier
        self.cost_multiplier = cost_multiplier
        self.target_states_dagger = conjugate_transpose_ad(self.target_states)
        self.type = "control_implicitly_related"

    def format(self, control_num, total_time_steps):
        self.total_time_steps = total_time_steps
        self.cost_normalization_constant = 1 / ((self.state_count ** 2) * total_time_steps)
        self.cost_format = (total_time_steps)
        self.grad_format = (control_num, self.total_time_steps)

    def cost(self, forward_state, mode, backward_state, cost_value, time_step):
        """
        Compute the penalty.

        Arguments:
        controls
        states
        system_eval_step

        Returns:
        cost
        """
        # The cost is the infidelity of each evolved state and its target state.
        if mode is "AD":
            return self.cost_value_ad(forward_state)
        else:
            return self.cost_value_ag(forward_state, backward_state, cost_value, time_step)

    def cost_value_ad(self, states):
        if self.state_transfer is True:
            inner_product = anp.inner(self.target_states.conjugate(), states)
        else:
            inner_product = anp.trace(anp.matmul(self.target_states_dagger, states))
        inner_product_square = anp.real(inner_product * anp.conjugate(inner_product))
        # Normalize the cost for the number of evolving states
        # and the number of times the cost is computed.
        cost_value = 1 - inner_product_square * self.cost_normalization_constant
        return cost_value * self.cost_multiplier

    def cost_value_ag(self, forward_state, backward_state, cost_value, time_step):
        inner_product = np.inner(np.conjugate(backward_state), forward_state)
        cost_value[time_step] = inner_product
        return cost_value

    def grads_factor(self, state_packages):
        grads_fac = 0.
        for state_package in state_packages:
            grads_fac = grads_fac + state_package[self.name + "_cost_value"]
        return grads_fac

    def cost_collection(self, grads_factor):
        cost_value = np.real(np.sum(grads_factor * np.conjugate(grads_factor)))
        return np.real(1 - self.cost_normalization_constant * cost_value * self.cost_multiplier)

    def gradient_initialize(self, backward_state, grads_factor):
        return backward_state * grads_factor[-1]

    def grads(self, forward_state, backward_state, H_total, H_control, grads, tol, time_step_index, control_index):
        propagator_der_state, updated_bs = expmat_der_vec_mul(H_total, H_control, tol, backward_state)
        self.updated_bs = updated_bs
        grads[control_index][time_step_index] = self.cost_multiplier * (-2 * self.cost_normalization_constant *
                                                                        np.inner(np.conjugate(propagator_der_state),
                                                                                 forward_state)) / (
                                                        self.state_count ** 2)
        return grads

    def update_bs(self, target_state, grad_factor, time_step):
        return self.updated_bs + grad_factor[time_step - 1] * target_state

    def grad_collection(self, state_packages):
        grads = np.zeros(self.grad_format)
        for state_package in state_packages:
            grads = grads + state_package[self.name + "_grad_value"]
        return np.real(grads)
