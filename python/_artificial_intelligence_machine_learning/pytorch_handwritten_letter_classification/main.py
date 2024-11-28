"""
PyTorch CNN for handwritten letter classification

Author: Sam Barba
Created 28/11/2024
"""

import os

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pygame as pg
from sklearn.metrics import f1_score
from sklearn.model_selection import train_test_split
import torch
from torch.utils.data import DataLoader
from tqdm import tqdm

from _utils.custom_dataset import CustomDataset
from _utils.early_stopping import EarlyStopping
from _utils.model_architecture_plots import plot_model
from _utils.model_evaluation_plots import plot_cnn_learned_filters, plot_cnn_feature_maps, plot_confusion_matrix
from conv_net import CNN


torch.manual_seed(1)

INPUT_SHAPE = (1, 28, 28)  # Colour channels, H, W
BATCH_SIZE = 256
NUM_EPOCHS = 50
DRAWING_CELL_SIZE = 15
DRAWING_SIZE = DRAWING_CELL_SIZE * 28


def load_data():
	df = pd.read_csv('C:/Users/Sam/Desktop/projects/datasets/handwritten_letters.csv')

	x, y = df.iloc[:, 1:].to_numpy(dtype=float), df.iloc[:, 0].to_numpy()

	# Reshape images, normalise to [0,1], and add channel dim
	x = x.reshape((-1, 28, 28)) / 255
	x = np.expand_dims(x, 1)

	# One-hot encode y
	y = np.eye(26)[y]  # 26 classes (A-Z)

	x, y = torch.tensor(x).float(), torch.tensor(y).float()

	# Create train/validation/test sets (ratio 0.98:0.01:0.01)
	x_train_val, x_test, y_train_val, y_test = train_test_split(x, y, train_size=0.99, stratify=y, random_state=1)
	x_train, x_val, y_train, y_val = train_test_split(x_train_val, y_train_val, train_size=0.99, stratify=y_train_val, random_state=1)

	train_set = CustomDataset(x_train, y_train)
	train_loader = DataLoader(train_set, batch_size=BATCH_SIZE, shuffle=False)

	return train_loader, x_val, y_val, x_test, y_test


if __name__ == '__main__':
	# Prepare data

	train_loader, x_val, y_val, x_test, y_test = load_data()

	# Define model

	model = CNN()
	print(f'\nModel:\n{model}\n')
	plot_model(model, INPUT_SHAPE)
	model.to('cpu')

	loss_func = torch.nn.CrossEntropyLoss()

	if os.path.exists('./model.pth'):
		model.load_state_dict(torch.load('./model.pth'))
	else:
		# Plot some example images

		_, axes = plt.subplots(nrows=8, ncols=8, figsize=(5, 5))
		plt.subplots_adjust(left=0.05, right=0.95, top=0.9, bottom=0.05, hspace=0.05, wspace=0.05)
		for idx, ax in enumerate(axes.flatten()):
			sample = x_val[idx].squeeze()
			ax.imshow(sample, cmap='gray')
			ax.axis('off')
		plt.suptitle('Data samples', y=0.95)
		plt.show()

		# Train model

		print('----- TRAINING -----\n')

		optimiser = torch.optim.Adam(model.parameters())  # LR = 1e-3
		early_stopping = EarlyStopping(patience=5, min_delta=0, mode='max')

		for epoch in range(1, NUM_EPOCHS + 1):
			progress_bar = tqdm(range(len(train_loader)), unit='batches', ascii=True)
			model.train()

			for x_train, y_train in train_loader:
				progress_bar.update()
				progress_bar.set_description(f'Epoch {epoch}/{NUM_EPOCHS}')

				y_train_logits = model(x_train)
				loss = loss_func(y_train_logits, y_train)

				optimiser.zero_grad()
				loss.backward()
				optimiser.step()

				progress_bar.set_postfix_str(f'loss={loss.item():.4f}')

			model.eval()
			with torch.inference_mode():
				y_val_logits = model(x_val)
			val_loss = loss_func(y_val_logits, y_val).item()
			val_f1 = f1_score(y_val.argmax(dim=1), y_val_logits.argmax(dim=1), average='weighted')
			progress_bar.set_postfix_str(f'val_loss={val_loss:.4f}, val_F1={val_f1:.4f}')
			progress_bar.close()

			if early_stopping(val_f1, model.state_dict()):
				print('Early stopping at epoch', epoch)
				break

		model.load_state_dict(early_stopping.best_weights)  # Restore best weights
		torch.save(model.state_dict(), './model.pth')

	# Plot the model's learned filters
	plot_cnn_learned_filters(model, num_cols=4, figsize=(9, 4))

	# Test model

	print('\n----- TESTING -----\n')

	model.eval()
	with torch.inference_mode():
		y_test_logits = model(x_test)
	test_pred = y_test_logits.argmax(dim=1)
	test_loss = loss_func(y_test_logits, y_test)
	print(f'Test loss: {test_loss.item()}\n')

	# Confusion matrix
	f1 = f1_score(y_test.argmax(dim=1), test_pred, average='weighted')
	labels = [chr(i) for i in range(65, 91)]
	plot_confusion_matrix(y_test.argmax(dim=1), test_pred, labels, f'Test confusion matrix\n(F1 score: {f1:.3f})')

	# User draws a letter to predict

	pg.init()
	pg.display.set_caption('Draw a letter!')
	scene = pg.display.set_mode((DRAWING_SIZE, DRAWING_SIZE))
	font = pg.font.SysFont('consolas', 16)
	user_drawing_coords = np.zeros((0, 2))
	model_input = torch.zeros(INPUT_SHAPE)
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
						user_drawing_coords = np.append(user_drawing_coords, [[x, y]], axis=0)
				case pg.MOUSEMOTION:
					if left_btn_down:
						x, y = event.pos
						user_drawing_coords = np.append(user_drawing_coords, [[x, y]], axis=0)
				case pg.MOUSEBUTTONUP:
					if event.button == 1:
						left_btn_down = False

		if not left_btn_down:
			continue

		# Map coords to range [0,27]
		pixelated_coords = user_drawing_coords * 27 / DRAWING_SIZE
		pixelated_coords = np.unique(np.round(pixelated_coords), axis=0).astype(int)  # Keep only unique coords
		pixelated_coords = np.clip(pixelated_coords, 0, 27)

		# Set these pixels as bright
		model_input[:, pixelated_coords[:, 1], pixelated_coords[:, 0]] = 1

		# Add some edge blurring
		for x, y in pixelated_coords:
			for dx, dy in [(0, -1), (1, 0), (0, 1), (-1, 0)]:
				if 0 <= x + dx <= 27 and 0 <= y + dy <= 27 and model_input[:, y + dy, x + dx] == 0:
					model_input[:, y + dy, x + dx] = np.random.uniform(0.33, 1)

		with torch.inference_mode():
			pred_logits = model(model_input.unsqueeze(dim=0))
		pred_probs = torch.softmax(pred_logits, dim=-1)

		for y in range(28):
			for x in range(28):
				colour = round(255 * model_input[0, y, x].item())
				pg.draw.rect(
					scene,
					(colour, colour, colour),
					pg.Rect(x * DRAWING_CELL_SIZE, y * DRAWING_CELL_SIZE, DRAWING_CELL_SIZE, DRAWING_CELL_SIZE)
				)

		pred_letter = chr(65 + pred_probs.argmax().item())
		pred_lbl = font.render(f'{pred_letter} ({(100 * pred_probs.max()):.1f}% sure)', True, 'green')
		scene.blit(pred_lbl, (10, 10))

		pg.display.update()

	# Plot feature maps of user-drawn letter
	plot_cnn_feature_maps(model, num_cols=4, input_img=model_input, title_append=' (user-drawn letter)', figsize=(9, 4))