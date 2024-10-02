'''
a collection of methods for working with directories to make my life easier.
* includes wrappers for tkinter filedialogs, to prevent having to manage windows and to avoid crashing the kernel. 
'''

def choose_directory(initialdir = None, title = None) -> str:
    import tkinter as tk
    from tkinter import filedialog
    root = tk.Tk()
    root.withdraw()
    return filedialog.askdirectory(initialdir = initialdir, title = title)

def choose_file(initialdir = None, title = None, ext = None) -> str:
    import tkinter as tk
    from tkinter import filedialog
    root = tk.Tk()
    root.withdraw()
    return filedialog.askopenfilename(initialdir = initialdir, title = title, defaultextension = ext)

def read_file(initialdir = None, title = None, ext = None):
    import tkinter as tk
    from tkinter import filedialog
    root = tk.Tk()
    root.withdraw()
    fi = filedialog.askopenfilename(initialdir = initialdir, title = title, defaultextension = ext)
    return open(fi, 'r').read()

def choose_files(initialdir = None, title = None, ext = None) -> list:
    import tkinter as tk
    from tkinter import filedialog
    root = tk.Tk()
    root.withdraw()
    return filedialog.askopenfilenames(initialdir = initialdir, title = title, defaultextension = ext)

def write_file(bytes, title = None, initialdir = None, ext = None):
    import tkinter as tk
    from tkinter import filedialog
    root = tk.Tk()
    root.withdraw()
    f =  filedialog.asksaveasfile(title = title, initialdir = initialdir, mode = 'w', defaultextension = ext)
    if not f:
        return None
    f.write(bytes)
    f.close

def save_file_name(initialdir = None, title = None, ext = None):
    import tkinter as tk
    from tkinter import filedialog
    root = tk.Tk()
    root.withdraw()
    return filedialog.asksaveasfilename(initialdir = initialdir, title = title, defaultextension = ext)

def download_url(url, dst):
    import requests
    response = requests.get(url)
    assert response.status_code == 200

    with open(dst, 'wb') as f:
        f.write(response.content)