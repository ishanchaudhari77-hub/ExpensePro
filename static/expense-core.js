/*
 * Core dashboard expense calculation shared by the dashboard and JSUnit tests.
 * This is the same getWindowSum logic previously defined inside dashboard.html.
 */
(function (global) {
    function getWindowSum(model, startIndex, windowSize, categoryKey) {
        if (!model || startIndex < 0 || windowSize <= 0) return 0;
        if (categoryKey === "all") {
            return model.totals
                .slice(startIndex, startIndex + windowSize)
                .reduce((acc, item) => acc + (Number(item) || 0), 0);
        }
        let sum = 0;
        for (let index = startIndex; index < startIndex + windowSize; index += 1) {
            const dayData = model.dailyCategoryByKey[index] || {};
            sum += Number(dayData[categoryKey] || 0);
        }
        return sum;
    }

    global.ExpenseProCore = global.ExpenseProCore || {};
    global.ExpenseProCore.getWindowSum = getWindowSum;
}(window));
