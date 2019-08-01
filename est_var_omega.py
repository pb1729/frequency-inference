import numpy as np
from scipy.fftpack import dct, idct
from matplotlib import pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

from sim import *



def perturb_omega(omega, v1):
    return clip_omega(omega + np.random.normal(0., np.sqrt(v1)))


def sample_omega_list(omegas, prior, v1, length):
    omega0 = sample_dist(omegas, prior)
    omega_list = [omega0]
    for i in range(1, length):
        omega_list.append(perturb_omega(omega_list[-1], v1))
    return omega_list


# RULE: all fn calls should preserve normalization 
class ParticleDist:
    def normalize(self):
        self.dist = normalize(self.dist)
    def mean_omega(self):
        return np.sum(self.dist * self.omegas)
    def mean_log_v1(self):
        return np.sum(self.dist * np.log(self.v1s))
    def many_update(self, ts, ms):
        for t, m in zip(ts, ms):
            self.wait_u()
            self.update(t, m)
    def get_name(self):
        return self.name


class GridDist(ParticleDist):
    name = 'grid_dist'
    def __init__(self, omegas, v1s, prior):
        assert omegas.shape + v1s.shape == prior.shape
        self.shape = prior.shape
        self.omegas = np.copy(omegas).reshape((omegas.size, 1))
        self.v1s = np.copy(v1s).reshape((1, v1s.size))
        self.dist = np.copy(prior)
    def wait_u(self):
        ''' given a posterior distribution for omega at time t,
            we find the dist for omega at time t+u '''
        diff = self.omegas[-1] - self.omegas[0]
        fact = ((self.v1s * np.pi**2) / (2. * diff**2))
        cos_coeffs = dct(self.dist, axis=0) # switch to fourier space, in terms of cosines to get Neumann BC
        n = np.outer(np.arange(self.shape[0]), np.ones(self.shape[1]))
        cos_coeffs *= np.exp( - fact * n**2 ) # heat eq update
        self.dist = idct(cos_coeffs, axis=0) / (2 * self.shape[0]) # switch back to the usual representation
    def update(self, t, m):
        self.dist *= get_likelihood(self.omegas, t, m)
        self.normalize()


class DynamicDist(ParticleDist):
    name = 'dynamic_dist'
    size = NUM_PARTICLES
    def __init__(self, omegas, v1s, prior):
        assert omegas.shape + v1s.shape == prior.shape
        new_omegas = np.outer(omegas, np.ones(v1s.size)).flatten()
        new_v1s = np.outer(np.ones(omegas.size), v1s).flatten()
        
        chosen_indices = deterministic_sample(self.size, prior.flatten())
        self.omegas = new_omegas[chosen_indices]
        self.v1s = new_v1s[chosen_indices]
        self.dist = np.ones(self.size) / self.size
        self.target_cov = self.cov() # initialize target covariance to actual covariance
    def cov(self):
        return np.cov(np.stack([self.omegas, self.v1s]), ddof=0, aweights=self.dist)
    # TODO: nontrivial adaptation from other implementation here



def get_measurements(omega_list, ts):
    for omega, t in zip(omega_list, ts):
        yield np.random.binomial(1, prob_excited(t, omega))


def do_run(v1s, v1_prior, omegas, omega_prior, get_ts, get_v1, mk_est):
    estimator = mk_est(omegas, v1s, np.outer(omega_prior, v1_prior))
    ts, length = get_ts(estimator)
    
    v1_true = get_v1(v1s, v1_prior)
    omega_list_true = sample_omega_list(omegas, omega_prior, v1_true, length)
    ms = get_measurements(omega_list_true, ts)
    
    estimator.many_update(ts, ms)
    return estimator, v1_true, omega_list_true


def losses(estimator, v1_true, omega_list_true):
    loss_omega = (omega_list_true[-1] - estimator.mean_omega())**2 / v1_true    # normalize to get rid of scaling issues
    loss_v1 = (np.log(v1_true) - estimator.mean_log_v1())**2                    # log to get rid of scaling issues
    return loss_omega, loss_v1


def do_runs(v1s, v1_prior, omegas, omega_prior, get_ts, get_v1, mk_est, n_runs):
    loss_omegas, loss_v1s = np.zeros(n_runs), np.zeros(n_runs)
    for r in range(0, n_runs):
        loss_omegas[r], loss_v1s[r] = losses( *do_run(v1s, v1_prior, omegas,
            omega_prior, get_ts, get_v1, mk_est) )
    return loss_omegas, loss_v1s


def x_trace(v1s, v1_prior, omegas, omega_prior, get_get_ts, get_get_v1,
est_class, n_runs, x_list, x_list_nm):
    loss_omegas = np.zeros((len(x_list), n_runs))
    loss_v1s    = np.zeros((len(x_list), n_runs))
    for i, x in enumerate(x_list):
        print(i, '\t', x)
        loss_omegas[i], loss_v1s[i] = do_runs(v1s, v1_prior, omegas,
            omega_prior, get_get_ts(x), get_get_v1(x), est_class, n_runs)
    data = {
        'omega_min': omega_min,
        'omega_max': omega_max,
        'v_0': v_0,
        'omegas': omegas,
        'omega_prior': omega_prior,
        'x_list_nm': x_list_nm,
        'x_list': x_list,
        'estimator_name': est_class.name,
        'get_get_ts': inspect.getsource(get_get_ts),
        'get_get_v1': inspect.getsource(get_get_v1),
        'loss_omegas': loss_omegas,
        'loss_v1s': loss_v1s,
        'plottype': 'est_var_omega_%s' % x_list_nm,
        'estimator_params': get_numeric_class_vars(est_class),
    }
    save_data(data, get_filepath(data['plottype']))


def main():
    log_v1s = np.linspace(-12., -3., 63)
    v1s = np.exp(log_v1s)
    v1_prior = normalize(1. + 0.*v1s)
    omegas = np.linspace(omega_min, omega_max, 80)
    omega_prior = normalize(1. + 0.*omegas)
    
    whichthing = 0
    
    if whichthing == 1:
        def get_get_ts(x):
            def get_ts(est):
                l = 200
                return np.random.uniform(0., 4.*np.pi, l), l
            return get_ts
        def get_get_v1(x):
            def get_v1(v1s, v1_prior):
                return x
            return get_v1
        x_trace(v1s, v1_prior, omegas, omega_prior, get_get_ts, get_get_v1, GridDist, 500, [1e-6, 2e-6, 3e-6, 6e-6, 1e-5, 2e-5, 3e-5, 6e-5, 1e-4, 2e-4, 3e-4, 6e-4, 0.001], 'v1_true')
    
    if whichthing == 2:
        def get_get_ts(x):
            def get_ts(est):
                l = x
                return np.random.uniform(0., 4.*np.pi, l), l
            return get_ts
        def get_get_v1(x):
            def get_v1(v1s, v1_prior):
                return 0.0001
            return get_v1
        x_trace(v1s, v1_prior, omegas, omega_prior, get_get_ts, get_get_v1, GridDist, 100, [3, 6, 10, 20, 30, 60, 100, 200, 300, 600, 1000, 2000], 'n_measurements')
    
    
    if whichthing == 0:
        def get_ts(est):
            l = 2000
            return np.random.uniform(0., 4.*np.pi, l), l
        def get_v1(v1s, prior):
            return sample_dist(v1s, v1_prior)
        
        #grid = GridDist(omegas, v1s, np.outer(omega_prior, v1_prior))
        grid, v1_true, omega_list_true = do_run(v1s, v1_prior, omegas, omega_prior, get_ts, get_v1, GridDist)
        #grid.many_update(ts, ms)
        
        print(grid.dist[grid.dist<-0.001])
        print(grid.mean_omega(), omega_list_true[-1])
        print(np.exp(grid.mean_log_v1()), v1_true)
        
        if False:
            fig = plt.figure()
            ax = fig.add_subplot(111, projection='3d')
            X, Y = np.meshgrid(log_v1s, omegas)
            ax.plot_surface(X, Y, grid.dist, cmap=plt.get_cmap('inferno'))
        else:
            plt.imshow(grid.dist, cmap=plt.get_cmap('inferno'),
                interpolation='nearest', aspect='auto',
                extent=[np.log(grid.v1s)[0, 0], np.log(grid.v1s)[0, -1],
                        grid.omegas[0, 0], grid.omegas[-1, 0]] )
        plt.show()




if __name__ == '__main__':
    main()

