"""
This file is used to display error message
"""

class Message:
    def __init__(self):
        self.expected_and_actual_not_equal = "Expected value and actual value are different."
        self.compare_expected_and_actual = "Expected value was {} vs Actual value {}"
        self.epxected_is_null = "Expected Values is null"
        self.actual_is_null = "Actual value is null"
        self.repair_test_case = "Repair the test case"
        self.function_failed = "The function didn't worked correctly."