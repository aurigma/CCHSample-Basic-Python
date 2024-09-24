# CCHSample-Basic-Python

Some basic code examples of Customer's Canvas API usage, suitable for quick experiments.

- `blank-editor-save-file-sample.py` - open Design Editor with a blank design of a specified size and save the results to a local folder.
- `open-template-in-editor-save-file-sample.py` - open Design Editor with a specified design template and save the results to a local folder.

## Prerequisites

These samples require Python 3, no external requirements needed. 

## Run

Just pass the script name to `python3` command, like this: 

```
python3 blank-editor-save-file-sample.py
```

It will open on http://localhost:8000. If you prefer using another port, find this line (in the end of a script) and modify it appropriately:

``` py
httpd = HTTPServer(('localhost', 8000), SimpleHTTPRequestHandler)
```

## Further steps

Each sample is heavily commented, so it is recommended to read the script code from the beginning. Also, refer Customer's Canvas docs for more details:

- https://customerscanvas.com/dev/ - developer center, API docs, editor SDK, etc.
- https://customerscanvas.com/help/ - help center for admin and designer functionality.