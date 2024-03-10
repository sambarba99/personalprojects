"""
PyTorch MNIST convolutional neural network

Author: Sam Barba
Created 30/10/2022
"""

import os

import matplotlib.pyplot as plt
import numpy as np
import pygame as pg
from sklearn.metrics import confusion_matrix, ConfusionMatrixDisplay, f1_score
from sklearn.model_selection import train_test_split
from tensorflow.keras.datasets import mnist  # Faster to use TF than torchvision
import torch
from torch.utils.data import DataLoader

from conv_net import CNN
from early_stopping import EarlyStopping
from mnist_dataset import MNISTDataset


os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'  # Reduce tensorflow log spam
torch.manual_seed(1)

INPUT_SHAPE = (1, 28, 28)  # Colour channels, H, W
N_EPOCHS = 100
BATCH_SIZE = 256
LEARNING_RATE = 1e-4
DRAWING_SIZE = 500


def load_data():
	(x_train, y_train), (x_test, y_test) = mnist.load_data()

	# Normalise images to [0,1] and correct shape
	x = np.concatenate([x_train, x_test], axis=0).astype(float) / 255
	x = np.reshape(x, (len(x), *INPUT_SHAPE))

	# One-hot encode y
	y = np.concatenate([y_train, y_test])
	y = np.eye(10)[y]  # 10 classes (0-9)

	# Train:validation:test ratio of 0.8:0.1:0.1
	x_train_val, x_test, y_train_val, y_test = train_test_split(x, y, train_size=0.89, stratify=y, random_state=1)
	x_train, x_val, y_train, y_val = train_test_split(x_train_val, y_train_val, train_size=0.89, stratify=y_train_val, random_state=1)

	# Convert to tensors
	x_val, y_val, x_test, y_test = map(
		lambda arr: torch.from_numpy(arr).float(),
		[x_val, y_val, x_test, y_test]
	)

	train_set = MNISTDataset(x_train, y_train)
	train_loader = DataLoader(train_set, batch_size=BATCH_SIZE, shuffle=False, num_workers=8)

	return train_loader, x_val, y_val, x_test, y_test


if __name__ == '__main__':
	train_loader, x_val, y_val, x_test, y_test = load_data()

	model = CNN()
	print(f'\nModel:\n{model}')

	loss_func = torch.nn.CrossEntropyLoss()

	if os.path.exists('./model.pth'):
		model.load_state_dict(torch.load('./model.pth'))
	else:
		# Plot some example images

		_, axes = plt.subplots(nrows=5, ncols=5, figsize=(5, 5))
		plt.subplots_adjust(left=0.05, right=0.95, top=0.9, bottom=0.05, hspace=0.05, wspace=0.05)
		for idx, ax in enumerate(axes.flatten()):
			sample = x_val[idx].squeeze()
			ax.imshow(sample, cmap='gray')
			ax.axis('off')
		plt.suptitle('Data samples', y=0.95)
		plt.show()

		# Train model

		print('\n----- TRAINING -----\n')

		optimiser = torch.optim.Adam(model.parameters(), lr=LEARNING_RATE)
		early_stopping = EarlyStopping(patience=10, min_delta=0, mode='max')
		history = {'loss': [], 'F1': [], 'val_loss': [], 'val_F1': []}

		for epoch in range(1, N_EPOCHS + 1):
			total_loss = total_f1 = 0
			model.train()

			for x, y in train_loader:
				y_probs = model(x).squeeze()
				y_pred = y_probs.argmax(dim=1)

				loss = loss_func(y_probs, y)
				f1 = f1_score(y.argmax(dim=1), y_pred, average='weighted')
				total_loss += loss.item()
				total_f1 += f1

				optimiser.zero_grad()
				loss.backward()
				optimiser.step()

			model.eval()
			with torch.inference_mode():
				y_val_probs = model(x_val).squeeze()
			y_val_pred = y_val_probs.argmax(dim=1)
			val_loss = loss_func(y_val_probs, y_val).item()
			val_f1 = f1_score(y_val.argmax(dim=1), y_val_pred, average='weighted')

			history['loss'].append(total_loss / len(train_loader))
			history['F1'].append(total_f1 / len(train_loader))
			history['val_loss'].append(val_loss)
			history['val_F1'].append(val_f1)

			print(f'Epoch {epoch}/{N_EPOCHS} | '
				f'Loss: {total_loss / len(train_loader)} | '
				f'F1: {total_f1 / len(train_loader)} | '
				f'Val loss: {val_loss} | '
				f'Val F1: {val_f1}')

			if early_stopping(val_f1, model.state_dict()):
				print('Early stopping at epoch', epoch)
				break

		model.load_state_dict(early_stopping.best_weights)  # Restore best weights
		torch.save(model.state_dict(), './model.pth')

		# Plot loss and F1 throughout training
		_, (ax_loss, ax_f1) = plt.subplots(nrows=2, sharex=True, figsize=(8, 5))
		ax_loss.plot(history['loss'], label='Training loss')
		ax_loss.plot(history['val_loss'], label='Validation loss')
		ax_f1.plot(history['F1'], label='Training F1')
		ax_f1.plot(history['val_F1'], label='Validation F1')
		ax_loss.set_ylabel('Categorical\ncross-entropy')
		ax_f1.set_ylabel('F1')
		ax_f1.set_xlabel('Epoch')
		ax_loss.legend()
		ax_f1.legend()
		plt.title('Model loss and F1 score during training', y=2.24)
		plt.show()

	# Testing

	print('\n----- TESTING -----\n')

	model.eval()
	with torch.inference_mode():
		y_test_probs = model(x_test).squeeze()
	test_pred = y_test_probs.argmax(dim=1)
	test_loss = loss_func(y_test_probs, y_test)
	print('Test loss:', test_loss.item())

	# Confusion matrix

	f1 = f1_score(y_test.argmax(dim=1), test_pred, average='weighted')
	cm = confusion_matrix(y_test.argmax(dim=1), test_pred)
	ConfusionMatrixDisplay(confusion_matrix=cm).plot(cmap='Blues')
	plt.title(f'Test confusion matrix\n(F1 score: {f1:.3f})')
	plt.show()

	# User draws a digit to predict

	pg.init()
	pg.display.set_caption('Draw a digit!')
	scene = pg.display.set_mode((DRAWING_SIZE, DRAWING_SIZE))
	user_drawing_coords = []
	drawing = True
	left_btn_down = False

	while drawing:
		for event in pg.event.get():
			match event.type:
				case pg.QUIT:
					drawing = False
					pg.quit()
				case pg.MOUSEBUTTONDOWN:
					if event.button == 1:
						left_btn_down = True
						x, y = event.pos
						user_drawing_coords.append([x, y])
						scene.set_at((x, y), (255, 255, 255))
						pg.display.update()
				case pg.MOUSEMOTION:
					if left_btn_down:
						x, y = event.pos
						user_drawing_coords.append([x, y])
						scene.set_at((x, y), (255, 255, 255))
						pg.display.update()
				case pg.MOUSEBUTTONUP:
					if event.button == 1:
						left_btn_down = False

	user_drawing_coords = np.array(user_drawing_coords) // (DRAWING_SIZE // 27)  # Make coords range from 0-27
	user_drawing_coords = np.unique(user_drawing_coords, axis=0)  # Keep unique pairs only
	drawn_digit_grid = torch.zeros((28, 28))
	drawn_digit_grid[user_drawing_coords[:, 1], user_drawing_coords[:, 0]] = 1
	drawn_digit_input = drawn_digit_grid.reshape((1, *INPUT_SHAPE))
	with torch.inference_mode():
		pred_vector = model(drawn_digit_input).squeeze()

	plt.imshow(drawn_digit_grid, cmap='gray')
	plt.title(f'Drawn digit is {pred_vector.argmax()} ({(100 * pred_vector.max()):.1f}% sure)')
	plt.axis('off')
	plt.show()
