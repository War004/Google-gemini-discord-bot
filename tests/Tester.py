import sys

from tests.TestContainer import TestContainer
from src.cogs.chat.ChatHistoryHandler import ChatHistoryHandler
from pathlib import Path
from tests.unit.HistoryHandlerUnitTest import HistoryHandlerUnitTest
from tests.Message import Message
from tests.TestResult import Passed, Failed
from src.loader.Results import Success, Error
from tests.unit.module_tests import ModuleTest
from typing import Literal, Callable

testContainer = TestContainer(
    chat_history_handler=ChatHistoryHandler(Path("test_data")),
    messages=Message()
)

#Unit test for module, chat handler 
model_unit_test = ModuleTest(testContainer.messages)
chat_handler_unit_test = HistoryHandlerUnitTest(testContainer.chat_history_handler,testContainer.messages)

#Test function instances for module, chat handler
module_unit_test_instance = model_unit_test.get_all_test_in_order()
chat_handler_unit_test_instance = chat_handler_unit_test.get_all_test_in_order()

#A list that contain a list of callable with any parameter but output is Passed or Failed 
all_function_instance:list[list[Callable[..., Passed | Failed]]] = [module_unit_test_instance,chat_handler_unit_test_instance]
test_result:dict[str, dict[str,int]] = {}
for instance in all_function_instance:
    try:
        instance_name = instance[0].__self__.__class__.__name__
        if instance_name is None:
            print("Could not resolve class name for the test instance.")
            sys.exit(1)
    except IndexError:
        print("The list of test instances is empty.")
        sys.exit(1)

    print(f"Starting test for {instance_name}")
    
    test_result[instance_name] = {
        "total": 0,
        "failed": 0
    }

    for test in instance:
        result = test()

        cusor = test_result.get(result.instance)
        cusor["total"] += 1
        
        match result:
            case Passed():
                pass
            case Failed():
                print(f"Test failed for {result.method}")
                print(result.message)
                print("\n")
                cusor["failed"] += 1


total_instance = 0
total_tests = 0
total_passed = 0
total_failed = 0
for entry in test_result:
    total_instance +=1

    cusor = test_result.get(entry)
    total_tests += cusor.get("total")
    total_failed += cusor.get("failed")
    total_passed += cusor.get("total") - cusor.get("failed")

if(total_passed==total_tests and total_tests>0):
    print(f"Ran {total_tests} tests across {total_instance} test instance. All {total_passed} tests passed.")
    sys.exit(0)
else:
    print(f"Total test: {total_tests}\nTotal instance: {total_instance}\nTotal Failed: {total_failed}\nTotal Passed: {total_passed}")
    print("Look in the logs, for information aboue failed tests.")
    sys.exit(1)