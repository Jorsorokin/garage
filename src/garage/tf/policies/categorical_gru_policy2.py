"""CategoricalGRUPolicy with model."""
import akro
import numpy as np
import tensorflow as tf

from garage.tf.models import CategoricalGRUModel
from garage.tf.policies import StochasticPolicy2


class CategoricalGRUPolicy2(StochasticPolicy2):
    """CategoricalGRUPolicy

    A policy that contains a GRU to make prediction based on
    a categorical distribution.

    It only works with akro.Discrete action space.

    Args:
        env_spec (garage.envs.env_spec.EnvSpec): Environment specification.
        name (str): Policy name, also the variable scope.
        hidden_dim (int): Hidden dimension for LSTM cell.
        hidden_nonlinearity (callable): Activation function for intermediate
            dense layer(s). It should return a tf.Tensor. Set it to
            None to maintain a linear activation.
        hidden_w_init (callable): Initializer function for the weight
            of intermediate dense layer(s). The function should return a
            tf.Tensor.
        hidden_b_init (callable): Initializer function for the bias
            of intermediate dense layer(s). The function should return a
            tf.Tensor.
        recurrent_nonlinearity (callable): Activation function for recurrent
            layers. It should return a tf.Tensor. Set it to None to
            maintain a linear activation.
        recurrent_w_init (callable): Initializer function for the weight
            of recurrent layer(s). The function should return a
            tf.Tensor.
        output_nonlinearity (callable): Activation function for output dense
            layer. It should return a tf.Tensor. Set it to None to
            maintain a linear activation.
        output_w_init (callable): Initializer function for the weight
            of output dense layer(s). The function should return a
            tf.Tensor.
        output_b_init (callable): Initializer function for the bias
            of output dense layer(s). The function should return a
            tf.Tensor.
        hidden_state_init (callable): Initializer function for the
            initial hidden state. The functino should return a tf.Tensor.
        hidden_state_init_trainable (bool): Bool for whether the initial
            hidden state is trainable.
        state_include_action (bool): Whether the state includes action.
            If True, input dimension will be
            (observation dimension + action dimension).
        layer_normalization (bool): Bool for using layer normalization or not.
    """

    def __init__(self,
                 env_spec,
                 name='CategoricalGRUPolicy',
                 hidden_dim=32,
                 hidden_nonlinearity=tf.nn.tanh,
                 hidden_w_init=tf.glorot_uniform_initializer(),
                 hidden_b_init=tf.zeros_initializer(),
                 recurrent_nonlinearity=tf.nn.sigmoid,
                 recurrent_w_init=tf.glorot_uniform_initializer(),
                 output_nonlinearity=tf.nn.softmax,
                 output_w_init=tf.glorot_uniform_initializer(),
                 output_b_init=tf.zeros_initializer(),
                 hidden_state_init=tf.zeros_initializer(),
                 hidden_state_init_trainable=False,
                 state_include_action=True,
                 layer_normalization=False):
        if not isinstance(env_spec.action_space, akro.Discrete):
            raise ValueError('CategoricalGRUPolicy only works'
                             'with akro.Discrete action space.')

        super().__init__(name, env_spec)
        self._obs_dim = env_spec.observation_space.flat_dim
        self._action_dim = env_spec.action_space.n

        self._hidden_dim = hidden_dim
        self._hidden_nonlinearity = hidden_nonlinearity
        self._hidden_w_init = hidden_w_init
        self._hidden_b_init = hidden_b_init
        self._recurrent_nonlinearity = recurrent_nonlinearity
        self._recurrent_w_init = recurrent_w_init
        self._output_nonlinearity = output_nonlinearity
        self._output_w_init = output_w_init
        self._output_b_init = output_b_init
        self._hidden_state_init = hidden_state_init
        self._hidden_state_init_trainable = hidden_state_init_trainable
        self._layer_normalization = layer_normalization
        self._state_include_action = state_include_action

        if state_include_action:
            self._input_dim = self._obs_dim + self._action_dim
        else:
            self._input_dim = self._obs_dim

        self.model = CategoricalGRUModel(
            output_dim=self._action_dim,
            hidden_dim=self._hidden_dim,
            name='prob_network',
            hidden_nonlinearity=hidden_nonlinearity,
            hidden_w_init=hidden_w_init,
            hidden_b_init=hidden_b_init,
            recurrent_nonlinearity=recurrent_nonlinearity,
            recurrent_w_init=recurrent_w_init,
            hidden_state_init=hidden_state_init,
            hidden_state_init_trainable=hidden_state_init_trainable,
            output_nonlinearity=output_nonlinearity,
            output_w_init=output_w_init,
            output_b_init=output_b_init,
            layer_normalization=layer_normalization)

        self._prev_actions = None
        self._prev_hiddens = None

    def build(self, state_var, name=None):
        with tf.compat.v1.variable_scope(self.name) as vs:
            self._variable_scope = vs
            step_input_var = tf.compat.v1.placeholder(shape=(None,
                                                             self._input_dim),
                                                      name='step_input',
                                                      dtype=tf.float32)
            step_hidden_var = tf.compat.v1.placeholder(shape=(None,
                                                              self._hidden_dim),
                                                       name='step_hidden_input',
                                                       dtype=tf.float32)
            self.model.build(state_var, step_input_var, step_hidden_var, name=name)

        self._f_step_prob = tf.compat.v1.get_default_session().make_callable(
            [
                self.model.networks['default'].step_output,
                self.model.networks['default'].step_hidden
            ],
            feed_list=[step_input_var, step_hidden_var])

    @property
    def vectorized(self):
        """Vectorized or not."""
        return True

    def reset(self, dones=None):
        """Reset the policy."""
        if dones is None:
            dones = [True]
        dones = np.asarray(dones)
        if self._prev_actions is None or len(dones) != len(self._prev_actions):
            self._prev_actions = np.zeros(
                (len(dones), self.action_space.flat_dim))
            self._prev_hiddens = np.zeros((len(dones), self._hidden_dim))

        self._prev_actions[dones] = 0.
        self._prev_hiddens[dones] = self.model.networks[
            'default'].init_hidden.eval()

    def get_action(self, observation):
        """Return a single action."""
        actions, agent_infos = self.get_actions([observation])
        return actions[0], {k: v[0] for k, v in agent_infos.items()}

    def get_actions(self, observations):
        """Return multiple actions."""
        if self._state_include_action:
            assert self._prev_actions is not None
            all_input = np.concatenate([observations, self._prev_actions], axis=-1)
        else:
            all_input = observations
        probs, hidden_vec = self._f_step_prob(all_input, self._prev_hiddens)
        actions = list(map(self.action_space.weighted_sample, probs))
        prev_actions = self._prev_actions
        self._prev_actions = self.action_space.flatten_n(actions)
        self._prev_hiddens = hidden_vec
        agent_info = dict(prob=probs)
        if self._state_include_action:
            agent_info['prev_action'] = np.copy(prev_actions)
        return actions, agent_info

    @property
    def recurrent(self):
        """Recurrent or not."""
        return True

    @property
    def distribution(self):
        return self.model.networks['default'].dist

    @property
    def state_info_specs(self):
        """State info specification."""
        if self._state_include_action:
            return [
                ('prev_action', (self._action_dim, )),
            ]
        else:
            return []

    def clone(self, name):
        """Return a clone of the policy.

        It only copies the configuration of the primitive,
        not the parameters.

        Args:
            name (str): Name of the newly created policy. It has to be
                different from source policy if cloned under the same
                computational graph.

        Returns:
            garage.tf.policies.Policy: Newly cloned policy.

        """
        return self.__class__(name=name,
                              env_spec=self._env_spec,
                              hidden_dim=self._hidden_dim,
                              hidden_nonlinearity=self._hidden_nonlinearity,
                              hidden_w_init=self._hidden_w_init,
                              hidden_b_init=self._hidden_b_init,
                              recurrent_nonlinearity=self._recurrent_nonlinearity,
                              recurrent_w_init=self._recurrent_w_init,
                              output_nonlinearity=self._output_nonlinearity,
                              output_w_init=self._output_w_init,
                              output_b_init=self._output_b_init,
                              hidden_state_init=self._hidden_state_init,
                              hidden_state_init_trainable=self._hidden_state_init_trainable,
                              state_include_action=self._state_include_action,
                              layer_normalization=self._layer_normalization)

    def __getstate__(self):
        """Object.__getstate__."""
        new_dict = super().__getstate__()
        del new_dict['_f_step_prob']
        return new_dict

    def __setstate__(self, state):
        """Object.__setstate__."""
        super().__setstate__(state)
