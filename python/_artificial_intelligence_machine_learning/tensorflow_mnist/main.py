"""
TensorFlow MNIST convolutional neural network

Author: Sam Barba
Created 20/10/2021
"""

import os

from keras.layers import Conv2D, Dense, Dropout, Flatten, Input, LeakyReLU, MaxPooling2D
from keras.models import load_model, Model, Sequential
from keras.utils.vis_utils import plot_model
import matplotlib.pyplot as plt
import numpy as np
import pygame as pg
from sklearn.metrics import f1_score
from sklearn.model_selection import train_test_split
import tensorflow as tf
from tensorflow.keras.datasets import mnist

from _utils.model_evaluation_plots import plot_confusion_matrix


os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'  # Reduce tensorflow log spam
tf.random.set_seed(1)

INPUT_SHAPE = (28, 28, 1)  # H, W, colour channels
BATCH_SIZE = 256
NUM_EPOCHS = 50
DRAWING_CELL_SIZE = 15
DRAWING_SIZE = DRAWING_CELL_SIZE * 28


def load_data():
	(x_train, y_train), (x_test, y_test) = mnist.load_data()

	# Normalise images to [0,1] and correct shape
	x = np.concatenate([x_train, x_test], axis=0).astype(float) / 255
	x = np.reshape(x, (len(x), *INPUT_SHAPE))

	# One-hot encode y
	y = np.concatenate([y_train, y_test])
	y = np.eye(10)[y]  # 10 classes (0-9)

	# Create train/validation/test sets (ratio 0.96:0.02:0.02)
	x_train_val, x_test, y_train_val, y_test = train_test_split(x, y, train_size=0.98, stratify=y, random_state=1)
	x_train, x_val, y_train, y_val = train_test_split(x_train_val, y_train_val, train_size=0.98, stratify=y_train_val, random_state=1)

	return x_train, y_train, x_val, y_val, x_test, y_test


def build_model():
	model = Sequential(
		layers=[
			Input(shape=INPUT_SHAPE),
			Conv2D(8, kernel_size=3),   # -> (N, 26, 26, 8)
			LeakyReLU(alpha=1e-2),
			MaxPooling2D(),  # 2          -> (N, 13, 13, 8)
			Conv2D(16, kernel_size=3),  # -> (N, 11, 11, 16)
			LeakyReLU(alpha=1e-2),
			MaxPooling2D(),             # -> (N, 5, 5, 16)
			Flatten(),                  # -> (N, 400)
			Dropout(0.5),
			Dense(64),
			LeakyReLU(alpha=1e-2),
			Dense(10, activation='softmax')
		],
		name='digit_recognition_model'
	)

	model.compile(loss='categorical_crossentropy', optimizer='adam', metrics=['accuracy'])  # LR = 1e-3
	model.build(input_shape=INPUT_SHAPE)

	return model


if __name__ == '__main__':
	# 1. Prepare data

	x_train, y_train, x_val, y_val, x_test, y_test = load_data()

	if os.path.exists('./model.h5'):
		model = load_model('./model.h5')
	else:
		# 2. Plot some example images

		_, axes = plt.subplots(nrows=5, ncols=5, figsize=(5, 5))
		plt.subplots_adjust(left=0.05, right=0.95, top=0.9, bottom=0.05, hspace=0.05, wspace=0.05)
		for idx, ax in enumerate(axes.flatten()):
			sample = x_train[idx].squeeze()
			ax.imshow(sample, cmap='gray')
			ax.axis('off')
		plt.suptitle('Data samples', y=0.95)
		plt.show()

		# 3. Define model

		model = build_model()
		model.summary()
		plot_model(
			model,
			to_file='./images/model_architecture.png',
			show_shapes=True,
			show_dtype=True,
			expand_nested=True,
			show_layer_activations=True
		)

		# 4. Train model

		print('\n----- TRAINING -----\n')

		early_stopping = tf.keras.callbacks.EarlyStopping(
			patience=5,
			restore_best_weights=True,
			monitor='val_accuracy',
			mode='max'
		)

		history = model.fit(
			x_train, y_train,
			epochs=NUM_EPOCHS,
			batch_size=BATCH_SIZE,
			validation_data=(x_val, y_val),
			callbacks=[early_stopping],
			verbose=1
		)

		# Plot loss and accuracy throughout training
		_, (ax_loss, ax_accuracy) = plt.subplots(nrows=2, sharex=True, figsize=(8, 5))
		ax_loss.plot(history.history['loss'], label='Training loss')
		ax_loss.plot(history.history['val_loss'], label='Validation loss')
		ax_accuracy.plot(history.history['accuracy'], label='Training accuracy')
		ax_accuracy.plot(history.history['val_accuracy'], label='Validation accuracy')
		ax_loss.set_ylabel('Categorical\ncross-entropy')
		ax_accuracy.set_ylabel('Accuracy')
		ax_accuracy.set_xlabel('Epoch')
		ax_loss.legend()
		ax_accuracy.legend()
		plt.title('Model loss and accuracy during training', y=2.24)
		plt.show()

		model.save('./model.h5')

	# 5. Evaluate model

	print('\n----- EVALUATION -----\n')
	test_loss, test_accuracy = model.evaluate(x_test, y_test, verbose=0)
	print('Test loss:', test_loss)
	print(f'Test accuracy: {test_accuracy}\n')

	# Confusion matrix
	test_pred = model.predict(x_test, verbose=0).argmax(axis=1)
	f1 = f1_score(y_test.argmax(axis=1), test_pred, average='weighted')
	plot_confusion_matrix(y_test.argmax(axis=1), test_pred, None, f'Test confusion matrix\n(F1 score: {f1:.3f})')

	# 6. Plot the learned conv layer filters

	conv_layer_indices = [
		idx for idx, layer_name in
		enumerate([layer.name for layer in model.layers])
		if 'conv' in layer_name
	]

	for idx, conv_idx in enumerate(conv_layer_indices, start=1):
		layer = model.layers[conv_idx]
		filters, biases = layer.get_weights()
		num_filters = filters.shape[-1]
		rows = num_filters // 4  # Works because num_filters is 8 for 1st conv layer, 16 for 2nd one
		cols = num_filters // rows

		print(f'Layer name: {layer.name} | Filters shape: {filters.shape} | Biases shape: {biases.shape}')

		_, axes = plt.subplots(nrows=rows, ncols=cols, figsize=(8, 5))
		for ax_idx, ax in enumerate(axes.flatten()):
			channel_mean = filters[..., ax_idx].mean(axis=2)  # Mean of this filter across the channel dimension (2)
			ax.imshow(channel_mean, cmap='gray')
			ax.axis('off')
		plt.suptitle(f'Filters of conv layer {idx}/{len(conv_layer_indices)}', x=0.512, y=0.94)
		plt.gcf().set_facecolor('#80b0f0')
		plt.show()

	# 7. User draws a digit to predict

	pg.init()
	pg.display.set_caption('Draw a digit!')
	scene = pg.display.set_mode((DRAWING_SIZE, DRAWING_SIZE))
	font = pg.font.SysFont('consolas', 16)
	user_drawing_coords = np.zeros((0, 2))
	model_input = np.zeros(INPUT_SHAPE)
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
		model_input[pixelated_coords[:, 1], pixelated_coords[:, 0], :] = 1

		# Add some edge blurring
		for x, y in pixelated_coords:
			for dx, dy in [(0, -1), (1, 0), (0, 1), (-1, 0)]:
				if 0 <= x + dx <= 27 and 0 <= y + dy <= 27 and model_input[y + dy, x + dx, :] == 0:
					model_input[y + dy, x + dx, :] = np.random.uniform(0.33, 1)

		pred_vector = model.predict(np.expand_dims(model_input, 0), verbose=0)

		for y in range(28):
			for x in range(28):
				colour = round(255 * model_input[y, x, 0])
				pg.draw.rect(
					scene,
					(colour, colour, colour),
					pg.Rect(x * DRAWING_CELL_SIZE, y * DRAWING_CELL_SIZE, DRAWING_CELL_SIZE, DRAWING_CELL_SIZE)
				)

		pred_lbl = font.render(f'{pred_vector.argmax()} ({(100 * pred_vector.max()):.1f}% sure)', True, 'green')
		scene.blit(pred_lbl, (10, 10))

		pg.display.update()

	# 8. Plot feature maps for user-drawn digit

	outputs = [model.layers[i].output for i in conv_layer_indices]  # Conv outputs for user digit
	short_model = Model(inputs=model.inputs, outputs=outputs)
	feature_maps = short_model.predict(np.expand_dims(model_input, 0), verbose=0)

	for idx, feature_map in enumerate(feature_maps, start=1):
		print(f'Feature map {idx}/{len(feature_maps)} shape: {feature_map.shape}')

		map_depth = feature_map.shape[-1]  # No. channels
		rows = map_depth // 4
		cols = map_depth // rows

		_, axes = plt.subplots(nrows=rows, ncols=cols, figsize=(8, 5))
		for ax_idx, ax in enumerate(axes.flatten()):
			ax.imshow(feature_map[0, ..., ax_idx], cmap='gray')  # Plot feature_map of depth 'ax_idx'
			ax.axis('off')
		plt.suptitle(f'Feature map of conv layer {idx}/{len(feature_maps)}\n(user-drawn digit)', x=0.512, y=0.97)
		plt.gcf().set_facecolor('#80b0f0')
		plt.show()
