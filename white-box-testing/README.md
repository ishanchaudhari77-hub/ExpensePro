# Experiment No. 8 — White Box Testing

## Aim

Write and execute white-box test cases for the core ExpensePro expense-tracker logic using JSUnit 2.2.

## Software used

JSUnit.net / JSUnit 2.2 (the existing `../jsunit` folder).

## Actual ExpensePro function tested

`ExpenseProCore.getWindowSum(model, startIndex, windowSize, categoryKey)` in `../static/expense-core.js`.

This is ExpensePro's real dashboard expense-total calculation. The dashboard imports this same function in `../templates/dashboard.html` to calculate the spend total for the selected date range and category in the expense trend chart. It was moved unchanged from the dashboard inline script to the shared static file only so the dashboard and JSUnit can both call the exact same code. No calculation or application behaviour was changed.

## What the function does

It returns an expense total for a selected period:

- Returns `0` for an invalid model, negative start index, or zero/negative window size.
- For category `all`, adds all daily expense totals in the requested window.
- For a named category such as `food`, adds that category's amount from each day.
- Missing categories contribute `0` instead of causing an error.

## Test cases and result

| Test case | Internal path | Expected result | Actual result | Status |
| --- | --- | --- | --- | --- |
| TC01 | All-category total branch | 250 | 250 | PASS |
| TC02 | Specific-category loop (`food`) | 150 | 150 | PASS |
| TC03 | Missing-category fallback (`health`) | 0 | 0 | PASS |
| TC04 | Guard condition (negative start index) | 0 | 0 | PASS |

## Run the practical

1. Open the `white-box-testing` folder.
2. Double-click `TestRunner.html` in Edge or Chrome.
3. Confirm the page shows **Runs: 4**, **Passed: 4**, **Failures: 0**, and TC01–TC04 all show **PASS**.

No web server, Flask change, package installation, or Selenium is required. The test runner uses the supplied JSUnit 2.2 `assertEquals()` library directly; the old 2007 frame-based JSUnit browser runner is not reliable in modern Edge local-file mode.

## Screenshot for the journal

Take one screenshot of the completed **ExpensePro - White Box Testing** page. It should visibly show the `Runs: 4 | Passed: 4 | Failures: 0` summary and the four TC rows with expected and actual results.

## Short explanation for teacher

“I tested ExpensePro's actual dashboard expense-total function, `getWindowSum`. It is used when the dashboard calculates spending for a selected date range and category. I read its code and designed test cases for its all-category path, category loop, missing-category fallback, and invalid-index guard. This is white-box testing because the test cases were designed from the function's internal conditions and statements. All four JSUnit tests passed, which means the tested paths produced the expected expense totals.”
