# Official JSUnit 2.2 Runner

The original JSUnit 2.2 runner needs an HTTP URL in modern Edge. Do not open `jsunit/testRunner.html` directly with `file:///`.

1. Open PowerShell in the ExpensePro project folder.
2. Run:

```powershell
py -m http.server 8000
```

3. Keep that PowerShell window open. In Edge, open this exact URL:

```text
http://127.0.0.1:8000/jsunit/testRunner.html?testpage=http://127.0.0.1:8000/white-box-testing/testExpenseWindowSum.html&autorun=true&ui=modern&showtestframe=true
```

4. Wait until the official JSUnit runner shows `Runs: 4`, `Errors: 0`, and `Failures: 0`.
5. Click **All** if needed to display successful test entries. Take the screenshot of this official JSUnit screen for the journal.
6. Return to PowerShell and press `Ctrl+C` when finished to stop the temporary local server.
