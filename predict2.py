from train2 import *
import matplotlib.pyplot as plt


import os, torch
import scipy as sp


class HyperPara:
    star_id = 100
    teff = 4806.
    teff_sig = 100
    numax = 203.
    numax_sig = 3.6
    dnu = 15.6
    dnu_sig = 0.13
    fe_h = 0.05
    fe_h_sig = 0.1
    luminosity = 9.14
    luminosity_sig = 0.33
    output_fig = True
    num_samples = 50000
    star_type = '/best_model_ms_new.torchmodel'


numax_scale = 3500.
dnu_scale = 150.
teff_scale = 5777.
luminosy_scale = 1.

def infer(HyperPara):
    # Get cpu or gpu device for training.
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using {device} device")

    #training the model
    #go to another convention
    package_dir = os.path.dirname(os.path.abspath(__file__))

    print(HyperPara.star_type)

    saved_model_dict = package_dir + HyperPara.star_type

    trained_model = StarNetwork(hidden_size=512, num_gaussians=16).to(device)



    trained_model.load_state_dict(torch.load(saved_model_dict))
    trained_model.eval()

    select_numax = torch.Tensor([HyperPara.numax / numax_scale]).float().to(device)
    select_numax_sigma = torch.Tensor([HyperPara.numax_sig * 100. / HyperPara.numax]).float().to(device)
    select_dnu = torch.Tensor([HyperPara.dnu / dnu_scale]).float().to(device)
    select_dnu_sigma = torch.Tensor([HyperPara.dnu_sig * 100. / HyperPara.dnu]).float().to(device)
    select_teff = torch.Tensor([HyperPara.teff / teff_scale]).float().to(device)
    select_teff_sigma = torch.Tensor([HyperPara.teff_sig / teff_scale * 100./HyperPara.teff]).float().to(device)
    select_fe_h = torch.Tensor([HyperPara.fe_h]).float().to(device)
    select_fe_h_sigma = torch.Tensor([HyperPara.fe_h_sig]).float().to(device)
    select_luminosity = torch.Tensor([HyperPara.luminosity]).float().to(device)
    select_luminosity_sigma = torch.Tensor([HyperPara.luminosity_sig]).float().to(device)

    select_pi, select_sigma, select_mu = trained_model(input_numax=select_numax,
                                                       input_teff=select_teff, input_fe_h=select_fe_h,
                                                       input_delta_nu=select_dnu, input_lum=select_luminosity,
                                                       input_numax_sigma= select_numax_sigma,
                                                       input_teff_sigma= select_teff_sigma,
                                                       input_fe_h_sigma=select_fe_h_sigma,
                                                       input_dnu_sigma=select_dnu_sigma,
                                                       input_lum_sigma=select_luminosity_sigma)

    output_params = ['mass', 'age', 'hydrogen', 'metallicity', 'alpha', 'radii']
    output_pi, output_sigma, output_mu, output_grid, output_median, output_conf_interval, output_pdf = [], [], [], [], [], [], []
    output_median, output_low_err, output_up_err = [], [], []

    print('--------- RESULTS ---------')
    for i, params in enumerate(output_params):
        param_pi = select_pi.data.cpu().numpy().squeeze()
        param_sigma = select_sigma[:, :, i].data.cpu().numpy().squeeze()
        param_mu = select_mu[:, :, i].data.cpu().numpy().squeeze()

        if params in ['metallicity']:
            param_mu = np.exp(param_mu)
            param_sigma = np.exp(param_sigma)

        param_grid = np.arange(np.min(param_mu.squeeze()) - 10 * param_sigma.squeeze()[np.argmin(param_mu.squeeze())],
                               np.max(param_mu.squeeze()) + 10 * param_sigma.squeeze()[np.argmax(param_mu.squeeze())],
                               0.0001)
        param_pdf = mix_pdf(param_grid, param_mu.squeeze(), param_sigma.squeeze(), param_pi.squeeze())
        param_cumsum_grid = np.cumsum(param_pdf) / (np.sum(param_pdf))
        param_quartile_vec = param_grid[np.argmin(np.abs(param_cumsum_grid - 0.16))]
        param_median_vec = param_grid[np.argmin(np.abs(param_cumsum_grid - 0.5))]
        param_third_quartile_vec = param_grid[np.argmin(np.abs(param_cumsum_grid - 0.83))]
        param_mean = dist_mu_npy(param_pi.reshape(1, -1), param_mu.reshape(1, -1))

        print(params + ': ' + '%.3f +%.3f -%.3f' % (
        param_median_vec, param_third_quartile_vec - param_median_vec, param_median_vec - param_quartile_vec))

        output_pi.append(param_pi)
        output_sigma.append(param_sigma)
        output_mu.append(param_mu)
        output_grid.append(param_grid)
        output_median.append(param_median_vec)
        output_conf_interval.append([param_quartile_vec, param_third_quartile_vec])
        output_pdf.append(param_pdf)
        output_low_err.append(param_median_vec - param_quartile_vec)
        output_up_err.append(param_third_quartile_vec - param_median_vec)

    if HyperPara.output_fig:
        plot_fig(output_pi, output_mu, output_sigma, output_grid, output_median, output_conf_interval, output_pdf)

    return output_median,  output_up_err, output_low_err


def plot_fig(par_pi, par_mus, par_sigmas, output_grid, output_median, output_conf_interval, output_pdf):
    fig = plt.figure(figsize=(25, 10))
    par_name = ['$M$', '$\\tau$', '$X_0$', '$Z_0$', '$\\alpha_{\\mathrm{MLT}}$', '$R$', '$L$']
    par_units = ['$M_{\\odot}$', 'Gyr', '', '', '', '$R_{\\odot}$', '$L_{\\odot}$']

    for i in range(len(par_mus)):
        exec("ax%d = fig.add_subplot(2,5,%d)" % (i + 1, i + 1))
        exec("ax%d.tick_params(width=5)" % (i + 1))
        for axis in ['top', 'bottom', 'left', 'right']:
            exec("ax%d.spines[axis].set_linewidth(2)" % (i + 1))

        exec("ax%d.plot(output_grid[i], output_pdf[i], c='k')" % (i + 1))
        exec("ax%d.text(x=0.75, y=0.9, s=par_name[i], transform = ax%d.transAxes, fontsize=27)" % (i + 1, i + 1))

        if i == 0:
            exec(
                "ax%d.set_xlim([max(0,output_median[i] - 7*np.median(par_sigmas[i])), output_median[i] + 7*np.median(par_sigmas[i])])" % (
                            i + 1))
        elif i == 4:
            exec(
                "ax%d.set_xlim([max(0,output_median[i] - 8*np.median(par_sigmas[i])), output_median[i] + 8*np.median(par_sigmas[i])])" % (
                            i + 1))

        elif i == 2:
            exec(
                "ax%d.set_xlim([max(0,output_median[i] - 5*np.median(par_sigmas[i])), output_median[i] + 5*np.median(par_sigmas[i])])" % (
                            i + 1))

        else:
            exec(
                "ax%d.set_xlim([max(0,output_median[i] - 5*np.median(par_sigmas[i])), output_median[i] + 5*np.median(par_sigmas[i])])" % (
                            i + 1))
            if i == 3:
                pass

        exec("ax%d.set_xlabel(par_units[i], fontsize=27)" % (i + 1))

        exec("ax%d.set_yticklabels([])" % (i + 1))
        exec("ax%d.tick_params(axis='x', labelsize=30)" % (i + 1))

        if i in [5, 6, 7]:
            exec("ax%d.set_xscale('log')" % (i + 1))
            if i != 6:
                exec("ax%d.set_xlim([1e-4, 1])" % (i + 1))
            else:
                exec("ax%d.set_xlim([1e-4, 3])" % (i + 1))
            exec("ax%d.vlines(x=output_conf_interval[i], ymin=[-0.05,-0.05],\
        ymax= [1e6, 1e6],\
          linestyles='dotted', lw=3)" % (i + 1))
            exec("ax%d.set_ylim([-0.05, np.max(output_pdf[i]) + 10])" % (i + 1))
            exec("ax%d.set_xticks([1e-4, 1e-2, 1])" % (i + 1))

            exec("ax%d.vlines(x=output_median[i], linestyles='dashed', ymin=-0.05,\
    ymax = 1e6)" % (i + 1))
        else:
            exec("ax%d.vlines(x=output_conf_interval[i], ymin=[-0.05,-0.05],\
    ymax=[output_pdf[i][np.argmin(np.abs(output_grid[i]-output_conf_interval[i][0]))],\
    output_pdf[i][np.argmin(np.abs(output_grid[i]-output_conf_interval[i][1]))]],\
          linestyles='dotted', lw=3)" % (i + 1))
            exec("ax%d.set_ylim([-0.05, 1.1*np.max(output_pdf[i])])" % (i + 1))
            exec("ax%d.vlines(x=output_median[i], linestyles='dashed', ymin=-0.05,\
    ymax = output_pdf[i][np.argmin(np.abs(output_grid[i]-output_median[i]))], lw=3)" % (i + 1))

    fig.add_subplot(111, frameon=False)
    # hide tick and tick label of the big axes
    plt.tick_params(labelcolor='none', top='off', bottom='off', left='off', right='off')
    plt.grid(False)
    plt.ylabel("Density", fontsize=30)
    plt.tight_layout(w_pad=0.25)
    plt.savefig('results.png')
    plt.close()


if __name__ == '__main__':
    infer(HyperPara)





