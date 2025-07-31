@echo off
REM --- DOS Batch Script to run a command repeatedly ---

REM Define the Python command and its arguments
REM Make sure 'python.exe' is in your system's PATH, or provide its full path (e.g., C:\Python39\python.exe)
REM Make sure 'tmtc.py' and '28v\tlm1.abf' are accessible from where you run this batch file,
REM or provide their full paths.
set "PYTHON_CMD=python"
set "TMTC_SCRIPT=tmtc.py"
set "COM_PORT=COM20"
set "ABF_FILE=28v\tlm1.abf"

REM Define the delay in seconds
set /a DELAY_SECONDS=1

echo Starting script to run "%PYTHON_CMD% %TMTC_SCRIPT% %COM_PORT% %ABF_FILE%" every %DELAY_SECONDS% second(s).
echo Press Ctrl+C to stop.

:loop
    echo.
    echo --- Running command at %DATE% %TIME% ---

    REM Execute the Python command
    %PYTHON_CMD% %TMTC_SCRIPT% %COM_PORT% %ABF_FILE%

    REM Wait for the specified interval
    timeout /t %DELAY_SECONDS% /nobreak >nul

goto loop

REM This section is typically unreachable but good practice for Ctrl+C handling
:end
echo.
echo Script stopped by user (Ctrl+C).
echo Exiting.