@echo off
echo Building PrismDB Studio...
call venv\Scripts\activate

REM Clean previous build
rmdir /s /q build
rmdir /s /q dist

REM Build
pyinstaller main.spec

echo Build Complete!
echo You can find the executable in the 'dist' folder.
pause
