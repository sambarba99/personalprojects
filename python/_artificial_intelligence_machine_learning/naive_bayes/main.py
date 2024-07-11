"""
Naive Bayes classification demo

Author: Sam Barba
Created 21/11/2021
"""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import f1_score

from _utils.csv_data_loader import load_csv_classification_data
from _utils.model_evaluation_plots import plot_confusion_matrix, plot_roc_curve
from naive_bayes_classifier import NaiveBayesClassifier


pd.set_option('display.max_columns', 12)
pd.set_option('display.width', None)


if __name__ == '__main__':
	choice = input(
		'\nEnter 1 to use banknote dataset,'
		'\n2 for breast tumour dataset,'
		'\n3 for glass dataset,'
		'\n4 for iris dataset,'
		'\n5 for mushroom dataset,'
		'\n6 for pulsar dataset,'
		'\n7 for Titanic dataset,'
		'\nor 8 for wine dataset\n>>> '
	)

	match choice:
		case '1': path = 'C:/Users/Sam/Desktop/projects/datasets/banknote_authenticity.csv'
		case '2': path = 'C:/Users/Sam/Desktop/projects/datasets/breast_tumour_pathology.csv'
		case '3': path = 'C:/Users/Sam/Desktop/projects/datasets/glass_classification.csv'
		case '4': path = 'C:/Users/Sam/Desktop/projects/datasets/iris_classification.csv'
		case '5': path = 'C:/Users/Sam/Desktop/projects/datasets/mushroom_edibility_classification.csv'
		case '6': path = 'C:/Users/Sam/Desktop/projects/datasets/pulsar_identification.csv'
		case '7': path = 'C:/Users/Sam/Desktop/projects/datasets/titanic_survivals.csv'
		case _: path = 'C:/Users/Sam/Desktop/projects/datasets/wine_classification.csv'

	x_train, y_train, x_test, y_test, labels, _ = load_csv_classification_data(path, train_size=0.8, test_size=0.2)

	clf = NaiveBayesClassifier()
	clf.fit(x_train, y_train)

	test_pred_probs = clf.predict(x_test)
	test_pred_labels = test_pred_probs.argmax(axis=1)

	# Confusion matrix
	f1 = f1_score(y_test, test_pred_labels, average='binary' if len(labels) == 2 else 'weighted')
	plot_confusion_matrix(y_test, test_pred_labels, labels, f'Test confusion matrix\n(F1 score: {f1:.3f})')

	# ROC curve
	if len(labels) == 2:  # Binary classification
		plot_roc_curve(y_test, test_pred_probs[:, 1])  # Assuming 1 is the positive class
