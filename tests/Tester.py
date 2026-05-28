import sys

from tests.TestContainer import TestContainer
from src.cogs.chat.ChatHistoryHandler import ChatHistoryHandler
from pathlib import Path
from tests.unit.HistoryHandlerUnitTest import HistoryHandlerUnitTest
from tests.Message import Message
from tests.TestResult import Passed, Failed
from src.loader.Results import Success, Error

testContainer = TestContainer(
    chat_history_handler=ChatHistoryHandler(Path("test_data")),
    messages=Message()
)

#First unit test
chat_handler_unit_test = HistoryHandlerUnitTest(testContainer.chat_history_handler,testContainer.messages)

functions = chat_handler_unit_test.get_all_test_inOrder()
test_results:list[Passed | Failed] = []
for call in functions:
    test_results.append(call())

passed = 0
for result in test_results:
    match result:
        case Passed():
            passed += 1
        case Failed():
            print(f"Test failed for {result.instance}.{result.method}")
            print(result.message)
            print("\n")
if passed == len(test_results) and len(test_results) > 0:
    print(f"All test cases for the instance {test_results[0].instance} passed.")
    sys.exit(0)
else:
    sys.exit(1)