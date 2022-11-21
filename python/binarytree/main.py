"""
Binary tree demo

Author: Sam Barba
Created 08/09/2021
"""

import numpy as np

from binary_tree import Tree
from tree_plotter import plot_tree

N_NODES = 31  # No. people names (max 113)

def make_random_binary_tree():
	with open(r'C:\Users\Sam Barba\Desktop\Programs\datasets\peopleNames.csv', 'r') as file:
		names = file.read().splitlines()

	rand_names = np.random.choice(names, size=N_NODES, replace=False)

	bin_tree = Tree(rand_names[0])

	for name in rand_names[1:]:
		bin_tree.insert(name)

	return bin_tree

def display_tree_info(tree):
	print('Tree:\n', tree.to_tuple())
	print('Height:', tree.get_height())
	print('In-order traversal:\n', tree.in_order_traversal())
	print('Pre-order traversal:\n', tree.pre_order_traversal())
	print('Post-order traversal:\n', tree.post_order_traversal())
	print('Breadth-first traversal:\n', tree.breadth_first_traversal())
	print('Is Binary Search Tree:', tree.is_bst())
	print('Balanced:', tree.is_balanced())

def make_balanced_bst(data, lo=0, hi=None):
	data.sort()

	if hi is None:
		hi = len(data) - 1
	if lo > hi:
		return None

	mid = (lo + hi) // 2

	tree = Tree(data[mid])
	tree.left_child = make_balanced_bst(data, lo, mid - 1)
	tree.right_child = make_balanced_bst(data, mid + 1, hi)
	return tree

if __name__ == '__main__':
	binary_tree = make_random_binary_tree()
	while binary_tree.is_balanced() and binary_tree.get_height() > 1:
		binary_tree = make_random_binary_tree()

	display_tree_info(binary_tree)

	plot_tree(binary_tree, 'unbalanced')

	binary_tree = make_balanced_bst(binary_tree.list_data())

	print()
	print('-' * 20, 'After balancing', '-' * 20)
	print()

	display_tree_info(binary_tree)

	plot_tree(binary_tree, 'balanced')
