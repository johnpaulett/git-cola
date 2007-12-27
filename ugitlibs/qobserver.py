#!/usr/bin/env python
from PyQt4.QtCore import QObject
from PyQt4.QtCore import SIGNAL
from PyQt4.QtGui import QSpinBox
from PyQt4.QtGui import QPixmap
from PyQt4.QtGui import QTextEdit
from PyQt4.QtGui import QLineEdit
from PyQt4.QtGui import QListWidget

from observer import Observer

class QObserver(Observer, QObject):

	def __init__(self, model, view):
		Observer.__init__(self, model)
		QObject.__init__(self)

		self.view = view

		self.__actions = {}
		self.__callbacks = {}
		self.__model_to_view = {}
		self.__view_to_model = {}
	
	def connect(self, obj, signal_str, *args):
		'''Convenience function so that subclasses do not have
		to import QtCore.SIGNAL.'''
		signal = signal_str
		if type(signal) is str:
			signal = SIGNAL(signal)
		return QObject.connect(obj, signal, *args)

	def SLOT(self, *args):
		'''Default slot to handle all Qt callbacks.
		This method delegates to callbacks from add_signals.'''

		widget = self.sender()
		sender = str(widget.objectName())

		if sender in self.__callbacks:
			self.__callbacks[sender](*args)

		elif sender in self.__view_to_model:
			model = self.model
			model_attr = self.__view_to_model[sender]
			if isinstance(widget, QTextEdit):
				value = str(widget.toPlainText())
				model.set(model_attr, value, notify=False)
			elif isinstance(widget, QLineEdit):
				value = str(widget.text())
				model.set(model_attr, value, notify=False)
			else:
				print("SLOT(): Unknown widget:", sender, widget)

	def add_signals(self, signal_str, *objects):
		'''Connects object's signal to the QObserver.'''
		for obj in objects:
			self.connect(obj, signal_str, self.SLOT)

	def add_callbacks(self, callbacks):
		'''Registers callbacks that are called in response to GUI events.'''
		for sender, callback in callbacks.iteritems():
			self.__callbacks[sender] = callback

	def model_to_view(self, model_attr, *widget_names):
		'''Binds model attributes to qt widgets(model->view)'''
		self.add_subject(model_attr)
		self.__model_to_view[model_attr] = widget_names
		for widget_name in widget_names:
			self.__view_to_model[widget_name] = model_attr

	def add_actions(self, model_attr, callback):
		'''Register view actions that are called in response to
		view changes.(view->model)'''
		self.add_subject(model_attr)
		self.__actions[model_attr] = callback

	def subject_changed(self, attr, value):
		'''Sends a model attribute to the view(model->view)'''
		if attr in self.__model_to_view:
			for widget_name in self.__model_to_view[attr]:
				widget = getattr(self.view, widget_name)
				if isinstance(widget, QSpinBox):
					widget.setValue(value)
				elif isinstance(widget, QPixmap):
					widget.load(value)
				elif isinstance(widget, QTextEdit):
					widget.setText(value)
				elif isinstance(widget, QLineEdit):
					widget.setText(value)
				elif isinstance(widget, QListWidget):
					widget.clear()
					for i in value: widget.addItem(i)
				else:
					print('subject_changed(): '
						+ 'Unknown widget:',
						widget_name, widget)

		if attr not in self.__actions:
			return
		widgets = []
		if attr in self.__model_to_view:
			for widget_name in self.__model_to_view[attr]:
				widget = getattr(self.view, widget_name)
				widgets.append(widget)
		# Call the model callback w/ the view's widgets as the args
		self.__actions[attr](*widgets)