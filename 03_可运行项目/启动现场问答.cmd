@echo off
chcp 65001 >nul
set PYTHONUTF8=1
set PYTHONDONTWRITEBYTECODE=1
cd /d "%~dp0"
set "RAG_PYTHON="
if exist ".venv\Scripts\python.exe" set "RAG_PYTHON=%CD%\.venv\Scripts\python.exe"
if not defined RAG_PYTHON if exist "..\..\.runtime\Scripts\python.exe" set "RAG_PYTHON=%CD%\..\..\.runtime\Scripts\python.exe"
if not defined RAG_PYTHON (
  echo 请先按 README_运行说明.md 安装本项目环境。
  pause
  exit /b 1
)
for %%I in ("%RAG_PYTHON%") do set "PATH=%%~dpI;%PATH%"
"%RAG_PYTHON%" rag_engine.py
pause