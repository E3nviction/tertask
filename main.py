import curses
import os
import json
import colorama
import time
from typing import cast
from task import Task, TaskManager, serialize_task, deserialize_task
from envutils import ADict

settings = ADict(keybindings={
	"j": "next task",
	"k": "prev task",
	"q": "quit",
	" ": "toggle task",
	"h": "help menu",
	"r": "rename task",
	"a": "add task",
	"d": "delete task",
	"s": "save tasks",
	curses.KEY_DOWN: "next task",
	curses.KEY_UP: "prev task",
})

class Application:
	def __init__(self) -> None:
		self.rename_mode = False

		self.save_path = os.path.join(os.path.expanduser("~"),".config/tertask/tasks.json")
		self.load()
		self.custom_message = ""

	def load(self) -> None:
		if not os.path.exists(os.path.dirname(self.save_path)):
			os.makedirs(os.path.dirname(self.save_path))
		if os.path.exists(self.save_path):
			data = open(self.save_path, "r").read()
			data = json.loads(data)
			self.tm = TaskManager()
			for task in data:
				self.tm._add(deserialize_task(task))
		else:
			self.tm = TaskManager()

	def save(self) -> None:
		with open(self.save_path, "w") as f:
			f.write(json.dumps([serialize_task(task) for task in self.tm.tasks]))

	def keyevent(self, key: str | int) -> str | None:
		for skey in settings.keybindings:
			if isinstance(skey, int):
				if key == skey:
					return settings.keybindings[skey]
			elif key == ord(skey):
				return settings.keybindings[skey]
		return None
	def show_help(self, stdscr: curses.window) -> None:
		stdscr.clear()
		stdscr.addstr(1, 2, " Help Menu - Press any key to return ", curses.A_BOLD | curses.A_REVERSE)

		for idx, (key, action) in enumerate(settings.keybindings.items(), start=3):
			rebindings = {
				" ": "Space",
				258: "↓",
				259: "↑",
			}
			if key in rebindings:
				key = rebindings[key]
			stdscr.addstr(idx, 4, f"{str(key).ljust(10, ' ')}| {action}")

		stdscr.getch()
	def draw_task(self, x: int, y: int, task: Task, selected: bool=False, attr: int=curses.A_NORMAL) -> None:
		if selected:
			self.stdscr.addstr(y, x, f"{task.mark} {task}", curses.color_pair(3) | attr)
		else:
			self.stdscr.addstr(y, x, f"{task.mark} {task}", attr)
	def request_input(self) -> None:
		curses.curs_set(1)
		curses.echo()
	def stop_input(self) -> None:
		curses.curs_set(0)
		curses.noecho()
	def render(self, only_render: bool=True) -> None:
		self.stdscr.clear()
		height, width = self.stdscr.getmaxyx()

		# Task list
		for idx, task in enumerate(self.tm.tasks):
			task = cast(Task, task) # convert to Task object
			x = 2
			y = 2 + idx
			if idx == self.tm.selected:
				if self.rename_mode and only_render:
					self.render(only_render=False)

					self.stdscr.addstr(y, x, f"{task.mark} {task.title} -> ", curses.color_pair(1))
					self.stdscr.move(y, x + len(task.title) + 6)
					self.stdscr.refresh()

					self.request_input()

					new_name = self.stdscr.getstr(y, x + len(task.title) + 6, width - len(task.title) - 4).decode("utf-8")

					if new_name: task.title = new_name
					self.rename_mode = False

					self.stop_input()

					self.stdscr.clear()
					self.render()
				else: self.draw_task(x, y, task, selected=True)
			else:
				self.draw_task(x, y, task, attr=curses.color_pair(2) if task.completed else curses.A_NORMAL)
		if len(self.tm.tasks) == 0:
			self.stdscr.addstr(2, 2, f"No tasks available. Press '{[keybind for keybind in settings.keybindings if settings.keybindings[keybind] == "add task"][0]}' to add a new task.")
		# Top bar
		self.stdscr.addstr(0, 0, " TerTask - 'h' for help ".ljust(width, " "), curses.A_BOLD)
		self.stdscr.addstr(1, 0, "─" * width)
		self.stdscr.addstr(0, width - len(self.custom_message) - 1, self.custom_message, curses.color_pair(4))

		# Description panel
		self.stdscr.addstr(height - 6, 0, "─" * width)
		self.stdscr.addstr(height - 5, 2, "Description: ")
		self.stdscr.addstr(height - 4, 2, self.tm.current_task.description)

		# Footer with created/modified info
		self.stdscr.addstr(height - 2, 2, f"Created: {self.tm.current_task.created_at} ")
		self.stdscr.addstr(height - 1, 2, f"Modified: {self.tm.current_task.modified_at} ")

	def main_loop(self, stdscr: curses.window) -> None:
		self.stdscr = stdscr
		curses.curs_set(0)
		curses.start_color()
		curses.use_default_colors()
		self.stdscr.keypad(True)
		self.render()

		curses.init_pair(1, 208, -1,) # edit mode
		curses.init_pair(2, curses.COLOR_GREEN, -1,) # Completed task
		curses.init_pair(3, curses.COLOR_BLUE, -1,) # Selected task
		curses.init_pair(4, 208, -1) # message

		while True:
			self.render()
			key = self.stdscr.getch()
			self.custom_message = ""

			if self.keyevent(key) == "prev task" and (not self.rename_mode):
				self.tm.prev()
			elif self.keyevent(key) == "next task" and (not self.rename_mode):
				self.tm.next()
			elif self.keyevent(key) == "quit":
				return
			elif self.keyevent(key) == "toggle task" and (not self.rename_mode):
				self.tm.current_task.toggle()
			elif self.keyevent(key) == "rename task":
				self.rename_mode = True
			elif self.keyevent(key) == "add task":
				self.tm.add("New Task")
				self.tm.select_task(-1)
				self.rename_mode = True
			elif self.keyevent(key) == "delete task":
				self.tm.current_task.delete()
				self.tm.prev()
			elif self.keyevent(key) == "save tasks":
				self.custom_message = "Saved tasks..."
				self.save()
			elif self.keyevent(key) == "help menu":
				self.show_help(self.stdscr)

if __name__ == "__main__":
	app = Application()
	curses.wrapper(app.main_loop)
