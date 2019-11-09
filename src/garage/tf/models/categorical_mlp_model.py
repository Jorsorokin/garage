"""MLP Model.

A model composed only of a multi-layer perceptron (MLP), which maps
real-valued inputs to real-valued outputs.
"""
import tensorflow as tf
import tensorflow_probability as tfp

from garage.tf.models.mlp_model import MLPModel


class CategoricalMLPModel(MLPModel):
    """Categorical MLP Model.

    Args:
        output_dim (int): Dimension of the network output.
        hidden_sizes (list[int]): Output dimension of dense layer(s).
            For example, (32, 32) means this MLP consists of two
            hidden layers, each with 32 hidden units.
        name (str): Model name, also the variable scope.
        hidden_nonlinearity (callable): Activation function for intermediate
            dense layer(s). It should return a tf.Tensor. Set it to
            None to maintain a linear activation.
        hidden_w_init (callable): Initializer function for the weight
            of intermediate dense layer(s). The function should return a
            tf.Tensor.
        hidden_b_init (callable): Initializer function for the bias
            of intermediate dense layer(s). The function should return a
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
        layer_normalization (bool): Bool for using layer normalization or not.
    """

    def __init__(self,
                 output_dim,
                 name='CategoricalMLPModel',
                 hidden_sizes=(32, 32),
                 hidden_nonlinearity=tf.nn.relu,
                 hidden_w_init=tf.glorot_uniform_initializer(),
                 hidden_b_init=tf.zeros_initializer(),
                 output_nonlinearity=None,
                 output_w_init=tf.glorot_uniform_initializer(),
                 output_b_init=tf.zeros_initializer(),
                 layer_normalization=False):
        super().__init__(
            output_dim,
            name,
            hidden_sizes,
            hidden_nonlinearity,
            hidden_w_init,
            hidden_b_init,
            output_nonlinearity,
            output_w_init,
            output_b_init,
            layer_normalization)

    def network_output_spec(self):
        """Network output spec."""
        return ['prob', 'dist']

    def _build(self, state_input, name=None):
        prob = super()._build(state_input, name=name)
        dist = tfp.distributions.OneHotCategorical(prob)
        return prob, dist
