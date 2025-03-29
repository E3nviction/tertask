from datetime import datetime

def curr_time() -> str:
	return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

class Task:
	def __init__(self, title: str, checked: bool=False, description: str="", _id: int=0) -> None:
		self._title = title
		self._description = description
		self._checked = checked
		self._created_at = curr_time()
		self._updated_at = curr_time()
		self._deleted = False
		self.id = _id
		self.index = 0

	@property
	def mark(self) -> str: return "✓" if self.checked else "✕"
	@property
	def title(self) -> str: return self._title
	@property
	def description(self) -> str: return self._description
	@property
	def checked(self) -> bool: return self._checked
	@property
	def created_at(self) -> str: return self._created_at
	@property
	def updated_at(self) -> str: return self._updated_at
	@property
	def deleted(self) -> bool: return self._deleted

	# Aliases
	@property
	def modified_at(self) -> str: return self.updated_at
	@property
	def done(self) -> bool: return self.checked
	@property
	def is_deleted(self) -> bool: return self.deleted
	@property
	def completed(self) -> bool: return self.checked
	@property
	def is_completed(self) -> bool: return self.checked

	@mark.setter
	def mark(self, mark: str) -> None: self.checked = (mark == "✓")
	@title.setter
	def title(self, title: str) -> None: self._title = title
	@checked.setter
	def checked(self, checked: bool) -> None: self._checked = checked
	@description.setter
	def description(self, description: str) -> None: self._description = description

	def set_description(self, description: str):
		self.description = description
		self._updated_at = curr_time()
		return self
	def set_title(self, title: str) -> "Task":
		self.title = title
		self._updated_at = curr_time()
		return self
	def set_checked(self, checked: bool) -> "Task":
		self.checked = checked
		self._updated_at = curr_time()
		return self
	def toggle(self) -> "Task":
		self.checked = not self.checked
		self._updated_at = curr_time()
		return self
	def delete(self) -> "Task":
		self._deleted = True
		self._updated_at = curr_time()
		return self
	def restore(self) -> "Task":
		self._deleted = False
		self._updated_at = curr_time()
		return self
	def check(self) -> "Task":
		self.checked = True
		self._updated_at = curr_time()
		return self
	def uncheck(self) -> "Task":
		self.checked = False
		self._updated_at = curr_time()
		return self
	def update(self) -> "Task":
		self._updated_at = curr_time()
		return self
	def complete(self) -> "Task":
		self.checked = True
		self._updated_at = curr_time()
		return self
	def uncomplete(self) -> "Task":
		self.checked = False
		self._updated_at = curr_time()
		return self

	def __len__(self) -> int:
		return len(self.title)
	def __str__(self) -> str:
		return f"{self.title}"
	def __repr__(self) -> str:
		return str(self)

class TaskManager:
	def __init__(self) -> None:
		self._tasks = []
		self._selected = 0
		self.scroll_y = 0
		self.max_items = 27

	@property
	def selected(self) -> int: return self._selected
	@property
	def deleted_tasks(self) -> list[Task]: return [task for task in self._tasks if task.deleted]
	@property
	def all_tasks(self) -> list[Task]: return self._tasks
	@property
	def active_tasks(self) -> list[Task]: return [task for task in self._tasks if not task.deleted]
	@property
	def tasks(self) -> list[Task]: return self.active_tasks[self.scroll_y:self.scroll_y+self.max_items]

	@selected.setter
	def selected(self, idx: int) -> None:
		self._selected = idx
		self._index_tasks()

	@tasks.setter
	def tasks(self, tasks: list[Task]) -> None:
		self.active_tasks[self.scroll_y:self.scroll_y+self.max_items] = tasks
		self._index_tasks()

	@active_tasks.setter
	def active_tasks(self, tasks: list[Task]) -> None:
		tasks.extend(self.deleted_tasks)
		self._tasks = tasks
		self._index_tasks()

	def __len__(self) -> int: return len(self.tasks)

	def add(self, title: str, description: str="", checked: bool=False) -> None:
		self._add(Task(title, checked, description, len(self.tasks)))
	def remove(self, idx: int) -> None:
		self._remove(idx)

	def _add(self, task: Task) -> None:
		self._tasks.append(task)
		self._index_tasks()
	def _remove(self, idx: int) -> None:
		self._tasks[idx].delete()
		self._index_tasks()

	def next(self) -> None:
		if len(self.tasks) == 0: return
		if self.selected + 1 >= len(self.tasks) and not (self.selected + 1 + self.scroll_y >= len(self.active_tasks)):
			excess = ((self.selected + 1) - len(self.tasks)) + 1
			self.scroll_y += excess
		elif self.selected + 1 + self.scroll_y >= len(self.active_tasks):
			self.scroll_y = 0
			self.selected = 0
		else:
			self.selected = (self.selected + 1) % len(self.tasks)
		self._index_tasks()
	def prev(self) -> None:
		if len(self.tasks) == 0: return
		if self.selected - 1 < 0:
			if self.scroll_y > 0:
				self.scroll_y -= 1
			else:
				if len(self.active_tasks) > self.max_items:
					self.scroll_y = len(self.active_tasks) - self.max_items
				else:
					self.scroll_y = 0
				self.selected = len(self.tasks) - 1
		else:
			self.selected = (self.selected - 1) % len(self.tasks)
		self._index_tasks()

	def move_task(self, idx: int, new_idx: int) -> None:
		if new_idx < 0 or new_idx >= len(self.tasks): return
		self._tasks.insert(new_idx + self.scroll_y, self._tasks.pop(idx + self.scroll_y))
		self.selected = new_idx
		self.active_tasks[new_idx].update()
		self._index_tasks()

	def load_serialized_tasks(self, tasks: list[dict]) -> None:
		self._tasks = [deserialize_task(task) for task in tasks]
		self._index_tasks()
	def serialize_tasks(self) -> list[dict]:
		return [serialize_task(task) for task in self._tasks]

	def _bulk_add(self, tasks: list[Task]) -> None:
		for task in tasks: self._add(task)
		self.selected = len(self.tasks) - 1
		self._index_tasks()
	def _bulk_remove(self, taskidxs: list[int]) -> None:
		for task in taskidxs: self._remove(task)
		self._index_tasks()

	def select_task(self, idx: int) -> None:
		self.selected = idx
		if idx == -1:
			if len(self.active_tasks) > self.max_items:
				self.scroll_y = len(self.active_tasks) - self.max_items
			else:
				self.scroll_y = 0
			self.selected = len(self.tasks) - 1
		self._index_tasks()

	def get(self, idx: int) -> Task:
		if len(self.tasks) == 0: return Task("No tasks found", False, "No tasks found")
		if idx >= len(self.tasks): return self.current_task
		return self.tasks[idx]

	@property
	def current_task(self) -> Task:
		if len(self.tasks) == 0: return Task("No tasks found", False, "No tasks found")
		if self.selected >= len(self.tasks): self.prev()
		return self.tasks[self.selected]

	def _index_tasks(self) -> None:
		for idx, task in enumerate(self.tasks):
			task.index = idx

def serialize_task(task) -> dict:
	return {
		"title": task.title,
		"description": task.description,
		"checked": task.checked,
		"created_at": task.created_at,
		"updated_at": task.updated_at,
		"deleted": task.deleted,
		"id": task.id
	}

def deserialize_task(data) -> Task:
	task = Task(data["title"], data["checked"], data["description"], data["id"])
	task._created_at = data["created_at"]
	task._updated_at = data["updated_at"]
	task._deleted = data["deleted"]
	return task