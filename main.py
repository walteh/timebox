#!/usr/bin/env python3
import rumps
import time
import subprocess
import shlex
import logging
import sys
import things
from typing import Dict, Tuple
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import os
from pathlib import Path
import glob

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

def extract_minutes(tag: str) -> int | None:
    """Extract minutes from various time formats like '30min', '30 min', '30m', '30 m'"""
    tag = tag.lower().replace(' ', '')
    if tag.endswith('min') or tag.endswith('m'):
        try:
            minutes = int(''.join(c for c in tag if c.isdigit()))
            return minutes
        except ValueError:
            return None
    return None

def get_todays_tasks() -> Dict[str, Dict[str, Tuple[int, str]]]:
    """Get today's tasks from Things, organized by project"""
    processed_tasks = {}
    
    try:
        tasks = things.today()
        for task in tasks:
            if 'tags' in task:
                time_tags = []
                for tag in task['tags']:
                    if minutes := extract_minutes(tag):
                        time_tags.append((tag, minutes))
                
                if time_tags:
                    _, minutes = time_tags[0]
                    project_name = task.get('project_title', 'No Project')
                    
                    if project_name not in processed_tasks:
                        processed_tasks[project_name] = {}
                    
                    processed_tasks[project_name][task['title']] = (
                        minutes,
                        f"things:///show?id={task['uuid']}"
                    )
    except Exception as e:
        logging.error(f"Error fetching tasks: {e}")
    
    return processed_tasks

def format_time(minutes: int) -> str:
    hours = minutes // 60
    mins = minutes % 60
    if hours > 0:
        return f"{hours}h{f' {mins}m' if mins else ''}"
    return f"{mins}m"

def get_things_db_path() -> str:
    """Get the path to the Things database"""
    base_paths = [
        "~/Library/Group Containers/JLMPQHK86H.com.culturedcode.ThingsMac/ThingsData-*/Things Database.thingsdatabase/main.sqlite",
        "~/Library/Containers/com.culturedcode.ThingsMac/Data/Library/Application Support/Cultured Code/Things/Things.sqlite3"
    ]
    
    for path_pattern in base_paths:
        expanded_path = os.path.expanduser(path_pattern)
        matching_paths = glob.glob(expanded_path)
        if matching_paths:
            return matching_paths[0]
    
    raise FileNotFoundError("Could not find Things database")

class ThingsDBHandler(FileSystemEventHandler):
    def __init__(self, timer_app):
        self.timer_app = timer_app
        self.last_sync = 0
        self.cooldown = 2  # Minimum seconds between syncs

    def on_modified(self, event):
        # Only sync if enough time has passed since last sync
        current_time = time.time()
        if current_time - self.last_sync > self.cooldown:
            self.last_sync = current_time
            logging.info("Things database changed, syncing...")
            # Call sync_data directly instead of using a timer
            self.timer_app.sync_data()

class TimerApp:
    def __init__(self):
        self.app = rumps.App("Timebox", "🥊")
        self.timer = rumps.Timer(self.on_tick, 1)
        self.timer.stop()
        self.timer.count = 0
        self.current_url = None
        
        # Menu items with fixed keys
        self.start_button = rumps.MenuItem(
            title="Start Timer",
            callback=self.start_timer,
            key="s"
        )
        self.sync_button = rumps.MenuItem(
            title="Sync",
            callback=self.sync_data,
            key="r"
        )
        self.stop_button = rumps.MenuItem(
            title="Stop Timer",
            callback=self.stop_timer
        )
        self.total_time = rumps.MenuItem(title="Total Time", callback=None)
        
        # Quick select buttons
        self.quick_buttons = {}
        for mins in [5, 10, 15, 20, 25]:
            self.quick_buttons[mins] = rumps.MenuItem(
                title=f"{mins} Minutes",
                callback=lambda _, m=mins: self.set_mins(_, m*60, None)
            )
        
        # Set up menu
        self.menu_items = [
            self.start_button,
            self.sync_button,
            None,  # separator
            self.total_time,
            None,  # separator
            *self.quick_buttons.values(),
            None,  # separator
            self.stop_button
        ]
        self.app.menu = self.menu_items
        
        # Set up file watching
        self.setup_file_watching()
        
        # Initial sync
        self.sync_data()

    def setup_file_watching(self):
        try:
            db_path = get_things_db_path()
            db_dir = str(Path(db_path).parent)
            db_name = Path(db_path).name
            
            class FilteredHandler(ThingsDBHandler):
                def on_modified(self, event):
                    if Path(event.src_path).name == db_name:
                        super().on_modified(event)
            
            self.observer = Observer()
            self.observer.schedule(
                FilteredHandler(self),
                db_dir,
                recursive=False
            )
            self.observer.start()
            logging.info(f"Watching Things database at: {db_path}")
        except Exception as e:
            logging.error(f"Could not set up database watching: {e}")

    def sync_data(self, sender=None):
        if sender:
            logging.info("Manual sync triggered")
        
        # Show sync indicator
        original_title = self.app.title
        self.app.title = "↻"
        
        try:
            tasks = get_todays_tasks()
            logging.info(f"Retrieved {len(tasks)} projects")
            
            # Create fresh instances of permanent menu items
            start_button = rumps.MenuItem(
                title=self.start_button.title,  # Preserve the current title state
                callback=self.start_timer,
                key="s"
            )
            sync_button = rumps.MenuItem(
                title="Sync",
                callback=self.sync_data,
                key="r"
            )
            stop_button = rumps.MenuItem(
                title="Stop Timer",
                callback=self.stop_timer
            )
            total_time = rumps.MenuItem(title="", callback=None)  # Empty title, will be updated later
            
            # Create fresh quick select buttons
            quick_buttons = {}
            for mins in [5, 10, 15, 20, 25]:
                quick_buttons[mins] = rumps.MenuItem(
                    title=f"{mins} Minutes",
                    callback=lambda _, m=mins: self.set_mins(_, m*60, None)
                )
            
            # Create a fresh menu list
            new_menu = [
                start_button,
                sync_button,
                None,  # separator
                total_time,
                None  # separator
            ]
            
            # Add task items
            self.task_items = []
            for project, project_tasks in tasks.items():
                if project_tasks:
                    # Add project header
                    header = rumps.MenuItem(f"—— {project} ——", callback=None)
                    new_menu.append(header)
                    self.task_items.append(header)
                    
                    # Add tasks
                    for title, (minutes, url) in project_tasks.items():
                        item = rumps.MenuItem(
                            title=f"{title} → {minutes}m",
                            callback=lambda _, m=minutes, u=url: self.set_mins(_, m*60, u)
                        )
                        new_menu.append(item)
                        self.task_items.append(item)
            
            # Add separator and quick buttons only if we have tasks
            if self.task_items:
                new_menu.append(None)  # separator
            
            # Add the quick select buttons and stop button
            new_menu.extend([
                *quick_buttons.values(),
                None,  # separator
                stop_button
            ])
            
            # Calculate total time before updating the menu
            total = sum(
                time for project in tasks.values() 
                for time, _ in project.values()
            )
            total_time.title = f"{format_time(total)} of work today!"
            
            # Clear the existing menu by setting it to just a quit button
            self.app.menu.clear()
            
            # Update the menu with new items
            self.app.menu = new_menu
            
            # Update our references to the new menu items
            self.start_button = start_button
            self.sync_button = sync_button
            self.stop_button = stop_button
            self.total_time = total_time
            self.quick_buttons = quick_buttons
            self.menu_items = new_menu
            
            # Restore the app title
            self.app.title = original_title
            logging.info("Menu updated successfully")
        except Exception as e:
            logging.error(f"Error updating menu: {e}")
            logging.error(f"Exception details: {str(e)}")
            import traceback
            logging.error(traceback.format_exc())
            self.app.title = original_title

    def set_mins(self, sender, seconds, url):
        self.timer.end = seconds
        self.current_url = url
        self.start_timer(sender)

    def start_timer(self, sender):
        if sender.title.startswith(("Start", "Continue")):
            if sender.title == "Start Timer":
                self.timer.count = 0
            sender.title = "Pause Timer"
            self.timer.start()
        else:
            sender.title = "Continue Timer"
            self.timer.stop()

    def stop_timer(self, sender=None):
        self.timer.stop()
        self.timer.count = 0
        self.app.title = "🥊"
        self.start_button.title = "Start Timer"

    def on_tick(self, timer):
        """Handle timer ticks"""
        time_left = timer.end - timer.count
        mins = time_left // 60 if time_left >= 0 else time_left // 60 + 1
        secs = time_left % 60 if time_left >= 0 else (-1 * time_left) % 60
        
        if mins == 0 and time_left < 0:
            rumps.notification(
                title="Timebox",
                subtitle="Time is up! Take a break :)",
                message=""
            )
            if self.current_url:
                subprocess.call(shlex.split(f"open '{self.current_url}'"))
                self.current_url = None
            self.stop_timer()
        else:
            self.app.title = f"{mins:2d}:{secs:02d}"
        timer.count += 1

def main():
    tasks = get_todays_tasks()
    
    # Print summary in terminal
    total_minutes = sum(
        time for project in tasks.values() 
        for time, _ in project.values()
    )
    print(f"\n📋 Today's Tasks ({format_time(total_minutes)} total):\n")
    
    for project, project_tasks in tasks.items():
        project_time = sum(time for time, _ in project_tasks.values())
        print(f"\n—— {project} ({format_time(project_time)}) ——")
        for title, (minutes, url) in project_tasks.items():
            print(f"• {title} → {minutes}m")
    
    print("\nStarting menu bar app...")
    
    try:
        TimerApp().app.run()
    except KeyboardInterrupt:
        logging.info("Shutting down...")
        # The observer will be stopped when the process ends

if __name__ == "__main__":
    main()
