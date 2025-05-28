libraries = ["jira", "requests", "litmos"]

for library in libraries:
    try:
        __import__(library)
        print(f"{library} is installed.")
    except ImportError:
        print(f"{library} is not installed.")
