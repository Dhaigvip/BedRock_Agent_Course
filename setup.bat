@echo off
REM Install dependencies for all three sub-projects.
REM Run once after cloning: setup.bat

echo.
echo =^> travel-api
cd travel-api && uv sync && cd ..

echo.
echo =^> mcp-server
cd mcp-server && uv sync && cd ..

echo.
echo =^> agent
cd agent && uv sync && cd ..

echo.
echo All done. See README.md for how to run the stack.
