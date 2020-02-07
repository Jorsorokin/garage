"""PEARL HalfCheetahDir example."""

import akro
import numpy as np

from garage.envs import normalize
from garage.envs.base import GarageEnv
from garage.envs.env_spec import EnvSpec
from garage.envs.half_cheetah_dir_env import HalfCheetahDirEnv
from garage.experiment import LocalRunner, run_experiment
from garage.sampler import PEARLSampler
from garage.torch.algos import PEARLSAC
from garage.torch.embeddings import MLPEncoder
from garage.torch.q_functions import ContinuousMLPQFunction
from garage.torch.policies import ContextConditionedPolicy, \
    TanhGaussianMLPPolicy2
import garage.torch.utils as tu

params = dict(
    num_epochs=500,
    num_train_tasks=2,
    num_test_tasks=2,
    latent_size=5,
    net_size=300,
    meta_batch_size=4,
    num_steps_per_epoch=2000,
    num_initial_steps=2000,
    num_tasks_sample=5,
    num_steps_prior=1000,
    num_extra_rl_steps_posterior=1000,
    num_evals=4,
    num_steps_per_eval=600,
    batch_size=256,
    embedding_batch_size=256,
    embedding_mini_batch_size=256,
    max_path_length=200,
    reward_scale=5.,
    use_gpu=True,
)


def run_task(snapshot_config, *_):
    """Set up environment and algorithm and run the task.

    Args:
        snapshot_config (garage.experiment.SnapshotConfig): The snapshot
            configuration used by LocalRunner to create the snapshotter.
            If None, it will create one with default settings.
        _ : Unused parameters

    """
    # create multi-task environment and sample tasks
    env = GarageEnv(normalize(HalfCheetahDirEnv()))
    runner = LocalRunner(snapshot_config)
    obs_dim = int(np.prod(env.observation_space.shape))
    action_dim = int(np.prod(env.action_space.shape))
    reward_dim = 1

    # instantiate networks
    encoder_in_dim = obs_dim + action_dim + reward_dim
    encoder_out_dim = params['latent_size'] * 2
    net_size = params['net_size']

    context_encoder = MLPEncoder(input_dim=encoder_in_dim,
                                 output_dim=encoder_out_dim,
                                 hidden_sizes=[200, 200, 200])

    space_a = akro.Box(low=-1, high=1, shape=(obs_dim+params['latent_size'], ), dtype=np.float32)
    space_b = akro.Box(low=-1, high=1, shape=(action_dim, ), dtype=np.float32)
    augmented_env = EnvSpec(space_a, space_b)

    qf1 = ContinuousMLPQFunction(env_spec=augmented_env,
                                 hidden_sizes=[net_size, net_size, net_size])

    qf2 = ContinuousMLPQFunction(env_spec=augmented_env,
                                 hidden_sizes=[net_size, net_size, net_size])

    obs_space = akro.Box(low=-1, high=1, shape=(obs_dim, ), dtype=np.float32)
    action_space = akro.Box(low=-1, high=1, shape=(params['latent_size'], ), dtype=np.float32)
    vf_env = EnvSpec(obs_space, action_space)

    vf = ContinuousMLPQFunction(env_spec=vf_env,
                                hidden_sizes=[net_size, net_size, net_size])

    policy = TanhGaussianMLPPolicy2(
        env_spec=augmented_env,
        hidden_sizes=[net_size, net_size, net_size])

    context_conditioned_policy = ContextConditionedPolicy(
        latent_dim=params['latent_size'],
        context_encoder=context_encoder,
        policy=policy,
        use_ib=params['use_information_bottleneck'],
        use_next_obs=params['use_next_obs_in_context'],
    )

    pearlsac = PEARLSAC(
        env=env,
        policy=context_conditioned_policy,
        qf1=qf1,
        qf2=qf2,
        vf=vf,
        num_train_tasks=params['num_train_tasks'],
        num_test_tasks=params['num_test_tasks'],
        latent_dim=params['latent_size'],
        meta_batch_size=params['meta_batch_size'],
        num_steps_per_epoch=params['num_steps_per_epoch'],
        num_initial_steps=params['num_initial_steps'],
        num_tasks_sample=params['num_tasks_sample'],
        num_steps_prior=params['num_steps_prior'],
        num_extra_rl_steps_posterior=params['num_extra_rl_steps_posterior'],
        num_evals=params['num_evals'],
        num_steps_per_eval=params['num_steps_per_eval'],
        batch_size=params['batch_size'],
        embedding_batch_size=params['embedding_batch_size'],
        embedding_mini_batch_size=params['embedding_mini_batch_size'],
        max_path_length=params['max_path_length'],
        reward_scale=params['reward_scale'],
    )

    tu.set_gpu_mode(params['use_gpu'], gpu_id=0)
    if params['use_gpu']:
        pearlsac.to()

    runner.setup(algo=pearlsac, env=env, sampler_cls=PEARLSampler,
        sampler_args=dict(max_path_length=params['max_path_length']))
    runner.train(n_epochs=params['num_epochs'], batch_size=params['batch_size'])


run_experiment(
    run_task,
    snapshot_mode='last',
    seed=1,
)
