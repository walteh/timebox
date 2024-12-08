#!/usr/bin/env python3
import rumps
import time
import subprocess
import shlex
import logging
import sys
import things
from typing import Dict, Tuple

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

class TimerApp:
    def __init__(self):
        self.app = rumps.App("Timebox", "🥊")
        self.timer = rumps.Timer(self.on_tick, 1)
        self.timer.stop()
        self.timer.count = 0
        
        # Menu items
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
        self.total_time = rumps.MenuItem(title="", callback=None)
        
        # Quick select buttons
        self.quick_buttons = {}
        for mins in [5, 10, 15, 20, 25]:
            self.quick_buttons[mins] = rumps.MenuItem(
                title=f"{mins} Minutes",
                callback=lambda _, m=mins: self.set_mins(_, m*60, None)
            )
        
        # Set up menu
        self.app.menu = [
            self.start_button,
            self.sync_button,
            None,
            self.total_time,
            None,
            *self.quick_buttons.values(),
            None,
            self.stop_button
        ]
        
        self.sync_data()

    def sync_data(self, sender=None):
        tasks = get_todays_tasks()
        
        # Remove old task items
        if hasattr(self, 'task_items'):
            for item in self.task_items:
                del self.app.menu[item.title]
        
        # Add new task items
        self.task_items = []
        last_item = self.total_time.title
        
        for project, project_tasks in tasks.items():
            if project_tasks:
                # Add project header
                header = rumps.MenuItem(f"—— {project} ——", callback=None)
                self.app.menu.insert_after(last_item, header)
                self.task_items.append(header)
                last_item = header.title
                
                # Add tasks
                for title, (minutes, url) in project_tasks.items():
                    item = rumps.MenuItem(
                        title=f"{title} → {minutes}m",
                        callback=lambda _, m=minutes, u=url: self.set_mins(_, m*60, u)
                    )
                    self.app.menu.insert_after(last_item, item)
                    self.task_items.append(item)
                    last_item = item.title
        
        # Update total time
        total = sum(
            time for project in tasks.values() 
            for time, _ in project.values()
        )
        self.total_time.title = f"{format_time(total)} of work today!"

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
    
    # Start menu bar app
    TimerApp().app.run()

if __name__ == "__main__":
    main()
