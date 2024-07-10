"""
Bayesian linear regression demo

Author: Sam Barba
Created 03/03/2022
"""

import matplotlib.pyplot as plt
import numpy as np
from sklearn.metrics import mean_absolute_error

import bayesian_utility


NUM_TRAIN = 14
NUM_VAL = NUM_TRAIN
NUM_TEST = 300
SIGMA = 0.3  # Noise = SIGMA ^ 2

plt.rcParams['figure.figsize'] = (9, 6)
plt.rcParams['mathtext.fontset'] = 'custom'
plt.rcParams['mathtext.it'] = 'Times New Roman:italic'


def plot_regression(approx_data, x_train, y_train, x_test, y_test, lam, lower_bounds=None, upper_bounds=None):
	plt.plot(x_test, y_test, '--', zorder=1, label='Ground truth')
	plt.scatter(x_train, y_train, color='black', zorder=2, label='Training samples')
	plt.plot(x_test, approx_data, zorder=3, label='Prediction')

	if lower_bounds is not None and upper_bounds is not None:
		plt.fill_between(
			x_test.squeeze(), lower_bounds, upper_bounds,
			color='tab:blue', alpha=0.2, zorder=0, label='Error'
		)
		plot_lim1 = lower_bounds.min() - 0.2
		plot_lim2 = upper_bounds.max() + 0.2
	else:
		plot_lim1 = np.append(y_train, y_test).min() - 0.2
		plot_lim2 = np.append(y_train, y_test).max() + 0.2

	plt.ylim(plot_lim1, plot_lim2)
	plt.xlabel('x')
	plt.ylabel('y')
	plt.title(
		fr'Regression with $\lambda$ = {lam:.4f}'
		'\n'
		fr'($\alpha$ = {(lam / SIGMA ** 2):.4f})'
	)
	plt.legend()
	plt.show()


def fit_pls(phi, y, lam):
	"""Partial least squares"""

	return np.linalg.inv(phi.T.dot(phi) + lam * np.eye(phi.shape[1])).dot(phi.T).dot(y)


def compute_posterior(phi, y, alpha, s2):
	"""
	Compute posterior mean (mu) and variance (sigma) for a Bayesian linear regression model with basis matrix
	phi and hyperparameters alpha and sigma^2, where lambda = alpha * sgima^2 (lambda = regularisation parameter)
	"""

	lam = alpha * s2
	mu = np.linalg.inv(phi.T.dot(phi) + lam * np.eye(phi.shape[1])).dot(phi.T).dot(y)
	sigma = s2 * np.linalg.inv(phi.T.dot(phi) + lam * np.eye(phi.shape[1]))
	return mu, sigma


def compute_log_marginal(phi, y, alpha, s2):
	"""
	Compute the logarithm of the marginal likelihood for a Bayesian linear regression model
	with basis matrix phi and hyperparameters alpha and sigma^2
	"""

	y = y.squeeze()
	n = phi.shape[0]
	lml1 = (2 * np.pi) ** (-n / 2) * np.linalg.det(s2 * np.eye(n) + phi.dot(phi.T) / alpha) ** -0.5
	lml2 = np.exp(-0.5 * y.T.dot(np.linalg.inv(s2 * np.eye(n) + phi.dot(phi.T) / alpha)).dot(y))
	return np.log(lml1 * lml2)


if __name__ == '__main__':
	# Synthesise datasets

	data_generator = bayesian_utility.DataGenerator(SIGMA ** 2)
	x_train, y_train = data_generator.get_data('TRAIN', NUM_TRAIN)
	x_val, y_val = data_generator.get_data('VALIDATION', NUM_VAL)
	x_test, y_test = data_generator.get_data('TEST', NUM_TEST)

	# Compute basis matrices for all 3 datasets - note that because a 'bias' function is used, we need n - 1
	# Gaussians to make the basis 'complete' (i.e. for m = n)

	m = NUM_TRAIN - 1
	centres = np.linspace(data_generator.x_min, data_generator.x_max, m)
	rbf_generator = bayesian_utility.RBFGenerator(centres=centres, radius=1)

	phi_train = rbf_generator.evaluate(x_train)
	phi_val = rbf_generator.evaluate(x_val)
	phi_test = rbf_generator.evaluate(x_test)

	# Plot regression for different lambda values
	for lam in [0, 0.01, 10]:
		w = fit_pls(phi_train, y_train, lam)
		approx_data = phi_test.dot(w)
		plot_regression(approx_data, x_train, y_train, x_test, y_test, lam)

	# Check consistency of fit_pls and compute_posterior
	# (let lambda = 0.01, so alpha = 0.01 / sigma^2)

	mu, _ = compute_posterior(phi_test, y_test, alpha=0.01 / SIGMA ** 2, s2=SIGMA ** 2)
	w = fit_pls(phi_test, y_test, lam=0.01)
	print('mu = PLS w:', all(mu == w))

	# Compute train, validation, and test set errors for the PLS model
	# - Also compute the negative log marginal likelihood (negative log evidence)
	# - Plot all curves on a graph

	v = np.linspace(-13, 5, 500)
	lam_vals = 10 ** v

	err_train = np.zeros(0)
	err_test = np.zeros(0)
	err_val = np.zeros(0)
	neg_log_evidence = np.zeros(0)

	for lam in lam_vals:
		w = fit_pls(phi_train, y_train, lam)
		train_pred = phi_train.dot(w)
		test_pred = phi_test.dot(w)
		val_pred = phi_val.dot(w)
		err_train = np.append(err_train, mean_absolute_error(y_train, train_pred))
		err_test = np.append(err_test, mean_absolute_error(y_test, test_pred))
		err_val = np.append(err_val, mean_absolute_error(y_val, val_pred))
		neg_log_evidence = np.append(
			neg_log_evidence,
			-compute_log_marginal(phi_train, y_train, lam / SIGMA ** 2, SIGMA ** 2)
		)

	ax1 = plt.subplot()
	ax2 = ax1.twinx()

	ax1.plot(v, err_train, label='Train')
	ax1.plot(v, err_test, '--', label='Test')
	ax1.plot(v, err_val, '--', label='Val')
	ax1.set_xlabel('log(lambda)')
	ax1.set_ylabel('MAE')
	ax1.legend(loc='center left')

	ax2.plot(v, neg_log_evidence, color='tab:green', label='Train')
	ax2.yaxis.label.set_color('tab:green')
	ax2.tick_params(axis='y', colors='tab:green')
	ax2.set_ylabel('-log(evidence)')
	ax2.legend(loc='center right')

	plt.show()

	min_err_val_idx = err_val.argmin()
	min_neg_log_evidence_idx = neg_log_evidence.argmin()

	print('\nMin point on test curve:', min(err_test))
	print('Point on test curve corresponding to min of val curve:', err_test[min_err_val_idx])
	print('Point on test curve corresponding to min of neg log evidence curve:', err_test[min_neg_log_evidence_idx])

	# Plotting regression with optimal lambda including 'error bars'
	# The predictive variance is sum of:
	# - Uncertainty due to noise (sigma^2)
	# - Uncertainty due to the parameter estimate being imprecise, encapsulated by posterior covariance sigma

	best_lam = 10 ** v[min_neg_log_evidence_idx]
	best_alpha = best_lam / SIGMA ** 2
	print('\nOptimal lambda =', best_lam)
	print('Optimal alpha =', best_alpha)

	mu, sigma = compute_posterior(phi_train, y_train, alpha=best_alpha, s2=SIGMA ** 2)
	y_posterior = phi_test.dot(mu).squeeze()
	var_matrix = SIGMA ** 2 + phi_test.dot(sigma).dot(phi_test.T)
	var_matrix = var_matrix.diagonal()
	sd = var_matrix ** 0.5
	lower_bounds = y_posterior - sd
	upper_bounds = y_posterior + sd

	plot_regression(y_posterior, x_train, y_train, x_test, y_test, best_lam, lower_bounds, upper_bounds)

	# Print log marginal likelihood given optimal lambda and alpha
	print(f'\nLog marginal likelihood with sigma^2 = {SIGMA ** 2}, lambda = optimal, alpha = optimal:')
	print(compute_log_marginal(phi_train, y_train, best_alpha, SIGMA ** 2))
