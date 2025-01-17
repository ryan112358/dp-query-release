import torch

from dp_query_release.gem import get_args, GEM_Workloads as GEM
from dp_query_release.qm import KWayMarginalQM
from dp_query_release.utils.utils_data import get_data, get_rand_workloads
from dp_query_release.utils.utils_general import get_errors, get_per_round_budget_zCDP

import pdb

args = get_args()

data = get_data(args.dataset)
workloads = get_rand_workloads(data, args.workload, args.marginal, seed=args.workload_seed)

query_manager = KWayMarginalQM(data, workloads)
true_answers = query_manager.get_answers(data)

delta = 1.0 / len(data) ** 2
eps0, rho = get_per_round_budget_zCDP(args.epsilon, delta, args.T, alpha=args.alpha)

#from IPython import embed; embed();

device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
model_save_dir = './save/GEM/{}/{}_{}_{}/{}_{}_{}_{}/'.format(args.dataset,
                                                            args.marginal, args.workload, args.workload_seed,
                                                            args.epsilon, args.T, args.alpha, args.syndata_size)
gem = GEM(query_manager, args.T, eps0,
          data, device,
          alpha=args.alpha, default_dir=model_save_dir,
          embedding_dim=args.dim, gen_dim=[args.dim * 2],
          batch_size=args.syndata_size, loss_p=args.loss_p,
          lr=args.lr, eta_min=args.eta_min, resample=args.resample,
          max_idxs=args.max_idxs, max_iters=args.max_iters,
          ema_weights=args.ema_weights, ema_weights_beta=args.ema_weights_beta,
          ema_error_factor=0.25,
          verbose=args.verbose, seed=args.test_seed
          )
gem.fit(true_answers)

# Use 100k sampled rows as the sample dataset (will have some tiny sampling error)
syndata = gem.get_syndata()
syndata_answers = query_manager.get_answers(syndata)
errors = get_errors(true_answers, syndata_answers)
print(errors)

from IPython import embed; embed()

# Use the distribution to derive answers (usually use this)
syndata_answers = gem.get_answers()
distr_errors = get_errors(true_answers, syndata_answers)
print(distr_errors)
