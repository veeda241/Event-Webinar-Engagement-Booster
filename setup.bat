@echo off
echo =================================================
echo  Installing Project Dependencies Globally
echo =================================================
echo This will install packages into your main Python installation.

echo Installing packages...
python -m pip install --upgrade pip
pip install -r requirements.txt

echo Setup complete!