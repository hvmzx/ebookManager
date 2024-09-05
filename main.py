import subprocess
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler

path="mangas"
print('Watching for folder ' + path + ' for new mangas')

class MyHandler(PatternMatchingEventHandler):
    def on_created(self, event):
        if not event.is_directory:
            print("New file created:", event.src_path)
            subprocess.run(["python", "kcc/kcc-c2e.py -p KoC -m -u -s -d -t " + event.src_path])
if __name__ == "__main__":
    observer = Observer()
    event_handler = MyHandler(patterns=["*.cbz"])
    observer.schedule(event_handler, path=path, recursive=True)
    observer.start()
    try:
        while True:
            pass
    except KeyboardInterrupt:
        observer.stop()
    observer.join()