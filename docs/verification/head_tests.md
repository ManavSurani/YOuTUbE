............FF.......................................................... [ 23%]
..........................F............................................. [ 46%]
........................................................................ [ 69%]
........................................................................ [ 92%]
.......................                                                  [100%]
================================== FAILURES ===================================
__________________________ test_scope_checker_clean ___________________________

    def test_scope_checker_clean():
        res = subprocess.run(
            [sys.executable, "tools/check_scope.py", "--phase", "11"],
            capture_output=True,
            text=True,
        )
>       assert res.returncode == 0
E       AssertionError: assert 1 == 0
E        +  where 1 = CompletedProcess(args=['C:\\Users\\Jay\\AppData\\Local\\Programs\\Python\\Python313\\python.exe', 'tools/check_scope.p...--phase 11):\n  Protected file violations (NEVER ALLOWED):\n    [PROTECTED] app/core/download_manager.py\n', stderr='').returncode

tests\test_check_scope.py:13: AssertionError
__________________________ test_scope_checker_final ___________________________

    def test_scope_checker_final():
        res = subprocess.run(
            [sys.executable, "tools/check_scope.py", "--final"],
            capture_output=True,
            text=True,
        )
>       assert res.returncode == 0
E       AssertionError: assert 1 == 0
E        +  where 1 = CompletedProcess(args=['C:\\Users\\Jay\\AppData\\Local\\Programs\\Python\\Python313\\python.exe', 'tools/check_scope.p...FAIL (--final): The following protected files were modified:\n  [PROTECTED] app/core/download_manager.py\n', stderr='').returncode

tests\test_check_scope.py:23: AssertionError
______________________ test_exact_command_string_unicode ______________________

    def test_exact_command_string_unicode():
        p = Path(r"C:\\Downloads\\\uff5c \uff1a \u29f8 \xe9 \u65e5\u672c\u8a9e \U0001f600.mkv")
        cmd = build_select_command(p)
>       assert cmd == r'/select,"C:\\Downloads\\\uff5c \uff1a \u29f8 \xe9 \u65e5\u672c\u8a9e \U0001f600.mkv"'
E       assert '/select,"C:\\... \xe9 \u65e5\u672c\u8a9e \U0001f600.mkv"' == '/select,"C:\\... \xe9 \u65e5\u672c\u8a9e \U0001f600.mkv"'
E         
E         - /select,"C:\\Downloads\\\uff5c \uff1a \u29f8 \xe9 \u65e5\u672c\u8a9e \U0001f600.mkv"
E         ?             ^
E         + /select,"C:\\downloads\\\uff5c \uff1a \u29f8 \xe9 \u65e5\u672c\u8a9e \U0001f600.mkv"
E         ?             ^

tests\test_file_actions.py:25: AssertionError
=========================== short test summary info ===========================
FAILED tests/test_check_scope.py::test_scope_checker_clean - AssertionError: ...
FAILED tests/test_check_scope.py::test_scope_checker_final - AssertionError: ...
FAILED tests/test_file_actions.py::test_exact_command_string_unicode - assert...
3 failed, 308 passed in 27.23s
