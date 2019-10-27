#!/usr/bin/env python3
"""This is an example to train a task with TRPO algorithm.

Here it runs CartPole-v1 environment with 100 iterations.

Results:
    AverageReturn: 100
    RiseTime: itr 13
"""
from garage.experiment import run_experiment
from garage.np.baselines import LinearFeatureBaseline
from garage.tf.algos import TRPO2
from garage.tf.envs import TfEnv
from garage.tf.experiment import LocalTFRunner
from garage.tf.policies import CategoricalMLPPolicy2


def run_task(snapshot_config, *_):
    """Run task.

    Args:
        snapshot_config (dict): Snapshot configuration.
        _ (tuple): Extra info for debugging.

    """
    with LocalTFRunner(snapshot_config=snapshot_config) as runner:
        env = TfEnv(env_name='CartPole-v1')

        policy = CategoricalMLPPolicy2(name='policy',
                                       env_spec=env.spec,
                                       hidden_sizes=(32, 32))

        baseline = LinearFeatureBaseline(env_spec=env.spec)

        algo = TRPO2(env_spec=env.spec,
                     policy=policy,
                     baseline=baseline,
                     max_path_length=100,
                     discount=0.99,
                     max_kl_step=0.01)

        runner.setup(algo, env)
        runner.train(n_epochs=100, batch_size=4000)


run_experiment(
    run_task,
    snapshot_mode='last',
    seed=1,
)
