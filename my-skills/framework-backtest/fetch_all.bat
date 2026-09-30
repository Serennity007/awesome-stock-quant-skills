@echo off
:loop
cd /d C:/Users/ztl/awesome-stock-quant-skills/my-skills/framework-backtest
python -u scripts/fetch_history.py --pool hs300 >> fetch_run.log 2>&1
if exist fetch_done.flag goto done
timeout /t 15 /nobreak >nul
goto loop
:done
echo ALL_FETCHED
