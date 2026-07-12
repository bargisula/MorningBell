@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo  ================================
echo   晨鐘 MorningBell 正在啟動...
echo  ================================
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo  [!] 找不到 Python。請先到 https://www.python.org/downloads/ 安裝，
    echo      安裝時記得勾選 "Add Python to PATH"，然後再執行一次這個檔案。
    pause
    exit /b 1
)

if not exist venv (
    echo  第一次啟動：正在建立環境（約 1~2 分鐘，只需要做這一次）...
    python -m venv venv
)

call venv\Scripts\activate.bat
pip install -r requirements.txt -q

echo.
echo  啟動完成！瀏覽器即將打開 http://127.0.0.1:8888
echo  要關閉時，直接關掉這個黑色視窗即可。
echo.
start "" http://127.0.0.1:8888
python -m uvicorn main:app --host 127.0.0.1 --port 8888
