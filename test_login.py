"""Run: first ``python app.py``, then ``python test_login.py``.

Selenium black-box suite for TC01-TC10. It creates a uniquely named test account
and test records only through the browser; application code is never modified.
"""
from time import time

from selenium import webdriver
from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

BASE_URL = "http://127.0.0.1:5000"
WAIT_SECONDS = 10
STAMP = str(int(time()))
NAME = f"Selenium Test {STAMP}"
EMAIL = f"selenium.{STAMP}@example.com"
PASSWORD = "TestPass123"
EXPENSE_NOTE = f"Selenium expense {STAMP}"
ALERT_NOTE = f"Selenium alert {STAMP}"


class ExpenseProTests:
    def __init__(self):
        self.driver = webdriver.Chrome(options=webdriver.ChromeOptions())
        self.wait = WebDriverWait(self.driver, WAIT_SECONDS)
        self.results = []

    def find(self, locator):
        return self.wait.until(EC.visibility_of_element_located(locator))

    def wait_for_splash(self):
        """Do not click controls while ExpensePro's welcome splash covers them."""
        self.wait.until(EC.invisibility_of_element_located((By.CSS_SELECTOR, "[data-splash].show")))

    def click(self, locator):
        self.wait_for_splash()
        self.wait.until(EC.element_to_be_clickable(locator)).click()

    def wait_for_text(self, text):
        self.wait.until(lambda d: text in d.find_element(By.TAG_NAME, "body").text)

    def wait_for_flash(self, text):
        def flash_contains(driver):
            try:
                element = driver.find_element(By.ID, "flashed-messages")
                return text in element.get_attribute("textContent")
            except StaleElementReferenceException:
                return False

        self.wait.until(flash_contains)

    def report(self, case_id, module, test_input, expected, actual, passed):
        status = "PASS" if passed else "FAIL"
        self.results.append((case_id, status))
        print(f"\nTest Case ID: {case_id}\nFunction/Module: {module}\nTest Input: {test_input}")
        print(f"Expected Output: {expected}\nActual Output: {actual}\nStatus: {status}")
        assert passed, f"{case_id} failed: {actual}"

    def run_case(self, case_id, module, test_input, expected, test):
        try:
            self.report(case_id, module, test_input, expected, test(), True)
        except Exception as error:
            self.report(case_id, module, test_input, expected, f"FAILED - {error}", False)

    def logout(self):
        self.driver.get(f"{BASE_URL}/login")
        # When already logged out, /login itself is the required final state.
        if "/login" in self.driver.current_url:
            self.find((By.NAME, "email"))
            return
        self.click((By.CSS_SELECTOR, "form[data-logout-form] button"))
        self.click((By.CSS_SELECTOR, "[data-logout-confirm]"))
        self.find((By.NAME, "email"))

    def add_expense(self, amount, description):
        self.driver.get(f"{BASE_URL}/expenses")
        form = self.find((By.CSS_SELECTOR, "form[action='/add']"))
        form.find_element(By.NAME, "amount").send_keys(str(amount))
        form.find_element(By.NAME, "description").send_keys(description)
        self.wait_for_splash()
        form.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

    def tc01(self):
        self.driver.get(f"{BASE_URL}/login")
        self.find((By.NAME, "email")).send_keys("wrong@example.com")
        self.driver.find_element(By.NAME, "password").send_keys("wrongpassword")
        self.click((By.CSS_SELECTOR, "form[action='/login'] button[type='submit']"))
        actual = self.find((By.CSS_SELECTOR, ".auth-error")).text.strip()
        assert actual == "Invalid email or password."
        return actual

    def tc03(self):
        self.driver.get(f"{BASE_URL}/register")
        self.find((By.NAME, "name")).send_keys(NAME)
        self.driver.find_element(By.NAME, "email").send_keys(EMAIL)
        self.driver.find_element(By.NAME, "password").send_keys(PASSWORD)
        self.driver.find_element(By.NAME, "confirm_password").send_keys(PASSWORD)
        self.click((By.CSS_SELECTOR, "form[action='/register'] button[type='submit']"))
        self.wait_for_text("Dashboard")
        return f"Account created for {EMAIL}; dashboard opened"

    def tc04(self):
        # Logged-in users are redirected away from /register by the app.
        self.logout()
        self.driver.get(f"{BASE_URL}/register")
        form = self.find((By.CSS_SELECTOR, "form[action='/register']"))
        assert not self.driver.execute_script("return arguments[0].checkValidity()", form)
        return "Browser validation blocked empty required fields"

    def tc02(self):
        self.logout()
        self.find((By.NAME, "email")).send_keys(EMAIL)
        self.driver.find_element(By.NAME, "password").send_keys(PASSWORD)
        self.click((By.CSS_SELECTOR, "form[action='/login'] button[type='submit']"))
        self.wait_for_text("Dashboard")
        return "Correct credentials opened the dashboard"

    def tc05(self):
        self.add_expense(250, EXPENSE_NOTE)
        self.wait_for_text(EXPENSE_NOTE)
        return f"Expense '{EXPENSE_NOTE}' was added"

    def tc06(self):
        self.driver.get(f"{BASE_URL}/expenses")
        form = self.find((By.CSS_SELECTOR, "form[action='/add']"))
        form.find_element(By.NAME, "amount").send_keys("-10")
        assert not self.driver.execute_script("return arguments[0].checkValidity()", form)
        return "Browser validation rejected negative amount"

    def tc07(self):
        self.driver.get(f"{BASE_URL}/settings")
        form = self.find((By.CSS_SELECTOR, "form[action='/settings/budget']"))
        amount = form.find_element(By.NAME, "amount")
        amount.clear()
        amount.send_keys("100")
        self.wait_for_splash()
        form.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        self.wait_for_flash("Budget saved")
        return "Monthly budget Rs. 100 was saved"

    def tc08(self):
        self.driver.get(f"{BASE_URL}/expenses")
        row = self.find((By.XPATH, f"//tr[.//td[contains(., '{EXPENSE_NOTE}')]]"))
        row.find_element(By.CSS_SELECTOR, "a.btn-edit").click()
        description = self.find((By.NAME, "description"))
        description.clear()
        description.send_keys(f"{EXPENSE_NOTE} edited")
        self.click((By.CSS_SELECTOR, "form[action^='/edit/'] button[type='submit']"))
        self.wait_for_flash("Expense updated")
        self.driver.get(f"{BASE_URL}/expenses")
        row = self.find((By.XPATH, f"//tr[.//td[contains(., '{EXPENSE_NOTE} edited')]]"))
        self.wait_for_splash()
        row.find_element(By.CSS_SELECTOR, "button.btn-delete").click()
        self.click((By.CSS_SELECTOR, "[data-action-confirm]"))
        self.wait.until(lambda d: f"{EXPENSE_NOTE} edited" not in d.find_element(By.TAG_NAME, "body").text)
        return "Existing expense was edited and deleted after confirmation"

    def tc09(self):
        self.driver.get(f"{BASE_URL}/reports")
        self.wait_for_text("Expense Overview")
        return "Reports page and expense overview loaded"

    def tc10(self):
        self.add_expense(150, ALERT_NOTE)
        self.wait_for_flash("Monthly budget exceeded")
        return "Budget exceeded alert displayed after a Rs. 150 expense"

    def run(self):
        # TC03 runs before TC02 because it creates the isolated account for login tests.
        cases = [
            ("TC01", "Login", "Wrong email + password", "Invalid email error", self.tc01),
            ("TC03", "Registration", "Valid name, email, password", "Account created", self.tc03),
            ("TC04", "Registration", "Empty required fields", "Submission blocked", self.tc04),
            ("TC02", "Login", "Correct email + password", "Dashboard opens", self.tc02),
            ("TC05", "Add Expense", "Rs. 250, category, details", "Expense added", self.tc05),
            ("TC06", "Add Expense", "Negative amount", "Submission blocked", self.tc06),
            ("TC07", "Budget", "Valid budget Rs. 100", "Budget saved", self.tc07),
            ("TC08", "Expense Management", "Existing test expense", "Edited and deleted", self.tc08),
            ("TC09", "Reports", "Existing expense data", "Report loads", self.tc09),
            ("TC10", "Alerts", "Rs. 150 against Rs. 100 budget", "Budget alert", self.tc10),
        ]
        for args in cases:
            self.run_case(*args)
        print("\nSummary: " + ", ".join(f"{case}: {status}" for case, status in self.results))

    def close(self):
        self.driver.quit()


if __name__ == "__main__":
    suite = ExpenseProTests()
    try:
        suite.run()
    finally:
        suite.close()
