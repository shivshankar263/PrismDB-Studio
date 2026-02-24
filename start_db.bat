@echo off
echo Starting Local MongoDB Instance...
if not exist "data" mkdir "data"
"C:\Program Files\MongoDB\Server\8.2\bin\mongod.exe" --dbpath="data" --bind_ip 127.0.0.1
pause
