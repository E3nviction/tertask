import curses
import os
import json
import sys
from re import T
from typing import cast
from task import Task, TaskManager, serialize_task
from envutils import ADict

EVENTS = [
	"next task",
	"prev task",
	"quit",
	"force quit",
	"toggle task",
	"help menu",
	"rename task",
	"add task",
	"delete task",
	"force delete task",
	"save tasks",
	"move task",
	"special:arrow pressed",
	"command"
]

settings = ADict(
	keybindings={
		"q": ["quit"],
		"Q": ["force quit"],
		" ": ["toggle task"],
		"h": ["help menu"],
		"r": ["rename task"],
		"a": ["add task"],
		"d": ["delete task"],
		"D": ["force delete task"],
		"s": ["save tasks"],

		":": ["command"],
		"e": ["command"],

		10:  ["move task"],
		"f": ["move task"],

		"j": ["next task"],
		"k": ["prev task"],
		curses.KEY_DOWN: ["next task", "special:arrow pressed"],
		curses.KEY_UP: ["prev task", "special:arrow pressed"],
	},
	use_colors=True,
	show_old_name_mode="next to", # ["shadow", "next to", "none"]
	show_help_message=True,
	show_current_mode=True,
	prompt_unsaved=True,
	prompt_delete=True,
	info=ADict(
		description=True,
		created_at=True,
		modified_at=True,
	)
)

class Application:
	def __init__(self) -> None:
		self.rename_mode = False
		self.move_mode   = False
		self.command_mode = False



		self.save_path = os.path.join(os.path.expanduser("~"),".config/tertask/tasks.json")
		self.load()
		self.custom_message = ""
		self.custom_type = "info"

	def load(self) -> None:
		save_exists = os.path.exists(self.save_path)

		self.create_folder_if_missing(os.path.dirname(self.save_path))

		self.tm = TaskManager()
		if save_exists:
			data = self.open_json(self.save_path)
			self.tm.load_serialized_tasks(data)

	def save(self) -> None:
		with open(self.save_path, "w") as f:
			f.truncate(0)
			f.write(json.dumps([serialize_task(task) for task in self.tm.tasks]))

	def keyevent(self, key: str | int) -> list[str]:
		for skey in settings.keybindings:
			actions_to_return = []
			for actions in settings.keybindings[skey]:
				is_int = isinstance(skey, int)
				if is_int and key == skey: actions_to_return.append(actions)
				if not is_int and key == ord(skey): actions_to_return.append(actions)
			if actions_to_return: return actions_to_return
		return [""]
	def show_help(self, page: int=1) -> None:
		self.stdscr.clear()
		self.stdscr.addstr(1, 2, " Help Menu - Press 'q' to return ", curses.A_BOLD | curses.A_REVERSE)
		self.stdscr.addstr(2, 2, " (c)ommands, (k)eybindings ", curses.A_BOLD)
		mode = "Help"
		if page == 1: mode = "Help — Commands"
		if page == 2: mode = "Help — Keybindings"
		if settings.show_current_mode: self.add_string(mode, self.width - (len(mode)+1), self.height - 1, curses.color_pair(4), move=False)
		if page == 1:
			text = [
				" :                  — Open command line",
				" ---------------------------------------",
				" q                  — quit",
				" q!                 — quit without saving",
				" w                  — save tasks",
				" wq                 — save tasks and quit",
				" export <file>      — export tasks to file",
				" rename <name...>   — rename task",
				" delete             — delete task",
				" describe <desc...> — set task description",
				" move               — move task",
				" a | add            — add task",
				" h | help           — show this help menu",
			]
			self.stdscr.addstr(4, 2, " Commands: ", curses.A_BOLD)
			self.stdscr.addstr(5, 4, "\n    ".join(text))
		elif page == 2:
			for idx, (key, action) in enumerate(settings.keybindings.items(), start=4):
				rebindings = {
					" ": "Space",
					258: "↓",
					259: "↑",
					10:  "⏎",
				}
				if key in rebindings:
					key = rebindings[key]
				self.stdscr.addstr(idx, 4, f"{str(key).ljust(10, ' ')}| {" - ".join(action)}")

		key = self.stdscr.getch()
		if key == ord("q"):
			return
		elif key == ord("c"):
			self.show_help(1)
		elif key == ord("k"):
			self.show_help(2)
		else:
			self.show_help()

	def render(self, only_render: bool=False) -> None:
		self.stdscr.clear()

		# Task list
		for idx, task in enumerate(self.tm.tasks):
			task = cast(Task, task) # convert to Task object
			x = 2
			y = 2 + idx
			is_completed_attr = curses.color_pair(2) if task.completed else curses.A_NORMAL
			if idx == self.tm.selected:
				if self.rename_mode and not only_render:
					self.render(only_render=True)
					new_name = ""

					if settings.show_old_name_mode == "next to":
						new_name = self.input(x, y, f"{task.mark} {task.title} → ", curses.color_pair(1))
					elif settings.show_old_name_mode == "shadow":
						self.add_string(f"{task.mark} {task.title}", x, y, curses.color_pair(5))
						new_name = self.input(x, y, f"{task.mark} ", curses.color_pair(3))
					elif settings.show_old_name_mode == "none":
						self.add_string(" " * len(f"{task.mark} {task.title}"), x, y, curses.color_pair(5))
						new_name = self.input(x, y, f"{task.mark} ", curses.color_pair(3))

					if new_name: task.title = new_name
					self.rename_mode = False
					self.render()
					break
				elif self.move_mode and not only_render:
					self.render(only_render=True)
					self.add_string(f" ↕ {task.mark} {task.title}", x, y, curses.color_pair(1))
					key = self.stdscr.getch()
					actions = self.check_keys(key, whitelist=["next task", "prev task", "special:arrow pressed", "move task"], use_whitelist=True)
					move_dir = 1 if "next task" in actions else -1
					if "special:arrow pressed" in actions:
						self.tm.move_task(self.tm.selected, self.tm.selected + move_dir)
					self.move_mode = "move task" not in actions
					self.render()
					break
				else:
					self.draw_task(x, y, task, selected=True)
					if not settings.use_colors:
						self.draw_task(x, y, task, selected=True, attr=curses.A_REVERSE)
			else: self.draw_task(x, y, task, attr=is_completed_attr)
		if len(self.tm.tasks) == 0:
		# if no tasks exist
			first_keybind_add_task = [keybind for keybind in settings.keybindings if settings.keybindings[keybind] == "add task"][0]
			self.stdscr.addstr(2, 2, f"No tasks available. Press '{first_keybind_add_task}' to add a new task.")
		# Top bar
		title = " TerTask - 'h' for help ".ljust(self.width, " ")
		if not settings.show_help_message:
			title = " TerTask ".ljust(self.width, " ")
		self.stdscr.addstr(0, 0, title, curses.A_BOLD)
		self.stdscr.addstr(1, 0, "─" * self.width)

		color = curses.color_pair(1)
		if self.custom_type == "info": color = curses.color_pair(3)
		elif self.custom_type == "warning": color = curses.color_pair(4)
		elif self.custom_type == "error": color = curses.color_pair(6)
		self.stdscr.addstr(0, self.width - len(self.custom_message) - 1, self.custom_message, color)

		# Bottom bar
		mode = "Normal"
		if self.rename_mode: mode = "Rename"
		elif self.move_mode: mode = "Move"
		elif self.command_mode: mode = "Command"
		if settings.show_current_mode: self.add_string(mode, self.width - (len(mode)+1), self.height - 1, curses.color_pair(4), move=False)

		# Description panel
		self.stdscr.addstr(self.height - 7, 0, "─" * self.width)
		if settings.info.description:
			self.stdscr.addstr(self.height - 6, 2, "Description: ")
			self.stdscr.addstr(self.height - 5, 2, self.tm.current_task.description)

		# Footer with created/modified info
		if settings.info.created_at: self.stdscr.addstr(self.height - 3, 2, f"Created: {self.tm.current_task.created_at} ")
		if settings.info.modified_at: self.stdscr.addstr(self.height - 2, 2, f"Modified: {self.tm.current_task.modified_at} ")

	def main_loop(self, stdscr: curses.window) -> None:
		self.stdscr = stdscr
		self.run_control_sequence(f"\x1b[\x36 q")
		curses.curs_set(0)
		curses.start_color()
		curses.use_default_colors()
		self.stdscr.keypad(True)
		self.render()

		# Colors
		if settings.use_colors:
			curses.init_pair(1, 208, -1) # edit mode
			curses.init_pair(2, curses.COLOR_GREEN, -1) # Completed task
			curses.init_pair(3, curses.COLOR_BLUE, -1) # Selected task
			curses.init_pair(4, 208, -1) # message
			curses.init_pair(5, 238, -1) # shadow
			curses.init_pair(6, 196, -1) # red
		else:
			curses.init_pair(1, curses.COLOR_WHITE, -1) # edit mode
			curses.init_pair(2, 238, -1) # Completed task
			curses.init_pair(3, curses.COLOR_WHITE, -1) # Selected task
			curses.init_pair(4, curses.COLOR_WHITE, -1) # message
			curses.init_pair(5, 235, -1) # shadow
			curses.init_pair(6, curses.COLOR_WHITE, -1) # red
		try:
			while True:
				self.tm.max_items = self.height - 9
				self.render()
				key = self.stdscr.getch()
				self.custom_message = ""
				self.custom_type = "info"

				whitelist = []
				use_whitelist = True if self.rename_mode or self.move_mode else False
				if self.rename_mode:
					whitelist = ["rename task"]
				if self.move_mode:
					whitelist = ["move task"]
				actions = self.check_keys(key, whitelist=whitelist, use_whitelist=use_whitelist)
				self.handle_actions(actions)
		except Exception as e:
			print("Unexpected error:", e)
			print("Do you want to save your tasks? (Y/n) ", end="")
			if input().lower() != "n": self.save()

	def handle_actions(self, actions: list[str], extended: bool=False, only_extended: bool=False) -> None:
		for action in actions:
			if not only_extended:
				if action == "rename task":
					self.rename_mode = True
				elif action == "move task":
					self.move_mode = True
				elif action == "prev task":
					self.tm.prev()
				elif action == "next task":
					self.tm.next()
				elif action == "quit":
					if not self.has_saved_tasks() and settings.prompt_unsaved:
						if self.prompt(2, self.height - 1, "You have unsaved tasks. Do you want to save them? (Y/n) ", curses.color_pair(1), True).lower() != "n": self.save()
					exit(0)
				elif action == "force quit":
					self.save()
					exit(0)
				elif action == "toggle task":
					self.tm.current_task.toggle()
				elif action == "add task":
					self.tm.add("New Task")
					self.tm.select_task(-1)
					self.rename_mode = True
				elif action == "delete task":
					if settings.prompt_delete:
						if self.prompt(2, self.height - 1, "Are you sure? (y/N) ", curses.color_pair(1), True).lower() != "y": break
					self.tm.current_task.delete()
				elif action == "force delete task":
					self.tm.current_task.delete()
				elif action == "save tasks":
					self.custom_message = "Saved tasks..."
					self.save()
				elif action == "command":
					self.command_mode = True
					self.render(only_render=True)
					cmd = self.input(2, self.height - 1, ": ", curses.color_pair(1), -1, placeholder="help - to open help menu")
					self.handle_actions([cmd], True, True)
					self.command_mode = False
				elif action == "help menu":
					self.show_help()
			if extended:
				actions = action.split(" ")
				action = actions[0]
				match action:
					case "q":
						if not self.has_saved_tasks() and settings.prompt_unsaved:
							if self.prompt(2, self.height - 1, "You have unsaved tasks. Are you sure? (y/N) ", curses.color_pair(1), True).lower() != "y": break
						exit(0)
					case "q!":
						exit(0)
					case "w":
						self.save()
						self.custom_message = "Saved tasks..."
					case "wq" | "qw":
						self.save()
						exit(0)
					case "export":
						if len(actions) == 2:
							self.custom_message = "Exporting tasks..."
							self.custom_type = "info"
							with open(actions[1], "w") as f:
								f.truncate(0)
								f.write(json.dumps([serialize_task(task) for task in self.tm.tasks]))
						else:
							self.custom_type = "error"
							self.custom_message = "Error: missing argument -> :export <file>"
					case "rename":
						if len(actions) > 1:
							self.custom_message = f"Renamed task '{self.tm.current_task.title}' to '{" ".join(actions[1:])}'."
							self.custom_type = "info"
							self.tm.current_task.title = " ".join(actions[1:])
						else:
							self.custom_type = "error"
							self.custom_message = "Error: missing argument -> :rename <new name...>"
					case "delete":
						self.custom_message = f"Deleted task '{self.tm.current_task.title}'."
						self.custom_type = "info"
						self.tm.current_task.delete()
					case "move":
						self.move_mode = True
					case "a" | "add":
						self.tm.add("New Task")
						self.tm.select_task(-1)
						self.rename_mode = True
					case "":
						pass
					case "h" | "help":
						self.show_help()
					case "describe":
						if len(actions) > 1:
							self.custom_message = f"Set Description for Task."
							self.custom_type = "info"
							self.tm.current_task.description = " ".join(actions[1:])
						else:
							self.custom_type = "error"
							self.custom_message = "Error: missing argument -> :describe <new description...>"
					case _:
						self.custom_type = "error"
						self.custom_message = "Error: unknown command"

	def check_keys(self, key: int, blacklist: list[str]=[], whitelist: list[str]=[], use_whitelist: bool=False) -> list[str]:
		actions = []
		for action in EVENTS:
			is_not_disabled = (action not in blacklist) if not use_whitelist else (action in whitelist)
			actions.append(action) if action in self.check_key(key, action, is_not_disabled) else None
		return actions if len(actions) != 0 else [] # return empty list if no actions are found

	def request_input(self) -> None:
		curses.curs_set(2)
		curses.echo()

	def stop_input(self) -> None:
		curses.curs_set(0)
		curses.noecho()

	def run_control_sequence(self, sequence: str) -> None:
		os.write(sys.stdout.fileno(), bytes(sequence, 'utf-8'))

	def draw_task(self, x: int, y: int, task: Task, selected: bool=False, attr: int=curses.A_NORMAL) -> None:
		self.stdscr.addstr(y, x, f"{task.mark} {str(task.title)}", curses.color_pair(3) | attr if selected else attr)

	def check_key(self, key: int, action: str, is_not_disabled: bool) -> list[str]:
		return self.keyevent(key) if (action in self.keyevent(key) and is_not_disabled) else [""]

	def create_folder_if_missing(self, path: str) -> None:
		if not os.path.exists(path): os.makedirs(path)

	def open_json(self, path: str) -> list[dict]:
		with open(path, "r") as f:
			return json.load(f)

	def has_saved_tasks(self) -> bool:
		old_tasks = self.open_json(self.save_path)
		new_tasks = [serialize_task(task) for task in self.tm._tasks]
		return str(old_tasks) == str(new_tasks)

	def input(self, x: int, y: int, prompt_string: str, attr: int, starting_offset: int=0, offset: int=3, prompt_attr: int=curses.A_NORMAL, placeholder: str="", placeholder_attr: int|None=None) -> str:
		self.add_string(prompt_string, x, y, attr)
		self.request_input()
		self.stdscr.attron(prompt_attr)
		if placeholder_attr is None: placeholder_attr = curses.color_pair(5)
		self.add_string(placeholder, x + len(prompt_string) + starting_offset, y, placeholder_attr, offset)
		answer = self.stdscr.getstr(y, x + len(prompt_string) + starting_offset, self.width - len(prompt_string) - offset).decode("utf-8")
		self.stdscr.attroff(prompt_attr)
		self.stop_input()
		return answer

	def prompt(self, x: int, y: int, prompt_string: str, attr: int, use_char: bool=False, starting_offset: int=0) -> str:
		if use_char: return self.inputch(x, y, prompt_string, attr, starting_offset)
		return self.input(x, y, prompt_string, attr, starting_offset)

	def inputch(self, x: int, y: int, prompt_string: str, attr: int, starting_offset: int=0) -> str:
		self.add_string(prompt_string, x, y, attr)
		self.request_input()
		answer = self.stdscr.getch(y, x + len(prompt_string) + starting_offset)
		self.stop_input()
		return chr(answer)

	def add_string(self, string: str, x: int, y: int, attr: int=curses.A_NORMAL, offset: int=0, move: bool=True) -> None:
		self.stdscr.addstr(y, x, string, attr)
		if move: self.stdscr.move(y, x + len(string) + offset)
		self.stdscr.refresh()

	@property
	def height(self) -> int: return self.stdscr.getmaxyx()[0]
	@property
	def width(self) -> int: return self.stdscr.getmaxyx()[1]


if __name__ == "__main__":
	app = Application()
	curses.wrapper(app.main_loop)
