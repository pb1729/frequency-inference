import numpy as np
from matplotlib import pyplot as plt
from sys import argv
from util import load_data, Bunch

def plot_measure_time(b):
    for loss, var, nm in zip(b.avg_losses, b.avg_loss_vars, b.estimator_names):
        plt.errorbar(b.tlist, loss, yerr=np.sqrt(var), capsize=2, label=nm)
    #plt.ylim(bottom=0.0)
    plt.yscale('log')

def plot_measure_number(b):
    for loss, var, nm in zip(b.avg_losses, b.avg_loss_vars, b.estimator_names):
        plt.errorbar(b.nlist, loss, yerr=np.sqrt(var), capsize=2, label=nm)
    #plt.ylim(bottom=0.0)
    plt.yscale('log')
    plt.xscale('log')

def plot_shot_number(b):
    for loss, var, nm in zip(b.avg_losses, b.avg_loss_vars, b.estimator_names):
        plt.errorbar(b.nshots_list, loss, yerr=np.sqrt(var), capsize=2, label=nm)
    #plt.ylim(bottom=0.0)
    plt.yscale('log')
    plt.xscale('log')

def plot_t_theta_loss(b):
    for loss, var, nm in zip(b.avg_losses, b.avg_loss_vars, b.t_estimator_names):
        plt.errorbar(b.theta_list, loss, yerr=np.sqrt(var), capsize=2, label=nm)
    #plt.ylim(bottom=0.0)
    plt.yscale('log')

def plot_measurement_performance(b):
    for loss, var, nm in zip(b.avg_losses, b.avg_loss_vars, b.estimator_names):
        plt.errorbar(b.N_list, loss, yerr=np.sqrt(var), capsize=2, label=nm)
    #plt.ylim(bottom=0.0)
    plt.yscale('log')
    plt.xscale('log')

plotfns = {
    'measure_time': plot_measure_time,
    'measure_number': plot_measure_number,
    'shot_number': plot_shot_number,
    't_theta_loss': plot_t_theta_loss,
    'measurement_performance': plot_measurement_performance
}

def plot(data):
    plotfns[data['plottype']](Bunch(data))

def main():
    for filename in argv[1:]:
        plot(load_data(filename))
    plt.legend()
    plt.show()

if __name__ == '__main__':
    main()

