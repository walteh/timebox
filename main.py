import rumps
import time
import subprocess
import shlex
import logging
import sys
import things

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

def get_things_today_tasks():
    try:
        logging.info("Fetching today's tasks from Things...")
        tasks = things.today()
        logging.info(f"Found {len(tasks)} tasks for today")
        # Add debug logging to see task structure
        for task in tasks:
            logging.debug(f"Task data: {task}")
        return tasks
    except Exception as e:
        logging.error(f"Error fetching tasks: {str(e)}")
        return []

def extract_minutes(tag):
    """Extract minutes from various time formats like '30min', '30 min', '30m', '30 m'"""
    # Remove spaces and convert to lowercase
    tag = tag.lower().replace(' ', '')
    
    # Try to find a number followed by m or min
    if tag.endswith('min') or tag.endswith('m'):
        try:
            # Remove 'min' or 'm' and convert to int
            minutes = int(''.join(c for c in tag if c.isdigit()))
            return minutes
        except ValueError:
            return None
    return None

def process_tasks(tasks):
    processed_tasks = {}  # Will be {project_name: {task_title: (minutes, url)}}
    logging.info(f"Processing {len(tasks)} tasks")
    
    for task in tasks:
        logging.debug(f"Processing task: {task['title']}")
        if 'tags' in task:
            # Look for any tag that might represent time
            time_tags = []
            for tag in task['tags']:
                if minutes := extract_minutes(tag):
                    time_tags.append((tag, minutes))
            
            if time_tags:
                # Use the first valid time tag found
                _, minutes = time_tags[0]
                
                # Get project name (or "No Project" if none)
                project_name = task.get('project_title', 'No Project')
                
                # Initialize project dict if needed
                if project_name not in processed_tasks:
                    processed_tasks[project_name] = {}
                
                processed_tasks[project_name][task['title']] = (
                    minutes,
                    f"things:///show?id={task['uuid']}"
                )
    
    logging.info(f"Found tasks in {len(processed_tasks)} projects")
    return processed_tasks

def hour_formatter(minutes):
    if minutes // 60 > 0:
        if spare_min := minutes % 60:
            return f"{minutes // 60}h and {spare_min}min of work today!"
        else:
            return f"{minutes // 60}h of work today!"
    else:
        return f"{minutes}min of work today!"

class TimerApp(object):
    def toggle_button(self, sender):
        sender.state = not sender.state

    def __init__(self, timer_interval=1):
        self.timer = rumps.Timer(self.on_tick, 1)
        self.timer.stop()  # timer running when initialized
        self.timer.count = 0
        self.app = rumps.App("Timebox", "🥊")
        self.interval = 60
        self.current_things_task_url = None
        self.start_pause_button = rumps.MenuItem(
            title="Start Timer",
            callback=lambda _: self.start_timer(_, self.interval),
            key="s",
        )
        self.stop_button = rumps.MenuItem(title="Stop Timer", callback=None)
        self.buttons = {}
        self.buttons_callback = {}
        for i in [5, 10, 15, 20, 25]:
            title = str(i) + " Minutes"
            callback = lambda _, j=i: self.set_mins(_, j, None)
            self.buttons["btn_" + str(i)] = rumps.MenuItem(
                title=title, callback=callback
            )
            self.buttons_callback[title] = callback

        self.sync_button = rumps.MenuItem(
            title="Sync", callback=lambda _: self.sync_data(), key="r"
        )

        self.sum_menu_item = rumps.MenuItem(
            title="sum_total_time", callback=None
        )

        self.app.menu = [
            self.start_pause_button,
            self.sync_button,
            None,
            self.sum_menu_item,
            # *self.things_buttons.values(),
            None,
            *self.buttons.values(),
            None,
            self.stop_button,
        ]

        self.sync_data()

    def sync_data(self):
        for key, btn in self.buttons.items():
            btn.set_callback(self.buttons_callback[btn.title])

        self.things_tasks = get_things_today_tasks()
        self.things_processed_tasks = process_tasks(self.things_tasks)

        # Calculate total time across all projects
        total_minutes = sum(
            task_data[0] 
            for project_tasks in self.things_processed_tasks.values() 
            for task_data in project_tasks.values()
        )
        
        self.app.menu["sum_total_time"].title = f"{hour_formatter(total_minutes)}"

        # Remove old menu items
        if hasattr(self, "things_buttons"):
            for project_items in self.things_buttons.values():
                for title in project_items:
                    del self.app.menu[title]

        # Create new menu structure
        self.things_buttons = {}
        
        # Add a separator after the total time
        self.app.menu.insert_after("sum_total_time", None)
        last_item = "sum_total_time"
        
        for project_name, project_tasks in self.things_processed_tasks.items():
            # Add project header if there are tasks
            if project_tasks:
                project_header = f"—— {project_name} ——"
                header_item = rumps.MenuItem(project_header, callback=None)
                self.app.menu.insert_after(last_item, header_item)
                last_item = project_header
                
                # Initialize project in things_buttons
                self.things_buttons[project_name] = []
                
                # Add tasks under project header
                for title, (time, task_url) in project_tasks.items():
                    menu_title = f"{title} → {time}min"
                    menu_item = rumps.MenuItem(
                        title=menu_title,
                        callback=lambda _, j=time, k=task_url: self.set_mins(_, j, k),
                    )
                    self.app.menu.insert_after(last_item, menu_item)
                    self.things_buttons[project_name].append(menu_title)
                    last_item = menu_title

        # Add a separator before the fixed-time buttons
        self.app.menu.insert_after(last_item, None)

    def run(self):
        # Calculate total time
        total_minutes = sum(
            task_data[0] 
            for project_tasks in self.things_processed_tasks.values() 
            for task_data in project_tasks.values()
        )
        self.app.menu["sum_total_time"].title = f"{hour_formatter(total_minutes)}"
        self.app.run()

    def set_mins(self, sender, interval, task_url):
        # Flatten all menu items for comparison
        all_menu_items = [
            item
            for project_items in self.things_buttons.values()
            for item in project_items
        ] + list(self.buttons.values())

        for btn in all_menu_items:
            if sender.title == btn.title:
                self.interval = interval * 60
                cleaned_title = " ".join(sender.title.split()[:-2])
                if task_url is not None:
                    self.menu_title = " → " + cleaned_title
                    self.current_things_task_url = task_url
                else:
                    self.menu_title = ""
                btn.state = True
            elif sender.title != btn.title:
                btn.state = False

    def start_timer(self, sender, interval):
        for btn in [*self.things_buttons.values(), *self.buttons.values()]:
            btn.set_callback(None)

        if sender.title.lower().startswith(("start", "continue")):

            if sender.title == "Start Timer":
                # reset timer & set stop time
                self.timer.count = 0
                self.timer.end = interval

            # change title of MenuItem from 'Start timer' to 'Pause timer'
            sender.title = "Pause Timer"

            # lift off! start the timer
            self.timer.start()
        else:  # 'Pause Timer'
            sender.title = "Continue Timer"
            self.timer.stop()

    def on_tick(self, sender):
        time_left = sender.end - sender.count
        mins = time_left // 60 if time_left >= 0 else time_left // 60 + 1
        secs = time_left % 60 if time_left >= 0 else (-1 * time_left) % 60
        if mins == 0 and time_left < 0:
            rumps.notification(
                title="Timebox",
                subtitle="Time is up! Take a break :)",
                message="",
            )
            if self.current_things_task_url is not None:
                # print("opening url", self.current_things_task_url)
                subprocess.call(
                    shlex.split("open '" + self.current_things_task_url + "'")
                )
                self.current_things_task_url = None
            self.stop_timer(sender)
            self.stop_button.set_callback(None)
            self.sync_data()
        else:
            self.stop_button.set_callback(self.stop_timer)
            self.app.title = "{:2d}:{:02d} {}".format(
                mins, secs, getattr(self, "menu_title", "")
            )
        sender.count += 1

    def stop_timer(self, sender=None):
        self.timer.stop()
        self.timer.count = 0
        self.app.title = "🥊"
        self.stop_button.set_callback(None)

        for key, btn in self.buttons.items():
            btn.set_callback(self.buttons_callback[btn.title])

        for (title, btn) in self.things_buttons.items():
            btn.set_callback(
                lambda _: self.set_mins(
                    _, self.things_processed_tasks[title], None
                )
            )

        self.start_pause_button.title = "Start Timer"
        self.sync_data()


if __name__ == "__main__":
    app = TimerApp(timer_interval=1)
    app.run()
