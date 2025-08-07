@echo off
echo.
echo ===================================================
echo         Token Validation Check
echo ===================================================
echo.

REM Check if token file exists
if not exist "token.config" (
    echo ❌ token.config file not found!
    echo Please ensure you have a valid token file.
    goto end
)

REM Get token file size
for %%i in ("token.config") do set filesize=%%~zi

echo ✅ Token file found (size: %filesize% bytes)

REM Show first few characters of token
set /p token=<token.config
set preview=%token:~0,50%
echo    Preview: %preview%...

echo.
echo ===================================================
echo         Token Generation Instructions
echo ===================================================
echo.
echo If your token is expired, follow these steps:
echo.
echo 1. Open this URL in your browser:
echo    https://login.microsoftonline.com/common/oauth2/authorize
echo    ?client_id=51f81489-12ee-4a9e-aaae-a2591f45987d
echo    ^&response_type=token
echo    ^&redirect_uri=https://localhost
echo    ^&resource=https://aurorabapenv87b96.crm10.dynamics.com/
echo    ^&prompt=login
echo.
echo 2. Log in with your Azure/Dataverse credentials
echo 3. After login, copy the access_token from redirect URL
echo 4. Replace token.config content with the new token
echo 5. Run multi_thread_runner.py to test
echo.
echo ===================================================
echo         API Test Information
echo ===================================================
echo.
echo Target API: https://aurorabapenv87b96.crm10.dynamics.com/api/copilot/v1.0/queryskillstructureddata
echo Headers: Authorization: Bearer [your-token]
echo Content-Type: application/json
echo.
echo Test the token by running:
echo   python multi_thread_runner.py
echo   python simple_token_test.py
echo.

:end
echo ===================================================
pause