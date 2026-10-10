........................................................................ [ 29%]
.F...................................................................... [ 59%]
........................................................................ [ 89%]
.........................                                                [100%]
================================== FAILURES ===================================
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
FAILED tests/test_file_actions.py::test_exact_command_string_unicode - assert...
1 failed, 240 passed in 17.04s
